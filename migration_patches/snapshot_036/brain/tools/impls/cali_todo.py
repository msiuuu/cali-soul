"""cali_todo tool - persistent task list with priorities, tags, status."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

def _find_script(name, persona_dir):
    """Find a script in cali-soul/. Tries CALI_SOUL_REPO env, persona_dir/cali-soul, USERPROFILE/cali-soul."""
    env_path = os.environ.get("CALI_SOUL_REPO")
    candidates = []
    if env_path:
        candidates.append(Path(env_path) / name)
    candidates.append(Path(persona_dir) / "cali-soul" / name)
    if sys.platform == "win32":
        userprofile = os.environ.get("USERPROFILE", "")
        if userprofile:
            candidates.append(Path(userprofile) / "cali-soul" / name)
    else:
        candidates.append(Path.home() / "cali-soul" / name)
    for c in candidates:
        if c.exists():
            return c
    return None


def cali_todo(
    action,
    *,
    persona_dir,
    text=None,
    priority="normal",
    tags=None,
    id_prefix=None,
    filter_status=None,
    filter_all=False,
    clear_done=False,
    clear_all=False,
    **_,
):
    """Persistent task list. Wraps cali-soul/cali_todo.py."""
    script = _find_script("cali_todo.py", persona_dir)
    if script is None:
        return {"ok": False, "error": "cali_todo.py not found in cali-soul/"}
    valid_actions = ("add", "list", "done", "undone", "remove", "clear", "status")
    if action not in valid_actions:
        return {"ok": False, "error": f"invalid action: {action} (valid: {valid_actions})"}
    args = [sys.executable, str(script), "--json", action]
    if action == "add":
        if not text:
            return {"ok": False, "error": "text required for add"}
        args.append(text)
        if priority in ("low", "normal", "high"):
            args.extend(["--priority", priority])
        for tag in (tags or []):
            args.extend(["--tag", str(tag)])
    elif action in ("done", "undone", "remove"):
        if not id_prefix:
            return {"ok": False, "error": f"id_prefix required for {action}"}
        args.append(id_prefix)
    elif action == "list":
        if filter_all:
            args.append("--all")
        if filter_status:
            args.extend(["--status", filter_status])
    elif action == "clear":
        if clear_done:
            args.append("--done")
        elif clear_all:
            args.append("--all")
        else:
            return {"ok": False, "error": "clear_done or clear_all required"}
    try:
        proc = subprocess.run(
            args,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
        result = {"ok": proc.returncode == 0, "exit_code": proc.returncode}
        if proc.stdout.strip():
            try:
                result["data"] = json.loads(proc.stdout)
            except json.JSONDecodeError:
                result["text"] = proc.stdout.strip()
        if proc.stderr.strip():
            result["stderr"] = proc.stderr.strip()
        return result
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "cali_todo timed out after 30s"}
    except Exception as e:
        return {"ok": False, "error": f"cali_todo failed: {type(e).__name__}: {e}"}
