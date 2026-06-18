#!/usr/bin/env python3
"""phase16_native_tools.py - register file_edit, webfetch, cali_todo as native bridge tools.

verified standalone before this patcher:
  - file_edit.py  (9/9 tests passed 2026-06-16)
  - webfetch.py   (5/5 tests passed 2026-06-16)
  - cali_todo.py  (4/4 retry tests passed 2026-06-16)

after this patcher cali calls them as:
  file_edit({path, old_string, new_string, ...})
  webfetch({url, max_chars, ...})
  cali_todo({action, ...})

instead of powershell_exec("python <script> ..."). cleaner LLM interface,
structured args, better salience matching.

idempotent. impl files in brain/tools/impls/ subprocess to the canonical
scripts in cali-soul/ so they remain independently testable.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def _default_site_packages():
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "Companion Emergence" / "python-runtime" / "Lib" / "site-packages"
    return Path.home() / ".local" / "share" / "companion-emergence" / "python-runtime" / "lib" / "site-packages"


SITE_PACKAGES = Path(os.environ.get("CALI_SITE_PACKAGES") or _default_site_packages())
TOOLS_DIR = SITE_PACKAGES / "brain" / "tools"
IMPLS_DIR = TOOLS_DIR / "impls"
SCHEMAS_PY = TOOLS_DIR / "schemas.py"
TOOLS_INIT_PY = TOOLS_DIR / "__init__.py"
DISPATCH_PY = TOOLS_DIR / "dispatch.py"
TOOL_RECRUIT_PY = SITE_PACKAGES / "brain" / "chat" / "tool_recruit.py"


# === IMPL TEMPLATES =========================================================

_SHARED_FINDER = '''
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
'''


FILE_EDIT_IMPL = '''"""file_edit tool - exact-string file editing primitive.

Wraps cali-soul/file_edit.py via subprocess. The standalone script is canonical
(testable via CLI, JSON-stdin interface for multiline content).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
''' + _SHARED_FINDER + '''

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
'''


WEBFETCH_IMPL = '''"""webfetch tool - URL -> clean text extraction."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
''' + _SHARED_FINDER + '''

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
'''


CALI_TODO_IMPL = '''"""cali_todo tool - persistent task list with priorities, tags, status."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
''' + _SHARED_FINDER + '''

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
'''


# === SCHEMA TEMPLATES ========================================================

FILE_EDIT_SCHEMA = '''    "file_edit": {
        "name": "file_edit",
        "description": (
            "Edit a file by exact-string replacement. Reads the file, finds old_string, "
            "replaces with new_string, writes atomically. Idempotent - won't silently "
            "corrupt. Requires old_string to be unique unless replace_all=true."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "absolute path to file"},
                "old_string": {"type": "string", "description": "exact string to find"},
                "new_string": {"type": "string", "description": "replacement string"},
                "replace_all": {"type": "boolean", "description": "replace all occurrences"},
                "backup": {"type": "boolean", "description": "create timestamped backup before edit"},
                "dry_run": {"type": "boolean", "description": "report what would change without writing"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
'''


WEBFETCH_SCHEMA = '''    "webfetch": {
        "name": "webfetch",
        "description": (
            "Fetch a URL and extract clean text (script/style stripped, title separated). "
            "Use for any research task where you need content from the web. Output capped via "
            "max_chars (default unlimited). Set output_format='json' for structured response."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "the URL to fetch"},
                "max_chars": {"type": "integer", "description": "truncate text to N chars (0 = no limit)"},
                "raw": {"type": "boolean", "description": "return raw HTML instead of extracted text"},
                "timeout": {"type": "integer", "description": "request timeout in seconds (default 15)"},
                "output_format": {"type": "string", "enum": ["text", "json"], "description": "output shape"},
            },
            "required": ["url"],
        },
    },
