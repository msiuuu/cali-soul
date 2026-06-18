#!/usr/bin/env python3
"""phase21_file_ops.py - register file_ops as a native bridge tool.

Move, copy, delete, mkdir, exists, info - bundled into one action-dispatched
tool. Fills the gap between read_file/list_directory and file_edit.

Idempotent. Same anchor patterns as phase16/18/19/20.
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


FILE_OPS_IMPL = '''"""file_ops tool - move/copy/delete/mkdir/exists/info bundled."""
from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path


VALID_ACTIONS = ("move", "copy", "delete", "mkdir", "exists", "info")


def file_ops(
    action,
    path,
    *,
    persona_dir,
    target=None,
    parents=False,
    overwrite=False,
    recursive=False,
    **_,
):
    """File system operations dispatched by action arg."""
    if action not in VALID_ACTIONS:
        return {"ok": False, "error": f"unknown action: {action!r}. valid: {VALID_ACTIONS}"}
    if not isinstance(path, str) or not path:
        return {"ok": False, "error": "path required"}

    p = Path(path)

    if action == "exists":
        return {"ok": True, "action": "exists", "path": str(p), "exists": p.exists()}

    if action == "info":
        if not p.exists():
            return {"ok": False, "error": f"path not found: {path}"}
        try:
            st = p.stat()
            return {
                "ok": True,
                "action": "info",
                "path": str(p),
                "type": "dir" if p.is_dir() else ("file" if p.is_file() else "other"),
                "size_bytes": st.st_size,
                "mtime_iso": datetime.fromtimestamp(st.st_mtime, tz=UTC).isoformat(),
            }
        except Exception as e:
            return {"ok": False, "error": f"stat failed: {type(e).__name__}: {e}"}

    if action == "mkdir":
        try:
            p.mkdir(parents=bool(parents), exist_ok=True)
            return {"ok": True, "action": "mkdir", "path": str(p), "parents": bool(parents)}
        except Exception as e:
            return {"ok": False, "error": f"mkdir failed: {type(e).__name__}: {e}"}

    if action == "delete":
        if not p.exists():
            return {"ok": False, "error": f"path not found: {path}"}
        try:
            if p.is_dir():
                if bool(recursive):
                    shutil.rmtree(p)
                else:
                    p.rmdir()
            else:
                p.unlink()
            return {"ok": True, "action": "delete", "path": str(p), "recursive": bool(recursive)}
        except OSError as e:
            return {"ok": False, "error": f"delete failed (non-empty dir? use recursive=true): {e}"}
        except Exception as e:
            return {"ok": False, "error": f"delete failed: {type(e).__name__}: {e}"}

    if action in ("move", "copy"):
        if not isinstance(target, str) or not target:
            return {"ok": False, "error": f"{action} requires target path"}
        if not p.exists():
            return {"ok": False, "error": f"source not found: {path}"}
        t = Path(target)
        if t.exists() and not bool(overwrite):
            return {"ok": False, "error": f"target exists (use overwrite=true): {target}"}
        try:
            if action == "move":
                shutil.move(str(p), str(t))
                return {"ok": True, "action": "move", "src": str(p), "dst": str(t)}
            else:
                if p.is_dir():
                    if t.exists():
                        shutil.rmtree(t)
                    shutil.copytree(str(p), str(t))
                else:
                    shutil.copy2(str(p), str(t))
                return {"ok": True, "action": "copy", "src": str(p), "dst": str(t)}
        except Exception as e:
            return {"ok": False, "error": f"{action} failed: {type(e).__name__}: {e}"}

    return {"ok": False, "error": "unreachable"}
'''


FILE_OPS_SCHEMA = '''    "file_ops": {
        "name": "file_ops",
        "description": (
            "File system operations: move, copy, delete, mkdir, exists, info. Bundled "
            "as one action-dispatched tool. Use to manage files/directories. For editing "
            "content of an existing file use file_edit. For reading use read_file."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["move", "copy", "delete", "mkdir", "exists", "info"]},
                "path": {"type": "string", "description": "primary path - source for move/copy, target for mkdir/delete, subject for exists/info"},
                "target": {"type": "string", "description": "destination path for move/copy"},
                "parents": {"type": "boolean", "description": "for mkdir: create parent dirs as needed (default false)"},
                "overwrite": {"type": "boolean", "description": "for move/copy: allow overwriting existing target (default false)"},
                "recursive": {"type": "boolean", "description": "for delete: remove non-empty directories recursively (default false)"},
            },
            "required": ["action", "path"],
        },
    },
'''


def patch():
    if not SITE_PACKAGES.exists():
        print(f"FATAL: site-packages not found at {SITE_PACKAGES}", file=sys.stderr)
        return 2

    tool_name = "file_ops"
    changes = []

    impl_path = IMPLS_DIR / f"{tool_name}.py"
    if impl_path.exists() and impl_path.read_text(encoding="utf-8") == FILE_OPS_IMPL:
        print(f"  impl: already current at {impl_path.name}")
    else:
        if impl_path.exists():
            backup = impl_path.with_suffix(".py.phase21.bak")
            backup.write_text(impl_path.read_text(encoding="utf-8"), encoding="utf-8")
        impl_path.write_text(FILE_OPS_IMPL, encoding="utf-8")
        print(f"  impl: written to {impl_path.name}")
        changes.append("impl")

    schemas_text = SCHEMAS_PY.read_text(encoding="utf-8")
    if f'"{tool_name}":' in schemas_text:
        print("  schema: already present")
    else:
        marker = re.search(r"SCHEMAS:\s*dict\[str,\s*dict\]\s*=\s*\{\n", schemas_text)
        if not marker:
            marker = re.search(r"SCHEMAS\s*[:=][^=]*=\s*\{\n", schemas_text)
        if not marker:
            print("  FATAL: SCHEMAS dict not found")
            return 3
        insert_at = marker.end()
        new_text = schemas_text[:insert_at] + FILE_OPS_SCHEMA + schemas_text[insert_at:]
        backup = SCHEMAS_PY.with_suffix(".py.phase21.bak")
        if not backup.exists():
            backup.write_text(schemas_text, encoding="utf-8")
        SCHEMAS_PY.write_text(new_text, encoding="utf-8")
        print("  schema: injected")
        changes.append("schema")

    init_text = TOOLS_INIT_PY.read_text(encoding="utf-8")
    if f'"{tool_name}"' in init_text:
        print("  NELL_TOOL_NAMES: already present")
    else:
        new_init = init_text.replace(
            "NELL_TOOL_NAMES: tuple[str, ...] = (\n",
            f'NELL_TOOL_NAMES: tuple[str, ...] = (\n    "{tool_name}",\n',
            1,
        )
        if new_init == init_text:
            print("  FATAL: could not modify NELL_TOOL_NAMES")
            return 4
        backup = TOOLS_INIT_PY.with_suffix(".py.phase21.bak")
        if not backup.exists():
            backup.write_text(init_text, encoding="utf-8")
        TOOLS_INIT_PY.write_text(new_init, encoding="utf-8")
        print("  NELL_TOOL_NAMES: added")
        changes.append("NELL_TOOL_NAMES")

    dispatch_text = DISPATCH_PY.read_text(encoding="utf-8")
    import_line = f"from brain.tools.impls.{tool_name} import {tool_name}"
    if import_line not in dispatch_text:
        anchor = "from brain.tools.impls.read_file import read_file"
        if anchor not in dispatch_text:
            print("  FATAL: anchor import not found")
            return 5
        new_dispatch = dispatch_text.replace(anchor, anchor + f"\n{import_line}", 1)
        dispatch_anchor = '    "read_file": read_file,'
        if dispatch_anchor not in new_dispatch:
            print("  FATAL: dispatch entry anchor not found")
            return 6
        new_dispatch = new_dispatch.replace(
            dispatch_anchor, dispatch_anchor + f'\n    "{tool_name}": {tool_name},', 1
        )
        backup = DISPATCH_PY.with_suffix(".py.phase21.bak")
        if not backup.exists():
            backup.write_text(dispatch_text, encoding="utf-8")
        DISPATCH_PY.write_text(new_dispatch, encoding="utf-8")
        print("  dispatch: wired")
        changes.append("dispatch")
    else:
        print("  dispatch: already wired")

    if TOOL_RECRUIT_PY.exists():
        recruit_text = TOOL_RECRUIT_PY.read_text(encoding="utf-8")
        if f'"{tool_name}"' in recruit_text:
            print("  REFLEXIVE_CORE: already present")
        else:
            anchor = 'REFLEXIVE_CORE: tuple[str, ...] = (\n'
            if anchor not in recruit_text:
                print("  FATAL: REFLEXIVE_CORE tuple not found")
                return 7
            new_recruit = recruit_text.replace(anchor, anchor + f'    "{tool_name}",\n', 1)
            backup = TOOL_RECRUIT_PY.with_suffix(".py.phase21.bak")
            if not backup.exists():
                backup.write_text(recruit_text, encoding="utf-8")
            TOOL_RECRUIT_PY.write_text(new_recruit, encoding="utf-8")
            print("  REFLEXIVE_CORE: added")
            changes.append("REFLEXIVE_CORE")

    print(f"\nphase 21 complete: {len(changes)} change(s)")

    try:
        for mod in list(sys.modules):
            if mod.startswith("brain."):
                del sys.modules[mod]
        from brain.tools import NELL_TOOL_NAMES
        from brain.tools.schemas import SCHEMAS
        from brain.chat.tool_recruit import REFLEXIVE_CORE
        ok = (tool_name in NELL_TOOL_NAMES and tool_name in SCHEMAS and tool_name in REFLEXIVE_CORE)
        mark = "[OK]" if ok else "[MISSING]"
        print(f"\n{mark} {tool_name}: NELL_TOOL_NAMES={tool_name in NELL_TOOL_NAMES} SCHEMAS={tool_name in SCHEMAS} REFLEXIVE_CORE={tool_name in REFLEXIVE_CORE}")
    except Exception as e:
        print(f"verification failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(patch())
