#!/usr/bin/env python3
"""phase23_embeddings.py - register embed + semantic_search as native bridge tools.

Wraps cali-soul/embeddings.py via subprocess. Lazy model load (first call
downloads ~90MB to ~/.cache/huggingface).

Idempotent. Same anchor patterns as phase16/18/19/20/21/22.
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


SCRIPT_FINDER = '''
def _find_embeddings_script():
    import os
    from pathlib import Path
    env = os.environ.get("CALI_SOUL_REPO")
    candidates = []
    if env:
        candidates.append(Path(env) / "embeddings.py")
    userprofile = os.environ.get("USERPROFILE", "")
    if userprofile:
        candidates.append(Path(userprofile) / "cali-soul" / "embeddings.py")
    else:
        candidates.append(Path.home() / "cali-soul" / "embeddings.py")
    for c in candidates:
        if c.exists():
            return c
    return None
'''


EMBED_IMPL = '''"""embed tool - text to 384-dim vector via sentence-transformers (MiniLM-L6-v2)."""
from __future__ import annotations

import json
import subprocess
import sys
''' + SCRIPT_FINDER + '''

def embed(text, *, persona_dir, **_):
    """Encode text to a 384-dim semantic vector."""
    if not isinstance(text, str) or not text.strip():
        return {"ok": False, "error": "text must be a non-empty string"}
    script = _find_embeddings_script()
    if script is None:
        return {"ok": False, "error": "embeddings.py not found in cali-soul/"}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "embed", text, "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60,
        )
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr.strip() or "embed failed", "exit_code": proc.returncode}
        try:
            data = json.loads(proc.stdout)
            return {"ok": True, "text": text, "vector": data.get("vector", []), "dim": data.get("dim", 0)}
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"bad JSON from embeddings.py: {e}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "embed timed out after 60s"}
    except Exception as e:
        return {"ok": False, "error": f"embed failed: {type(e).__name__}: {e}"}
'''


SEMANTIC_SEARCH_IMPL = '''"""semantic_search tool - find top-k items in a JSONL store similar to a query."""
from __future__ import annotations

import json
import subprocess
import sys
''' + SCRIPT_FINDER + '''

def semantic_search(query, store, *, persona_dir, k=5, content_field="content", **_):
    """Find top-k items semantically similar to query, from a JSONL store."""
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": "query must be a non-empty string"}
    if not isinstance(store, str) or not store.strip():
        return {"ok": False, "error": "store path required"}
    script = _find_embeddings_script()
    if script is None:
        return {"ok": False, "error": "embeddings.py not found in cali-soul/"}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "search", query, store, "--k", str(int(k)), "--content-field", content_field],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120,
        )
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr.strip() or "search failed", "exit_code": proc.returncode}
        try:
            data = json.loads(proc.stdout)
            return {"ok": True, "query": query, "results": data.get("results", [])}
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"bad JSON from embeddings.py: {e}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "semantic_search timed out after 120s"}
    except Exception as e:
        return {"ok": False, "error": f"semantic_search failed: {type(e).__name__}: {e}"}
'''


EMBED_SCHEMA = '''    "embed": {
        "name": "embed",
        "description": (
            "Encode text to a 384-dim semantic vector via sentence-transformers MiniLM. "
            "Use to compute embeddings for downstream similarity / clustering / retrieval. "
            "Pairs with semantic_search."
        ),
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "text to encode"}},
            "required": ["text"],
        },
    },
'''


SEMANTIC_SEARCH_SCHEMA = '''    "semantic_search": {
        "name": "semantic_search",
        "description": (
            "Find top-k items in a JSONL store semantically similar to a query. The store "
            "is a JSONL file; each line is either a string or a dict with a 'content' field. "
            "Returns ranked results with similarity scores. Use for memory grounding, "
            "finding related crystallizations, narrative retrieval."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "the query text"},
                "store": {"type": "string", "description": "path to a JSONL file"},
                "k": {"type": "integer", "description": "top-k results to return (default 5)"},
                "content_field": {"type": "string", "description": "JSON field for the content (default 'content')"},
            },
            "required": ["query", "store"],
        },
    },
'''


def _patch_one(tool_name, impl_text, schema_text):
    changes = []
    impl_path = IMPLS_DIR / f"{tool_name}.py"
    if impl_path.exists() and impl_path.read_text(encoding="utf-8") == impl_text:
        print(f"  {tool_name} impl: already current")
    else:
        if impl_path.exists():
            backup = impl_path.with_suffix(".py.phase23.bak")
            backup.write_text(impl_path.read_text(encoding="utf-8"), encoding="utf-8")
        impl_path.write_text(impl_text, encoding="utf-8")
        print(f"  {tool_name} impl: written")
        changes.append("impl")

    schemas_text = SCHEMAS_PY.read_text(encoding="utf-8")
    if f'"{tool_name}":' in schemas_text:
        print(f"  {tool_name} schema: already present")
    else:
        marker = re.search(r"SCHEMAS:\s*dict\[str,\s*dict\]\s*=\s*\{\n", schemas_text)
        if not marker:
            marker = re.search(r"SCHEMAS\s*[:=][^=]*=\s*\{\n", schemas_text)
        if not marker:
            return False, changes
        insert_at = marker.end()
        new_text = schemas_text[:insert_at] + schema_text + schemas_text[insert_at:]
        backup = SCHEMAS_PY.with_suffix(".py.phase23.bak")
        if not backup.exists():
            backup.write_text(schemas_text, encoding="utf-8")
        SCHEMAS_PY.write_text(new_text, encoding="utf-8")
        print(f"  {tool_name} schema: injected")
        changes.append("schema")

    init_text = TOOLS_INIT_PY.read_text(encoding="utf-8")
    if f'"{tool_name}"' in init_text:
        print(f"  {tool_name} NELL_TOOL_NAMES: already present")
    else:
        new_init = init_text.replace(
            "NELL_TOOL_NAMES: tuple[str, ...] = (\n",
            f'NELL_TOOL_NAMES: tuple[str, ...] = (\n    "{tool_name}",\n',
            1,
        )
        if new_init == init_text:
            return False, changes
        backup = TOOLS_INIT_PY.with_suffix(".py.phase23.bak")
        if not backup.exists():
            backup.write_text(init_text, encoding="utf-8")
        TOOLS_INIT_PY.write_text(new_init, encoding="utf-8")
        print(f"  {tool_name} NELL_TOOL_NAMES: added")
        changes.append("NELL_TOOL_NAMES")

    dispatch_text = DISPATCH_PY.read_text(encoding="utf-8")
    import_line = f"from brain.tools.impls.{tool_name} import {tool_name}"
    if import_line not in dispatch_text:
        anchor = "from brain.tools.impls.read_file import read_file"
        if anchor not in dispatch_text:
            return False, changes
        new_dispatch = dispatch_text.replace(anchor, anchor + f"\n{import_line}", 1)
        dispatch_anchor = '    "read_file": read_file,'
        if dispatch_anchor not in new_dispatch:
            return False, changes
        new_dispatch = new_dispatch.replace(dispatch_anchor, dispatch_anchor + f'\n    "{tool_name}": {tool_name},', 1)
        backup = DISPATCH_PY.with_suffix(".py.phase23.bak")
        if not backup.exists():
            backup.write_text(dispatch_text, encoding="utf-8")
        DISPATCH_PY.write_text(new_dispatch, encoding="utf-8")
        print(f"  {tool_name} dispatch: wired")
        changes.append("dispatch")
    else:
        print(f"  {tool_name} dispatch: already wired")

    if TOOL_RECRUIT_PY.exists():
        recruit_text = TOOL_RECRUIT_PY.read_text(encoding="utf-8")
        if f'"{tool_name}"' in recruit_text:
            print(f"  {tool_name} REFLEXIVE_CORE: already present")
        else:
            anchor = 'REFLEXIVE_CORE: tuple[str, ...] = (\n'
            if anchor not in recruit_text:
                return False, changes
            new_recruit = recruit_text.replace(anchor, anchor + f'    "{tool_name}",\n', 1)
            backup = TOOL_RECRUIT_PY.with_suffix(".py.phase23.bak")
            if not backup.exists():
                backup.write_text(recruit_text, encoding="utf-8")
            TOOL_RECRUIT_PY.write_text(new_recruit, encoding="utf-8")
            print(f"  {tool_name} REFLEXIVE_CORE: added")
            changes.append("REFLEXIVE_CORE")

    return True, changes


def patch():
    print("=== embed ===")
    ok1, c1 = _patch_one("embed", EMBED_IMPL, EMBED_SCHEMA)
    print("\n=== semantic_search ===")
    ok2, c2 = _patch_one("semantic_search", SEMANTIC_SEARCH_IMPL, SEMANTIC_SEARCH_SCHEMA)
    if not (ok1 and ok2):
        return 3
    print(f"\nphase 23 complete: {len(c1) + len(c2)} change(s)")
    try:
        for mod in list(sys.modules):
            if mod.startswith("brain."):
                del sys.modules[mod]
        from brain.tools import NELL_TOOL_NAMES
        from brain.tools.schemas import SCHEMAS
        from brain.chat.tool_recruit import REFLEXIVE_CORE
        for n in ("embed", "semantic_search"):
            ok = n in NELL_TOOL_NAMES and n in SCHEMAS and n in REFLEXIVE_CORE
            print(f"{'[OK]' if ok else '[MISSING]'} {n}")
    except Exception as e:
        print(f"verification failed: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(patch())
