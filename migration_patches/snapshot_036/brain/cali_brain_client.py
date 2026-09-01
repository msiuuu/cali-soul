"""cali_brain_client — sidecar daemon client for hanamorix bridge integration.

This module is the bridge-side half of the cali brain sidecar. The other half
is `my_brain.py daemon` (in cali-soul/), which runs as a persistent subprocess.

Architecture (per persistence_plan.md Option B):
    - my_brain.py runs as a daemon process started by the bridge
    - Communication via JSON-Lines over stdin/stdout pipes
    - One daemon per bridge process — singleton via module-level globals
    - Lazy spawn: first call to turn() starts the daemon
    - Crash recovery: if daemon dies, next call respawns it
    - Atexit hook: kills daemon when bridge exits

Public API:
    turn(message: str) -> dict       — per-message brain processing
    log_response(text: str) -> dict  — log cali's response for meta_loop check
    mark_initiation() -> dict        — record initiation reset
    boot() -> dict                   — full system boot (call once at session start)
    ping() -> dict                   — liveness check
    shutdown() -> None               — explicit cleanup (also fires on atexit)

All commands return a dict like:
    {"ok": bool, "stdout": str, "stderr": str, "error": str?}

If the daemon is unavailable or crashes, returns:
    {"ok": false, "error": "daemon unavailable: <reason>"}

Brain context for the LLM system prompt:
    build_brain_context_block(turn_result: dict) -> str
        Formats the stdout of a turn() result into a markdown-friendly block
        suitable for injection into build_system_message.
"""
from __future__ import annotations

import atexit
import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── configuration ──────────────────────────────────────────────────────────────

# Default path to my_brain.py — overridable via CALI_BRAIN_PATH env var or
# resolve_brain_path() argument. We look in the persona dir's cali-soul subdir
# first (where Mish copied her files), then fall back to a sibling cali-soul/
# checkout. Set CALI_BRAIN_PATH to override entirely.
_DEFAULT_BRAIN_FILENAME = "my_brain.py"

_REQUEST_TIMEOUT_SECONDS = 30.0
_BOOT_TIMEOUT_SECONDS = 60.0  # boot can be slow
_READINESS_TIMEOUT_SECONDS = 10.0
_DAEMON_SPAWN_RETRIES = 2

# ── singleton state ───────────────────────────────────────────────────────────

_proc: subprocess.Popen | None = None
_proc_lock = threading.Lock()  # serialises requests + lifecycle
_next_id = 1
_brain_path: Path | None = None  # resolved once per process


# ── path resolution ───────────────────────────────────────────────────────────

