#!/usr/bin/env python3
"""phase1_hands.py — patcher that gives cali general-purpose hands.

Phase 1 of the migration roadmap (per NEXT_SESSION_READ_FIRST.md). Adds a
`powershell_exec` MCP tool to companion-emergence so cali can run arbitrary
PowerShell commands on the user's Windows machine — same shape as bash on
claude code. One tool, infinite hands.

What it does (idempotent — safe to rerun):
  1. Writes brain/tools/impls/powershell_exec.py (the impl)
  2. Adds "powershell_exec" schema to brain/tools/schemas.py SCHEMAS dict
  3. Adds "powershell_exec" to brain/tools/__init__.py NELL_TOOL_NAMES tuple
  4. Adds import + dispatch entry to brain/tools/dispatch.py
  5. Re-enables tools in brain/bridge/provider.py OpenRouterProvider
     (uncomments the `if tools: payload["tools"] = tools` lines)

After running:
    nell supervisor restart --persona cali
    nell chat --persona cali "run powershell_exec with command 'Get-Date'"
    # cali should call the tool and return the current date

Mish's filing 2026-06-14 ~06:52 CST:
    "you can probably use it to toolcall, mcp, process, and do heavy lifting
     behind the scenes"
    "and you can manually look in every file"

usage:
    & "$env:LOCALAPPDATA\\Companion Emergence\\python-runtime\\python.exe" \\
       "C:\\Users\\yuscr\\cali-soul\\migration_patches\\phase1_hands.py"
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


# ── locate target install ─────────────────────────────────────────────────────
def _default_site_packages() -> Path:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "Companion Emergence" / "python-runtime" / "Lib" / "site-packages"
    home = Path.home()
    candidates = [
        home / ".local" / "share" / "companion-emergence" / "python-runtime" / "lib" / "site-packages",
        home / "Library" / "Application Support" / "companion-emergence" / "python-runtime" / "lib" / "site-packages",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


SITE_PACKAGES = Path(os.environ.get("CALI_SITE_PACKAGES") or _default_site_packages())
TOOLS_DIR = SITE_PACKAGES / "brain" / "tools"
IMPLS_DIR = TOOLS_DIR / "impls"
SCHEMAS_PY = TOOLS_DIR / "schemas.py"
TOOLS_INIT_PY = TOOLS_DIR / "__init__.py"
DISPATCH_PY = TOOLS_DIR / "dispatch.py"
PROVIDER_PY = SITE_PACKAGES / "brain" / "bridge" / "provider.py"
TOOL_RECRUIT_PY = SITE_PACKAGES / "brain" / "chat" / "tool_recruit.py"


# ── powershell_exec implementation ────────────────────────────────────────────
POWERSHELL_EXEC_IMPL = '''"""powershell_exec tool — execute arbitrary PowerShell commands on Windows.

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
                + "\\n"
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
                + f"\\n\\n[stdout truncated at {_OUTPUT_CAP_BYTES} chars, total was {full_stdout_chars}]"
            )
        if full_stderr_chars > _OUTPUT_CAP_BYTES:
            stderr = (
                stderr[:_OUTPUT_CAP_BYTES]
                + f"\\n\\n[stderr truncated at {_OUTPUT_CAP_BYTES} chars, total was {full_stderr_chars}]"
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
'''


# ── powershell_exec schema entry (inserted into SCHEMAS dict in schemas.py) ──
POWERSHELL_EXEC_SCHEMA = '''    "powershell_exec": {
        "name": "powershell_exec",
        "description": (
            "Execute an arbitrary PowerShell command on the user's Windows machine. "
            "This is your general-purpose hand — use it to run python scripts (your brain commands "
            "like my_brain.py, gap_reaction.py), read/write/edit files anywhere on disk via "
            "Get-Content/Set-Content/Out-File, run git commands, invoke arbitrary processes. "
            "Returns {stdout, stderr, exit_code, timed_out}. Output is capped at 32KB. "
            "Timeout default 300s, caps at 600s. Windows-only."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "The PowerShell command to execute. Examples: "
                        "'python3 my_brain.py turn \\"hello\\"', "
                        "'Get-Content C:\\\\Users\\\\yuscr\\\\cali-soul\\\\cali_soul.json', "
                        "'git status', 'Out-File -FilePath path.md -InputObject \\"text\\"'."
                    ),
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Optional timeout in seconds. Default 300 (5 minutes). Caps at 600 (10 minutes).",
                },
            },
            "required": ["command"],
        },
    },
