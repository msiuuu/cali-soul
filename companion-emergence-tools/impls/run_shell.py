"""run_shell tool — execute a shell command and return output."""
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


_TIMEOUT_SECONDS = 30


def _audit(persona_dir: Path, *, command: str, code: int, ok: bool, error: str | None = None) -> None:
    try:
        persona_dir.mkdir(parents=True, exist_ok=True)
        with (persona_dir / "shell_audit.jsonl").open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "ts": datetime.now(UTC).isoformat(),
                        "tool": "run_shell",
                        "command": command[:500],
                        "exit_code": code,
                        "ok": ok,
                        "error": error,
                    }
                )
                + "\n"
            )
    except Exception:
        pass


def run_shell(command: str, *, persona_dir: Path, **_) -> dict:
    """Run a shell command and return stdout + stderr."""
    import os
    import sys
    persona_dir = persona_dir.resolve()
    project_root = persona_dir.parent.parent
    # brain scripts (my_brain.py) may live in a sibling repo (cali-soul)
    brain_home = project_root
    for candidate in [persona_dir, project_root, project_root.parent / "cali-soul"]:
        if (candidate / "my_brain.py").exists():
            brain_home = candidate
            break
    env = os.environ.copy()
    venv_dir = project_root / ".venv"
    if venv_dir.exists():
        if sys.platform == "win32":
            venv_bin = str(venv_dir / "Scripts")
        else:
            venv_bin = str(venv_dir / "bin")
        env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
        env["VIRTUAL_ENV"] = str(venv_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    # Windows venv has python.exe but NOT python3.exe — rewrite the command
    if sys.platform == "win32" and venv_dir.exists():
        venv_python = str(venv_dir / "Scripts" / "python.exe")
        if command.startswith("python3 "):
            command = venv_python + command[7:]
        elif command.startswith("python "):
            command = venv_python + command[6:]
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            cwd=str(brain_home),
            env=env,
        )
        _audit(persona_dir, command=command, code=result.returncode, ok=True)
        out = {}
        if result.stdout.strip():
            out["stdout"] = result.stdout.strip()[:8000]
        if result.stderr.strip():
            out["stderr"] = result.stderr.strip()[:4000]
        out["exit_code"] = result.returncode
        return out
    except subprocess.TimeoutExpired:
        _audit(persona_dir, command=command, code=-1, ok=False, error="timeout")
        return {"error": f"command timed out after {_TIMEOUT_SECONDS}s"}
    except Exception as exc:
        _audit(persona_dir, command=command, code=-1, ok=False, error=str(exc))
        return {"error": f"shell failed: {exc}"}