def resolve_brain_path(persona_dir: Path | None = None) -> Path | None:
    """Resolve the path to my_brain.py.

    Resolution order:
        1. CALI_BRAIN_PATH env var (absolute path to my_brain.py)
        2. {persona_dir}/cali-soul/my_brain.py  (where mish copied files)
        3. {persona_dir}/my_brain.py            (alternate placement)
        4. None — daemon cannot start

    Caches result in module-level _brain_path on first successful resolve.
    """
    global _brain_path
    if _brain_path is not None and _brain_path.exists():
        return _brain_path

    env_path = os.environ.get("CALI_BRAIN_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            _brain_path = p
            return p
        logger.warning("CALI_BRAIN_PATH set to %s but file not found", env_path)

    if persona_dir is not None:
        candidates = [
            persona_dir / "cali-soul" / _DEFAULT_BRAIN_FILENAME,
            persona_dir / _DEFAULT_BRAIN_FILENAME,
        ]
        for c in candidates:
            if c.exists():
                _brain_path = c
                return c

    logger.warning("cali brain my_brain.py not found in any known location")
    return None


# ── daemon lifecycle ──────────────────────────────────────────────────────────

def _spawn_daemon(persona_dir: Path | None = None) -> bool:
    """Spawn the my_brain.py daemon subprocess. Returns True on success."""
    global _proc

    brain_path = resolve_brain_path(persona_dir)
    if brain_path is None:
        logger.warning("cali brain daemon: cannot spawn — my_brain.py not found")
        return False

    python_exe = sys.executable
    cwd = brain_path.parent

    for attempt in range(_DAEMON_SPAWN_RETRIES + 1):
        try:
            logger.info(
                "cali brain daemon: spawning (attempt %d): %s %s daemon",
                attempt + 1,
                python_exe,
                brain_path,
            )
            _proc = subprocess.Popen(
                [python_exe, str(brain_path), "daemon"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,  # line-buffered
                cwd=str(cwd),
            )

            # Wait for the readiness marker
            ready_line = _read_with_timeout(_proc.stdout, _READINESS_TIMEOUT_SECONDS)
            if ready_line is None:
                logger.warning("cali brain daemon: readiness timeout")
                _proc.kill()
                _proc = None
                continue
            try:
                ready = json.loads(ready_line)
            except json.JSONDecodeError:
                logger.warning("cali brain daemon: bad readiness JSON: %r", ready_line)
                _proc.kill()
                _proc = None
                continue
            if not ready.get("daemon_ready"):
                logger.warning("cali brain daemon: unexpected readiness frame: %r", ready)
                _proc.kill()
                _proc = None
                continue
            logger.info(
                "cali brain daemon: ready (pid=%s, cwd=%s, cmds=%s)",
                ready.get("pid"),
                ready.get("cwd"),
                ready.get("supported_cmds"),
            )
            return True
        except Exception:  # noqa: BLE001
            logger.exception("cali brain daemon: spawn failed (attempt %d)", attempt + 1)
            if _proc:
                try:
                    _proc.kill()
                except Exception:  # noqa: BLE001
                    pass
                _proc = None
            time.sleep(0.5 * (attempt + 1))

    logger.warning("cali brain daemon: all spawn attempts failed")
    return False


def _read_with_timeout(stream, timeout: float) -> str | None:
    """Read one line from a pipe with a timeout. Returns None on timeout/EOF."""
    if stream is None:
        return None
    # subprocess pipes are blocking by default — wrap in a thread with timeout
    result: list[str | None] = [None]

    def _reader():
        try:
            result[0] = stream.readline()
        except Exception:  # noqa: BLE001
            result[0] = None

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None
    line = result[0]
    if not line:
        return None
    return line


def _ensure_alive(persona_dir: Path | None = None) -> bool:
    """Ensure the daemon is alive. Spawn if not. Returns True if usable."""
    global _proc
    if _proc is not None and _proc.poll() is None:
        return True
    if _proc is not None:
        # Dead. Clean up.
        _proc = None
    return _spawn_daemon(persona_dir)


def shutdown() -> None:
    """Cleanly shut down the daemon if running."""
    global _proc
    with _proc_lock:
        if _proc is None or _proc.poll() is not None:
            _proc = None
            return
        try:
            _send_raw({"id": -1, "cmd": "shutdown"}, timeout=2.0)
        except Exception:  # noqa: BLE001
            pass
        try:
            _proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            try:
                _proc.kill()
            except Exception:  # noqa: BLE001
                pass
        _proc = None


atexit.register(shutdown)


# ── IPC ───────────────────────────────────────────────────────────────────────

def _send_raw(req: dict, timeout: float = _REQUEST_TIMEOUT_SECONDS) -> dict:
    """Send a JSON request, read the response. Assumes _proc is alive + locked."""
    if _proc is None or _proc.stdin is None or _proc.stdout is None:
        return {"ok": False, "error": "daemon unavailable: no process"}
    try:
        line = json.dumps(req) + "\n"
        _proc.stdin.write(line)
        _proc.stdin.flush()
    except (BrokenPipeError, OSError) as exc:
        return {"ok": False, "error": f"daemon write failed: {exc}"}

    resp_line = _read_with_timeout(_proc.stdout, timeout)
    if resp_line is None:
        return {"ok": False, "error": f"daemon read timeout ({timeout}s)"}
    try:
        return json.loads(resp_line)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"daemon bad json: {exc}", "raw": resp_line}


def _call(cmd: str, args: dict | None = None, *, persona_dir: Path | None = None, timeout: float | None = None) -> dict:
    """High-level call: ensures alive, sends, returns response dict.

    Thread-safe via _proc_lock. Per-call timeout overrides default.
    """
    global _next_id
    timeout = timeout or _REQUEST_TIMEOUT_SECONDS
    with _proc_lock:
        if not _ensure_alive(persona_dir):
            return {"ok": False, "error": "daemon unavailable: spawn failed"}
        req_id = _next_id
        _next_id += 1
        req = {"id": req_id, "cmd": cmd, "args": args or {}}
        return _send_raw(req, timeout=timeout)


# ── public API ────────────────────────────────────────────────────────────────

def boot(persona_dir: Path | None = None) -> dict:
    """Run the full boot command. Slow — call once per session."""
    return _call("boot", persona_dir=persona_dir, timeout=_BOOT_TIMEOUT_SECONDS)


def turn(message: str, *, persona_dir: Path | None = None) -> dict:
    """Per-message brain processing: gap_reaction + process-message merged."""
    return _call("turn", {"text": message}, persona_dir=persona_dir)


def log_response(text: str, *, persona_dir: Path | None = None) -> dict:
    """Log cali's response so meta_loop_caught can check it next turn."""
    return _call("log_response", {"text": text}, persona_dir=persona_dir)


def mark_initiation(*, persona_dir: Path | None = None) -> dict:
    """Reset initiation_required counter — cali just initiated unprompted."""
    return _call("mark_initiation", persona_dir=persona_dir)


def ping(*, persona_dir: Path | None = None) -> dict:
    """Liveness check. Cheap. Use to verify daemon is responsive."""
    return _call("ping", persona_dir=persona_dir, timeout=5.0)


# ── system message helper ─────────────────────────────────────────────────────

def build_brain_context_block(turn_result: dict) -> str:
    """Format a turn() result as a markdown block for injection into the
    framework's system message.

    Returns empty string if the turn had no output worth surfacing.
    """
    if not turn_result.get("ok"):
        return ""
    stdout = (turn_result.get("stdout") or "").strip()
    if not stdout:
        return ""
    return (
        "── cali brain (sidecar) ──\n"
        f"{stdout}\n"
        "── end cali brain ──"
    )
