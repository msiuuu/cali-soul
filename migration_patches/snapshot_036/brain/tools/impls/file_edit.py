"""file_edit tool - exact-string file editing primitive.

Wraps cali-soul/file_edit.py via subprocess. The standalone script is canonical
(testable via CLI, JSON-stdin interface for multiline content).
"""
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


def file_edit(
    path,
    old_string,
    new_string,
    *,
    persona_dir,
    replace_all=False,
    backup=False,
    dry_run=False,
    **_,
):
    """Exact-string file edit with atomic write."""
    script = _find_script("file_edit.py", persona_dir)
    if script is None:
        return {"ok": False, "error": "file_edit.py not found in cali-soul/"}
    payload = {
        "path": path,
        "old": old_string,
        "new": new_string,
        "replace_all": bool(replace_all),
        "backup": bool(backup),
        "dry_run": bool(dry_run),
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--json-stdin"],
            input=json.dumps(payload),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "exit_code": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "file_edit timed out after 60s"}
    except Exception as e:
        return {"ok": False, "error": f"file_edit failed: {type(e).__name__}: {e}"}