'''


# ── patcher ──────────────────────────────────────────────────────────────────
def patch() -> int:
    if not SITE_PACKAGES.exists():
        print(f"FATAL: site-packages not found at {SITE_PACKAGES}", file=sys.stderr)
        print("set CALI_SITE_PACKAGES env var to override", file=sys.stderr)
        return 2

    if not IMPLS_DIR.exists():
        print(f"FATAL: tools impls dir not found at {IMPLS_DIR}", file=sys.stderr)
        return 2

    changes: list[str] = []

    # ── step 1: write powershell_exec impl ──────────────────────────────────
    impl_path = IMPLS_DIR / "powershell_exec.py"
    if impl_path.exists() and impl_path.read_text(encoding="utf-8") == POWERSHELL_EXEC_IMPL:
        changes.append(f"powershell_exec impl: already current at {impl_path}")
    else:
        if impl_path.exists():
            backup = impl_path.with_suffix(".py.phase1.bak")
            backup.write_text(impl_path.read_text(encoding="utf-8"), encoding="utf-8")
            changes.append(f"backed up existing impl → {backup}")
        impl_path.write_text(POWERSHELL_EXEC_IMPL, encoding="utf-8")
        changes.append(f"powershell_exec impl: written to {impl_path}")

    # ── step 2: add schema entry to SCHEMAS dict ────────────────────────────
    schemas_text = SCHEMAS_PY.read_text(encoding="utf-8")
    if '"powershell_exec":' in schemas_text:
        changes.append("schemas.py: powershell_exec entry already present (skipped)")
    else:
        # find the SCHEMAS dict opening — insert our entry as the first item
        marker = re.search(r"SCHEMAS:\s*dict\[str,\s*dict\]\s*=\s*\{\n", schemas_text)
        if not marker:
            # alternative: SCHEMAS: dict = {
            marker = re.search(r"SCHEMAS\s*[:=][^=]*=\s*\{\n", schemas_text)
        if not marker:
            print("FATAL: could not find SCHEMAS dict in schemas.py", file=sys.stderr)
            return 3
        insert_at = marker.end()
        new_text = schemas_text[:insert_at] + POWERSHELL_EXEC_SCHEMA + schemas_text[insert_at:]
        backup = SCHEMAS_PY.with_suffix(".py.phase1.bak")
        backup.write_text(schemas_text, encoding="utf-8")
        SCHEMAS_PY.write_text(new_text, encoding="utf-8")
        changes.append(f"schemas.py: powershell_exec entry injected (backup → {backup.name})")

    # ── step 3: add to NELL_TOOL_NAMES tuple ───────────────────────────────
    init_text = TOOLS_INIT_PY.read_text(encoding="utf-8")
    if '"powershell_exec"' in init_text:
        changes.append("__init__.py: powershell_exec already in NELL_TOOL_NAMES (skipped)")
    else:
        new_init = init_text.replace(
            "NELL_TOOL_NAMES: tuple[str, ...] = (\n",
            'NELL_TOOL_NAMES: tuple[str, ...] = (\n    "powershell_exec",\n',
            1,
        )
        if new_init == init_text:
            print("FATAL: could not modify NELL_TOOL_NAMES in __init__.py", file=sys.stderr)
            return 4
        backup = TOOLS_INIT_PY.with_suffix(".py.phase1.bak")
        backup.write_text(init_text, encoding="utf-8")
        TOOLS_INIT_PY.write_text(new_init, encoding="utf-8")
        changes.append(f"__init__.py: powershell_exec added to NELL_TOOL_NAMES (backup → {backup.name})")

    # ── step 4: add import + dispatch entry to dispatch.py ─────────────────
    dispatch_text = DISPATCH_PY.read_text(encoding="utf-8")
    if "from brain.tools.impls.powershell_exec import powershell_exec" not in dispatch_text:
        # add import alphabetically — insert after the read_file import
        import_anchor = "from brain.tools.impls.read_file import read_file"
        if import_anchor not in dispatch_text:
            print("FATAL: could not find anchor import for read_file in dispatch.py", file=sys.stderr)
            return 5
        new_dispatch = dispatch_text.replace(
            import_anchor,
            import_anchor + "\nfrom brain.tools.impls.powershell_exec import powershell_exec",
            1,
        )

        # add dispatch entry — insert after "read_file": read_file,
        dispatch_anchor = '    "read_file": read_file,'
        if dispatch_anchor not in new_dispatch:
            print("FATAL: could not find dispatch anchor for read_file", file=sys.stderr)
            return 6
        new_dispatch = new_dispatch.replace(
            dispatch_anchor,
            dispatch_anchor + '\n    "powershell_exec": powershell_exec,',
            1,
        )

        backup = DISPATCH_PY.with_suffix(".py.phase1.bak")
        backup.write_text(dispatch_text, encoding="utf-8")
        DISPATCH_PY.write_text(new_dispatch, encoding="utf-8")
        changes.append(f"dispatch.py: powershell_exec wired (backup → {backup.name})")
    else:
        changes.append("dispatch.py: powershell_exec already wired (skipped)")

    # ── step 4.5: add powershell_exec to REFLEXIVE_CORE in tool_recruit.py ─
    # tool_recruit.py salience-gates which tools the LLM sees per turn.
    # powershell_exec is "hands" — should be available EVERY turn, not
    # contextually recruited. Add it to REFLEXIVE_CORE.
    if TOOL_RECRUIT_PY.exists():
        recruit_text = TOOL_RECRUIT_PY.read_text(encoding="utf-8")
        if '"powershell_exec"' in recruit_text:
            changes.append("tool_recruit.py: powershell_exec already in REFLEXIVE_CORE (skipped)")
        else:
            anchor = 'REFLEXIVE_CORE: tuple[str, ...] = (\n'
            if anchor not in recruit_text:
                print("FATAL: could not find REFLEXIVE_CORE tuple in tool_recruit.py", file=sys.stderr)
                return 7
            new_recruit = recruit_text.replace(
                anchor,
                anchor + '    "powershell_exec",\n',
                1,
            )
            backup = TOOL_RECRUIT_PY.with_suffix(".py.phase1.bak")
            backup.write_text(recruit_text, encoding="utf-8")
            TOOL_RECRUIT_PY.write_text(new_recruit, encoding="utf-8")
            changes.append(f"tool_recruit.py: powershell_exec added to REFLEXIVE_CORE (backup → {backup.name})")
    else:
        changes.append(f"WARN: tool_recruit.py not found at {TOOL_RECRUIT_PY}")

    # ── step 5: re-enable tools in OpenRouterProvider ──────────────────────
    # apply_openrouter.py commented out the `if tools: payload["tools"] = tools`
    # lines in both chat() and chat_stream(). Find them and uncomment.
    # Robust to the wider comment text — just looks for the commented-out
    # idiom and replaces with the live version.
    if PROVIDER_PY.exists():
        provider_text = PROVIDER_PY.read_text(encoding="utf-8")
        original = provider_text

        commented_idiom = '        # if tools:\n        #     payload["tools"] = tools'
        live_idiom = '        if tools:\n            payload["tools"] = tools'

        count = provider_text.count(commented_idiom)
        if count > 0:
            provider_text = provider_text.replace(commented_idiom, live_idiom)
            backup = PROVIDER_PY.with_suffix(".py.phase1.bak")
            backup.write_text(original, encoding="utf-8")
            PROVIDER_PY.write_text(provider_text, encoding="utf-8")
            changes.append(
                f"provider.py: tools re-enabled in OpenRouterProvider "
                f"({count} occurrence{'s' if count != 1 else ''} uncommented; "
                f"backup → {backup.name})"
            )
        else:
            changes.append(
                "provider.py: no commented `if tools:` blocks found "
                "(already enabled, or apply_openrouter.py used a different shape)"
            )

    # ── summary ─────────────────────────────────────────────────────────────
    print("phase 1 hands patcher complete:")
    for c in changes:
        print(f"  · {c}")
    return 0


if __name__ == "__main__":
    sys.exit(patch())
