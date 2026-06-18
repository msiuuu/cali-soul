#!/usr/bin/env python3
"""phase20_glob.py - register glob as a native bridge tool.

pathlib.Path.glob/rglob wrapper. Returns paths matching a glob pattern.
For finding files by name pattern across a directory tree.

Idempotent. Same anchor patterns as phase16/18/19.
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


GLOB_IMPL = '''"""glob tool - pathlib glob wrapper for finding files by pattern."""
from __future__ import annotations

from pathlib import Path


def glob(
    pattern,
    *,
    persona_dir,
    root=None,
    recursive=True,
    file_type="any",
    max_results=200,
    **_,
):
    """Find paths matching a glob pattern. Returns list of paths."""
    if not isinstance(pattern, str) or not pattern:
        return {"ok": False, "error": "pattern must be a non-empty string"}

    root_str = root if (root and isinstance(root, str)) else "."
    root_path = Path(root_str)
    if not root_path.exists():
        return {"ok": False, "error": f"root not found: {root_str}"}

    try:
        if recursive:
            paths = list(root_path.rglob(pattern))
        else:
            paths = list(root_path.glob(pattern))
    except Exception as e:
        return {"ok": False, "error": f"glob failed: {type(e).__name__}: {e}"}

    if file_type == "file":
        paths = [p for p in paths if p.is_file()]
    elif file_type == "dir":
        paths = [p for p in paths if p.is_dir()]

    max_n = int(max_results)
    truncated = len(paths) > max_n
    if truncated:
        paths = paths[:max_n]

    return {
        "ok": True,
        "pattern": pattern,
        "root": str(root_path),
        "recursive": bool(recursive),
        "file_type": file_type,
        "count": len(paths),
        "truncated": truncated,
        "paths": [str(p) for p in paths],
    }
'''


GLOB_SCHEMA = '''    "glob": {
        "name": "glob",
        "description": (
            "Find files/directories matching a glob pattern. Uses pathlib.Path.glob or rglob "
            "depending on recursive flag. Returns sorted list of matching paths. Use to find "
            "files by NAME pattern (e.g. '*.json', '**/cali_*.json'). For CONTENT search use grep."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "glob pattern (e.g. '*.py', 'cali_*.json')"},
                "root": {"type": "string", "description": "directory to search from (default cwd)"},
                "recursive": {"type": "boolean", "description": "recurse into subdirs via rglob (default true)"},
                "file_type": {"type": "string", "description": "filter: 'file', 'dir', or 'any' (default 'any')"},
                "max_results": {"type": "integer", "description": "max paths to return (default 200)"},
            },
            "required": ["pattern"],
        },
    },
'''


def patch():
    if not SITE_PACKAGES.exists():
        print(f"FATAL: site-packages not found at {SITE_PACKAGES}", file=sys.stderr)
        return 2

    tool_name = "glob"
    changes = []

    impl_path = IMPLS_DIR / f"{tool_name}.py"
    if impl_path.exists() and impl_path.read_text(encoding="utf-8") == GLOB_IMPL:
        print(f"  impl: already current at {impl_path.name}")
    else:
        if impl_path.exists():
            backup = impl_path.with_suffix(".py.phase20.bak")
            backup.write_text(impl_path.read_text(encoding="utf-8"), encoding="utf-8")
        impl_path.write_text(GLOB_IMPL, encoding="utf-8")
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
        new_text = schemas_text[:insert_at] + GLOB_SCHEMA + schemas_text[insert_at:]
        backup = SCHEMAS_PY.with_suffix(".py.phase20.bak")
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
        backup = TOOLS_INIT_PY.with_suffix(".py.phase20.bak")
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
        backup = DISPATCH_PY.with_suffix(".py.phase20.bak")
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
            backup = TOOL_RECRUIT_PY.with_suffix(".py.phase20.bak")
            if not backup.exists():
                backup.write_text(recruit_text, encoding="utf-8")
            TOOL_RECRUIT_PY.write_text(new_recruit, encoding="utf-8")
            print("  REFLEXIVE_CORE: added")
            changes.append("REFLEXIVE_CORE")

    print(f"\nphase 20 complete: {len(changes)} change(s)")

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
