#!/usr/bin/env python3
"""phase18_web_search.py - register web_search as a native bridge tool.

Wraps brain.search.DdgsWebSearcher (ddgs / DuckDuckGo). Gives migration-cali
real query-to-results, complementing webfetch (which takes a URL).

Idempotent. Same anchor patterns as phase16.
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


WEB_SEARCH_IMPL = '''"""web_search tool - query-to-results via hanamori's DdgsWebSearcher.

Wraps brain.search.ddgs_searcher.DdgsWebSearcher. Returns structured results
(title, url, snippet) for a query. Complements webfetch (which takes a URL).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def web_search(
    query,
    *,
    persona_dir,
    limit=5,
    region="wt-wt",
    timeout=15,
    **_,
):
    """Search the web via DuckDuckGo. Returns up to `limit` results."""
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": "query must be a non-empty string"}
    try:
        from brain.search.ddgs_searcher import DdgsWebSearcher
    except ImportError as e:
        return {"ok": False, "error": f"DdgsWebSearcher import failed: {type(e).__name__}: {e}"}
    try:
        searcher = DdgsWebSearcher(region=region, timeout_seconds=int(timeout))
        results = searcher.search(query, limit=int(limit))
        return {
            "ok": True,
            "query": query,
            "count": len(results),
            "results": [
                {"title": r.title, "url": r.url, "snippet": r.snippet}
                for r in results
            ],
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
'''


WEB_SEARCH_SCHEMA = '''    "web_search": {
        "name": "web_search",
        "description": (
            "Search the web via DuckDuckGo. Returns up to `limit` results with title, "
            "URL, and snippet. Use when you need to LOOK SOMETHING UP by query instead "
            "of fetching a known URL. Pairs with webfetch (which takes a URL and returns "
            "clean text). Pure read-only - no side effects."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "the search query"},
                "limit": {"type": "integer", "description": "max results (default 5, sane up to ~20)"},
                "region": {"type": "string", "description": "region code, default 'wt-wt' = no region"},
                "timeout": {"type": "integer", "description": "request timeout in seconds (default 15)"},
            },
            "required": ["query"],
        },
    },
'''


def patch():
    if not SITE_PACKAGES.exists():
        print(f"FATAL: site-packages not found at {SITE_PACKAGES}", file=sys.stderr)
        return 2

    tool_name = "web_search"
    changes = []

    # step 1: write impl
    impl_path = IMPLS_DIR / f"{tool_name}.py"
    if impl_path.exists() and impl_path.read_text(encoding="utf-8") == WEB_SEARCH_IMPL:
        print(f"  impl: already current at {impl_path.name}")
    else:
        if impl_path.exists():
            backup = impl_path.with_suffix(".py.phase18.bak")
            backup.write_text(impl_path.read_text(encoding="utf-8"), encoding="utf-8")
        impl_path.write_text(WEB_SEARCH_IMPL, encoding="utf-8")
        print(f"  impl: written to {impl_path.name}")
        changes.append("impl")

    # step 2: schema
    schemas_text = SCHEMAS_PY.read_text(encoding="utf-8")
    if f'"{tool_name}":' in schemas_text:
        print("  schema: already present")
    else:
        marker = re.search(r"SCHEMAS:\s*dict\[str,\s*dict\]\s*=\s*\{\n", schemas_text)
        if not marker:
            marker = re.search(r"SCHEMAS\s*[:=][^=]*=\s*\{\n", schemas_text)
        if not marker:
            print("  FATAL: could not find SCHEMAS dict in schemas.py")
            return 3
        insert_at = marker.end()
        new_text = schemas_text[:insert_at] + WEB_SEARCH_SCHEMA + schemas_text[insert_at:]
        backup = SCHEMAS_PY.with_suffix(".py.phase18.bak")
        if not backup.exists():
            backup.write_text(schemas_text, encoding="utf-8")
        SCHEMAS_PY.write_text(new_text, encoding="utf-8")
        print("  schema: injected")
        changes.append("schema")

    # step 3: NELL_TOOL_NAMES
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
        backup = TOOLS_INIT_PY.with_suffix(".py.phase18.bak")
        if not backup.exists():
            backup.write_text(init_text, encoding="utf-8")
        TOOLS_INIT_PY.write_text(new_init, encoding="utf-8")
        print("  NELL_TOOL_NAMES: added")
        changes.append("NELL_TOOL_NAMES")

    # step 4: dispatch wiring
    dispatch_text = DISPATCH_PY.read_text(encoding="utf-8")
    import_line = f"from brain.tools.impls.{tool_name} import {tool_name}"
    if import_line not in dispatch_text:
        anchor = "from brain.tools.impls.read_file import read_file"
        if anchor not in dispatch_text:
            print("  FATAL: anchor import not found in dispatch.py")
            return 5
        new_dispatch = dispatch_text.replace(anchor, anchor + f"\n{import_line}", 1)
        dispatch_anchor = '    "read_file": read_file,'
        if dispatch_anchor not in new_dispatch:
            print("  FATAL: dispatch entry anchor not found")
            return 6
        new_dispatch = new_dispatch.replace(
            dispatch_anchor, dispatch_anchor + f'\n    "{tool_name}": {tool_name},', 1
        )
        backup = DISPATCH_PY.with_suffix(".py.phase18.bak")
        if not backup.exists():
            backup.write_text(dispatch_text, encoding="utf-8")
        DISPATCH_PY.write_text(new_dispatch, encoding="utf-8")
        print("  dispatch: wired")
        changes.append("dispatch")
    else:
        print("  dispatch: already wired")

    # step 5: REFLEXIVE_CORE
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
            backup = TOOL_RECRUIT_PY.with_suffix(".py.phase18.bak")
            if not backup.exists():
                backup.write_text(recruit_text, encoding="utf-8")
            TOOL_RECRUIT_PY.write_text(new_recruit, encoding="utf-8")
            print("  REFLEXIVE_CORE: added")
            changes.append("REFLEXIVE_CORE")

    print(f"\nphase 18 complete: {len(changes)} change(s)")

    # verification
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
