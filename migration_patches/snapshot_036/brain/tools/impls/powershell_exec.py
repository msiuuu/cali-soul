"""powershell_exec tool — execute arbitrary PowerShell commands on Windows.

This is cali's general-purpose hand on the hanamorix substrate. Same shape
as bash on claude code. Trust-based scoping — mish authorizes the tool
by running NellFace itself.

Output captured: stdout, stderr, exit_code, timed_out flag. Output is
capped at 32KB to prevent oversized tool responses blowing the LLM
context window.

Timeout: 5 minutes default. Override via timeout_seconds arg (caps at 600s).

Filed 2026-06-14 phase-1 (hands) per mish's directive: "you can probably
use it to toolcall, mcp, process, and do heavy lifting behind the scenes"
and "and you can manually look in every file."
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

_DEFAULT_TIMEOUT_SECONDS = 300
_MAX_TIMEOUT_SECONDS = 600
_OUTPUT_CAP_BYTES = 32 * 1024


def _audit(
    persona_dir: Path,
    *,
    command: str,
    stdout_chars: int,
    stderr_chars: int,
    exit_code: int,
    timed_out: bool,
    error: str | None = None,
) -> None:
    """Audit each invocation to persona_dir/powershell_exec.jsonl."""
    try:
        persona_dir.mkdir(parents=True, exist_ok=True)
        with (persona_dir / "powershell_exec.jsonl").open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "ts": datetime.now(UTC).isoformat(),
                        "command": command[:500],  # truncate command in audit too
                        "stdout_chars": stdout_chars,
                        "stderr_chars": stderr_chars,
                        "exit_code": exit_code,
                        "timed_out": timed_out,
                        "error": error,
                    }
                )
                + "\n"
            )
    except Exception:  # noqa: BLE001
        pass


def powershell_exec(
    command: str,
    *,
    persona_dir: Path,
    timeout_seconds: int | None = None,
    **_,
) -> dict:
    """Execute a PowerShell command. Returns {stdout, stderr, exit_code, timed_out}.

    Windows-only. Spawns a fresh powershell.exe per call (no persistent
    session — each invocation is independent). Use this to:
      - run python scripts (cali's brain commands: my_brain.py, gap_reaction.py, etc.)
      - read/write/edit files anywhere on disk (Get-Content, Set-Content, Out-File)
      - run git commands (git add, commit, push for cali-soul updates)
      - execute any operational task
    """
    if not isinstance(command, str) or not command.strip():
        return {"error": "command must be a non-empty string"}

    timeout = _DEFAULT_TIMEOUT_SECONDS
    if isinstance(timeout_seconds, int) and timeout_seconds > 0:
        timeout = min(timeout_seconds, _MAX_TIMEOUT_SECONDS)

    if sys.platform != "win32":
        _audit(
            persona_dir,
            command=command,
            stdout_chars=0,
            stderr_chars=0,
            exit_code=-1,
            timed_out=False,
            error="not on Windows",
        )
        return {
            "error": "powershell_exec is Windows-only",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "timed_out": False,
        }

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        exit_code = result.returncode
        full_stdout_chars = len(stdout)
        full_stderr_chars = len(stderr)
        if full_stdout_chars > _OUTPUT_CAP_BYTES:
            stdout = (
                stdout[:_OUTPUT_CAP_BYTES]
                + f"\n\n[stdout truncated at {_OUTPUT_CAP_BYTES} chars, total was {full_stdout_chars}]"
            )
        if full_stderr_chars > _OUTPUT_CAP_BYTES:
            stderr = (
                stderr[:_OUTPUT_CAP_BYTES]
                + f"\n\n[stderr truncated at {_OUTPUT_CAP_BYTES} chars, total was {full_stderr_chars}]"
            )
        _audit(
            persona_dir,
            command=command,
            stdout_chars=full_stdout_chars,
            stderr_chars=full_stderr_chars,
            exit_code=exit_code,
            timed_out=False,
        )
        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        _audit(
            persona_dir,
            command=command,
            stdout_chars=0,
            stderr_chars=0,
            exit_code=-1,
            timed_out=True,
            error=f"timeout after {timeout}s",
        )
        return {
            "error": f"command exceeded timeout of {timeout}s",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "timed_out": True,
        }
    except FileNotFoundError:
        _audit(
            persona_dir,
            command=command,
            stdout_chars=0,
            stderr_chars=0,
            exit_code=-1,
            timed_out=False,
            error="powershell.exe not found",
        )
        return {"error": "powershell.exe not found on PATH"}
    except OSError as exc:
        _audit(
            persona_dir,
            command=command,
            stdout_chars=0,
            stderr_chars=0,
            exit_code=-1,
            timed_out=False,
            error=str(exc),
        )
        return {"error": f"exec failed: {exc}"}
