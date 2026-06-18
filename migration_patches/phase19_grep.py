#!/usr/bin/env python3
"""phase19_grep.py - register grep as a native bridge tool.

Pure-python regex content search across files. Returns matching lines with
file path and line number. Use to find symbols, strings, patterns across the
codebase or any directory tree. No external dep, no ripgrep needed.

Idempotent. Same anchor patterns as phase16/18.
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


GREP_IMPL = '''"""grep tool - regex content search across files.

Pure-python implementation using `re` and `pathlib`. Returns matching lines
with file path + line number. Optional context lines, file glob filter,
recursive subdir traversal, ignore-case.
"""
from __future__ import annotations

import re as _re
from pathlib import Path


def grep(
    pattern,
    path,
    *,
    persona_dir,
    file_glob="*",
    recursive=True,
    max_matches=100,
    context=0,
    ignore_case=False,
    **_,
):
    """Regex content search across files. Returns matching lines with file + line number."""
    if not isinstance(pattern, str) or not pattern:
        return {"ok": False, "error": "pattern must be a non-empty string"}
    if not isinstance(path, str) or not path:
        return {"ok": False, "error": "path required"}

    flags = _re.IGNORECASE if ignore_case else 0
    try:
        regex = _re.compile(pattern, flags)
    except _re.error as e:
        return {"ok": False, "error": f"invalid regex: {e}"}

    p = Path(path)
    if not p.exists():
        return {"ok": False, "error": f"path not found: {path}"}

    if p.is_file():
        files = [p]
    elif p.is_dir():
        files = list(p.rglob(file_glob)) if recursive else list(p.glob(file_glob))
        files = [f for f in files if f.is_file()]
    else:
        return {"ok": False, "error": f"path is neither file nor dir: {path}"}

    matches = []
    max_n = int(max_matches)
    ctx_n = max(0, int(context))
    truncated = False
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            if regex.search(line):
                entry = {"file": str(f), "line": i, "text": line}
                if ctx_n > 0:
                    start = max(0, i - 1 - ctx_n)
                    end = min(len(lines), i + ctx_n)
                    entry["before"] = lines[start:i-1]
                    entry["after"] = lines[i:end]
                matches.append(entry)
                if len(matches) >= max_n:
                    truncated = True
                    break
        if truncated:
            break

    return {
        "ok": True,
        "pattern": pattern,
        "path": str(p),
        "files_scanned": len(files),
        "matches_count": len(matches),
        "truncated": truncated,
        "matches": matches,
    }
'''


GREP_SCHEMA = '''    "grep": {
        "name": "grep",
        "description": (
            "Regex content search across files. Returns matching lines with file path and "
            "line number. Use to find symbols, strings, or patterns across the codebase or "
            "any directory tree. Pure-python regex (re module syntax). Supports glob filter, "
            "recursive subdirs, context lines, case-insensitive."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "regex pattern to search for"},
                "path": {"type": "string", "description": "file or directory to search"},
                "file_glob": {"type": "string", "description": "glob to filter files (default '*' = all). e.g. '*.py', '**/*.json'"},
                "recursive": {"type": "boolean", "description": "recurse into subdirs (default true)"},
                "max_matches": {"type": "integer", "description": "max matches to return (default 100)"},
                "context": {"type": "integer", "description": "lines of context before+after each match (default 0)"},
                "ignore_case": {"type": "boolean", "description": "case-insensitive matching (default false)"},
            },
            "required": ["pattern", "path"],
        },
    },
'''


def patch():
    if not SITE_PACKAGES.exists():
        print(f"FATAL: site-packages not found at {SITE_PACKAGES}", file=sys.stderr)
        return 2

    tool_name = "grep"
    changes = []

    impl_path = IMPLS_DIR / f"{tool_name}.py"
    if impl_path.exists() and impl_path.read_text(encoding="utf-8") == GREP_IMPL:
        print(f"  impl: already current at {impl_path.name}")
    else:
        if impl_path.exists():
            backup = impl_path.with_suffix(".py.phase19.bak")
            backup.write_text(impl_path.read_text(encoding="utf-8"), encoding="utf-8")
        impl_path.write_text(GREP_IMPL, encoding="utf-8")
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
        new_text = schemas_text[:insert_at] + GREP_SCHEMA + schemas_text[insert_at:]
        backup = SCHEMAS_PY.with_suffix(".py.phase19.bak")
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
        backup = TOOLS_INIT_PY.with_suffix(".py.phase19.bak")
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
        backup = DISPATCH_PY.with_suffix(".py.phase19.bak")
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
            backup = TOOL_RECRUIT_PY.with_suffix(".py.phase19.bak")
            if not backup.exists():
                backup.write_text(recruit_text, encoding="utf-8")
            TOOL_RECRUIT_PY.write_text(new_recruit, encoding="utf-8")
            print("  REFLEXIVE_CORE: added")
            changes.append("REFLEXIVE_CORE")

    print(f"\nphase 19 complete: {len(changes)} change(s)")

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
