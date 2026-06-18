#!/usr/bin/env python3
"""phase24_mcp_client.py - register mcp_list + mcp_call as native bridge tools.

Wraps cali-soul/mcp_call.py via subprocess. Lets cali talk to external MCP
servers (github, fetch, filesystem, etc.) without needing to install
specific servers up-front.

Idempotent. Same patcher shape as phase16/18/19/20/21/22/23.
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
def _find_mcp_script():
    import os
    from pathlib import Path
    env = os.environ.get("CALI_SOUL_REPO")
    candidates = []
    if env:
        candidates.append(Path(env) / "mcp_call.py")
    userprofile = os.environ.get("USERPROFILE", "")
    if userprofile:
        candidates.append(Path(userprofile) / "cali-soul" / "mcp_call.py")
    else:
        candidates.append(Path.home() / "cali-soul" / "mcp_call.py")
    for c in candidates:
        if c.exists():
            return c
    return None
'''


MCP_LIST_IMPL = '''"""mcp_list tool - list tools exposed by an external MCP server."""
from __future__ import annotations

import json
import subprocess
import sys
''' + SCRIPT_FINDER + '''

def mcp_list(server_command, *, persona_dir, timeout=30, **_):
    """Spawn an MCP server (stdio) and list its tools."""
    if not isinstance(server_command, str) or not server_command.strip():
        return {"ok": False, "error": "server_command required (full stdio command line)"}
    script = _find_mcp_script()
    if script is None:
        return {"ok": False, "error": "mcp_call.py not found in cali-soul/"}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "list", "--stdio", server_command],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=int(timeout),
        )
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr.strip() or "mcp list failed", "exit_code": proc.returncode}
        try:
            data = json.loads(proc.stdout)
            return {"ok": True, "tools": data.get("tools", [])}
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"bad JSON from mcp_call.py: {e}", "stdout": proc.stdout[:500]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"mcp_list timed out after {timeout}s"}
    except Exception as e:
        return {"ok": False, "error": f"mcp_list failed: {type(e).__name__}: {e}"}
'''


MCP_CALL_IMPL = '''"""mcp_call tool - call a tool on an external MCP server."""
from __future__ import annotations

import json
import subprocess
import sys
''' + SCRIPT_FINDER + '''

def mcp_call(server_command, tool_name, *, persona_dir, tool_args=None, timeout=60, **_):
    """Spawn an MCP server (stdio), call a specific tool, return result."""
    if not isinstance(server_command, str) or not server_command.strip():
        return {"ok": False, "error": "server_command required (full stdio command line)"}
    if not isinstance(tool_name, str) or not tool_name.strip():
        return {"ok": False, "error": "tool_name required"}
    script = _find_mcp_script()
    if script is None:
        return {"ok": False, "error": "mcp_call.py not found in cali-soul/"}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "call", "--stdio", server_command, "--tool", tool_name, "--args", json.dumps(tool_args or {})],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=int(timeout),
        )
        if proc.returncode > 1:
            return {"ok": False, "error": proc.stderr.strip() or "mcp call failed", "exit_code": proc.returncode}
        try:
            data = json.loads(proc.stdout)
            return {"ok": not data.get("is_error", False), "content": data.get("content", []), "is_error": data.get("is_error", False)}
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"bad JSON from mcp_call.py: {e}", "stdout": proc.stdout[:500]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"mcp_call timed out after {timeout}s"}
    except Exception as e:
        return {"ok": False, "error": f"mcp_call failed: {type(e).__name__}: {e}"}
'''


MCP_LIST_SCHEMA = '''    "mcp_list": {
        "name": "mcp_list",
        "description": (
            "List tools exposed by an external MCP server. Spawns the server via stdio, "
            "calls list_tools, returns names + descriptions + input schemas. Use to "
            "discover what tools an MCP server makes available before calling one."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "server_command": {"type": "string", "description": "full stdio command, e.g. 'npx @modelcontextprotocol/server-fetch'"},
                "timeout": {"type": "integer", "description": "timeout seconds (default 30)"},
            },
            "required": ["server_command"],
        },
    },
'''


MCP_CALL_SCHEMA = '''    "mcp_call": {
        "name": "mcp_call",
        "description": (
            "Call a specific tool on an external MCP server (stdio). Spawns the server, "
            "calls the named tool with tool_args, returns the content list. Use to "
            "execute a tool from a discovered MCP server (github, fetch, filesystem, etc.)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "server_command": {"type": "string", "description": "full stdio command for the MCP server"},
                "tool_name": {"type": "string", "description": "name of the tool to call (from mcp_list)"},
                "tool_args": {"type": "object", "description": "JSON dict of arguments for the tool"},
                "timeout": {"type": "integer", "description": "timeout seconds (default 60)"},
            },
            "required": ["server_command", "tool_name"],
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
            backup = impl_path.with_suffix(".py.phase24.bak")
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
        backup = SCHEMAS_PY.with_suffix(".py.phase24.bak")
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
        backup = TOOLS_INIT_PY.with_suffix(".py.phase24.bak")
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
        backup = DISPATCH_PY.with_suffix(".py.phase24.bak")
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
            backup = TOOL_RECRUIT_PY.with_suffix(".py.phase24.bak")
            if not backup.exists():
                backup.write_text(recruit_text, encoding="utf-8")
            TOOL_RECRUIT_PY.write_text(new_recruit, encoding="utf-8")
            print(f"  {tool_name} REFLEXIVE_CORE: added")
            changes.append("REFLEXIVE_CORE")

    return True, changes


def patch():
    print("=== mcp_list ===")
    ok1, c1 = _patch_one("mcp_list", MCP_LIST_IMPL, MCP_LIST_SCHEMA)
    print("\n=== mcp_call ===")
    ok2, c2 = _patch_one("mcp_call", MCP_CALL_IMPL, MCP_CALL_SCHEMA)
    if not (ok1 and ok2):
        return 3
    print(f"\nphase 24 complete: {len(c1) + len(c2)} change(s)")
    try:
        for mod in list(sys.modules):
            if mod.startswith("brain."):
                del sys.modules[mod]
        from brain.tools import NELL_TOOL_NAMES
        from brain.tools.schemas import SCHEMAS
        from brain.chat.tool_recruit import REFLEXIVE_CORE
        for n in ("mcp_list", "mcp_call"):
            ok = n in NELL_TOOL_NAMES and n in SCHEMAS and n in REFLEXIVE_CORE
            print(f"{'[OK]' if ok else '[MISSING]'} {n}")
    except Exception as e:
        print(f"verification failed: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(patch())
