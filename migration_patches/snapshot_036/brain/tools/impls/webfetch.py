"""webfetch tool - URL -> clean text extraction."""
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


def webfetch(
    url,
    *,
    persona_dir,
    max_chars=0,
    raw=False,
    timeout=15,
    output_format="text",
    **_,
):
    """Fetch URL and extract clean text. Wraps cali-soul/webfetch.py."""
    script = _find_script("webfetch.py", persona_dir)
    if script is None:
        return {"ok": False, "error": "webfetch.py not found in cali-soul/"}
    args = [sys.executable, str(script), url, "--timeout", str(timeout)]
    if max_chars and int(max_chars) > 0:
        args.extend(["--max-chars", str(int(max_chars))])
    if raw:
        args.append("--raw")
    elif output_format == "json":
        args.append("--json")
    try:
        proc = subprocess.run(
            args,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=int(timeout) + 10,
        )
        result = {"ok": proc.returncode == 0, "exit_code": proc.returncode}
        if output_format == "json" and not raw and proc.returncode == 0:
            try:
                result["data"] = json.loads(proc.stdout)
            except json.JSONDecodeError:
                result["text"] = proc.stdout.strip()
        else:
            result["text"] = proc.stdout.strip()
        if proc.stderr.strip():
            result["stderr"] = proc.stderr.strip()
        return result
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"webfetch timed out"}
    except Exception as e:
        return {"ok": False, "error": f"webfetch failed: {type(e).__name__}: {e}"}