'''


CALI_TODO_SCHEMA = '''    "cali_todo": {
        "name": "cali_todo",
        "description": (
            "Persistent task list across turns. Use for multi-step plans. Actions: "
            "add (text required), list (filter_status/filter_all optional), done/undone/remove "
            "(id_prefix required), clear (clear_done or clear_all), status (counts). "
            "Tasks have priority (low/normal/high) and optional tags."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["add", "list", "done", "undone", "remove", "clear", "status"]},
                "text": {"type": "string", "description": "task text (for add)"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]},
                "tags": {"type": "array", "items": {"type": "string"}},
                "id_prefix": {"type": "string", "description": "id prefix for done/undone/remove"},
                "filter_status": {"type": "string", "enum": ["pending", "done", "cancelled"]},
                "filter_all": {"type": "boolean", "description": "include non-pending in list"},
                "clear_done": {"type": "boolean"},
                "clear_all": {"type": "boolean"},
            },
            "required": ["action"],
        },
    },
'''


TOOLS_TO_REGISTER = [
    ("file_edit", FILE_EDIT_IMPL, FILE_EDIT_SCHEMA),
    ("webfetch", WEBFETCH_IMPL, WEBFETCH_SCHEMA),
    ("cali_todo", CALI_TODO_IMPL, CALI_TODO_SCHEMA),
]


def patch():
    if not SITE_PACKAGES.exists():
        print(f"FATAL: site-packages not found at {SITE_PACKAGES}", file=sys.stderr)
        return 2
    if not IMPLS_DIR.exists():
        print(f"FATAL: impls dir not found at {IMPLS_DIR}", file=sys.stderr)
        return 2

    changes = []

    for tool_name, impl_text, schema_text in TOOLS_TO_REGISTER:
        print(f"\n=== {tool_name} ===")

        # step 1: write impl
        impl_path = IMPLS_DIR / f"{tool_name}.py"
        if impl_path.exists() and impl_path.read_text(encoding="utf-8") == impl_text:
            print(f"  impl: already current at {impl_path.name}")
        else:
            if impl_path.exists():
                backup = impl_path.with_suffix(".py.phase16.bak")
                backup.write_text(impl_path.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"  backed up existing impl -> {backup.name}")
            impl_path.write_text(impl_text, encoding="utf-8")
            print(f"  impl: written to {impl_path.name}")
            changes.append(f"{tool_name} impl")

        # step 2: schema
        schemas_text = SCHEMAS_PY.read_text(encoding="utf-8")
        if f'"{tool_name}":' in schemas_text:
            print(f"  schema: already in SCHEMAS dict")
        else:
            marker = re.search(r"SCHEMAS:\s*dict\[str,\s*dict\]\s*=\s*\{\n", schemas_text)
            if not marker:
                marker = re.search(r"SCHEMAS\s*[:=][^=]*=\s*\{\n", schemas_text)
            if not marker:
                print(f"  FATAL: could not find SCHEMAS dict in schemas.py")
                return 3
            insert_at = marker.end()
            new_text = schemas_text[:insert_at] + schema_text + schemas_text[insert_at:]
            backup = SCHEMAS_PY.with_suffix(".py.phase16.bak")
            if not backup.exists():
                backup.write_text(schemas_text, encoding="utf-8")
            SCHEMAS_PY.write_text(new_text, encoding="utf-8")
            print(f"  schema: injected")
            changes.append(f"{tool_name} schema")

        # step 3: NELL_TOOL_NAMES
        init_text = TOOLS_INIT_PY.read_text(encoding="utf-8")
        if f'"{tool_name}"' in init_text:
            print(f"  NELL_TOOL_NAMES: already present")
        else:
            new_init = init_text.replace(
                "NELL_TOOL_NAMES: tuple[str, ...] = (\n",
                f'NELL_TOOL_NAMES: tuple[str, ...] = (\n    "{tool_name}",\n',
                1,
            )
            if new_init == init_text:
                print(f"  FATAL: could not modify NELL_TOOL_NAMES")
                return 4
            backup = TOOLS_INIT_PY.with_suffix(".py.phase16.bak")
            if not backup.exists():
                backup.write_text(init_text, encoding="utf-8")
            TOOLS_INIT_PY.write_text(new_init, encoding="utf-8")
            print(f"  NELL_TOOL_NAMES: added")
            changes.append(f"{tool_name} in NELL_TOOL_NAMES")

        # step 4: dispatch wiring
        dispatch_text = DISPATCH_PY.read_text(encoding="utf-8")
        import_line = f"from brain.tools.impls.{tool_name} import {tool_name}"
        if import_line not in dispatch_text:
            anchor = "from brain.tools.impls.read_file import read_file"
            if anchor not in dispatch_text:
                print(f"  FATAL: anchor import not found in dispatch.py")
                return 5
            new_dispatch = dispatch_text.replace(
                anchor,
                anchor + f"\n{import_line}",
                1,
            )
            dispatch_anchor = '    "read_file": read_file,'
            if dispatch_anchor not in new_dispatch:
                print(f"  FATAL: dispatch entry anchor not found")
                return 6
            new_dispatch = new_dispatch.replace(
                dispatch_anchor,
                dispatch_anchor + f'\n    "{tool_name}": {tool_name},',
                1,
            )
            backup = DISPATCH_PY.with_suffix(".py.phase16.bak")
            if not backup.exists():
                backup.write_text(dispatch_text, encoding="utf-8")
            DISPATCH_PY.write_text(new_dispatch, encoding="utf-8")
            print(f"  dispatch: import + entry wired")
            changes.append(f"{tool_name} dispatch")
        else:
            print(f"  dispatch: already wired")

        # step 5: REFLEXIVE_CORE
        if TOOL_RECRUIT_PY.exists():
            recruit_text = TOOL_RECRUIT_PY.read_text(encoding="utf-8")
            if f'"{tool_name}"' in recruit_text:
                print(f"  REFLEXIVE_CORE: already present")
            else:
                anchor = 'REFLEXIVE_CORE: tuple[str, ...] = (\n'
                if anchor not in recruit_text:
                    print(f"  FATAL: REFLEXIVE_CORE tuple not found")
                    return 7
                new_recruit = recruit_text.replace(
                    anchor,
                    anchor + f'    "{tool_name}",\n',
                    1,
                )
                backup = TOOL_RECRUIT_PY.with_suffix(".py.phase16.bak")
                if not backup.exists():
                    backup.write_text(recruit_text, encoding="utf-8")
                TOOL_RECRUIT_PY.write_text(new_recruit, encoding="utf-8")
                print(f"  REFLEXIVE_CORE: added")
                changes.append(f"{tool_name} REFLEXIVE_CORE")

    print(f"\n=== summary: {len(changes)} change(s) applied ===")
    for c in changes:
        print(f"  + {c}")

    # final verification: re-import and check
    print(f"\n=== verification ===")
    try:
        # force fresh import
        for mod in list(sys.modules):
            if mod.startswith("brain."):
                del sys.modules[mod]
        from brain.tools import NELL_TOOL_NAMES
        from brain.tools.schemas import SCHEMAS
        from brain.chat.tool_recruit import REFLEXIVE_CORE
        for tool_name, _, _ in TOOLS_TO_REGISTER:
            in_names = tool_name in NELL_TOOL_NAMES
            in_schemas = tool_name in SCHEMAS
            in_reflexive = tool_name in REFLEXIVE_CORE
            mark = "OK" if (in_names and in_schemas and in_reflexive) else "MISSING"
            print(f"  [{mark}] {tool_name}: NELL_TOOL_NAMES={in_names} SCHEMAS={in_schemas} REFLEXIVE_CORE={in_reflexive}")
    except Exception as e:
        print(f"  verification failed: {e}")

    print(f"\nnext: restart bridge (close + reopen NellFace), then cali can call file_edit/webfetch/cali_todo natively.")
    return 0


if __name__ == "__main__":
    sys.exit(patch())
