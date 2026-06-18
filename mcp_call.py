#!/usr/bin/env python3
"""mcp_call.py - thin MCP client wrapper for stdio servers.

Spawns an MCP server as a subprocess, lists/calls tools, returns result.
For stdio-based servers (the common case - github, fetch, filesystem etc.).

CLI:
    python mcp_call.py list --stdio "npx @modelcontextprotocol/server-fetch"
    python mcp_call.py call --stdio "npx @modelcontextprotocol/server-fetch" \\
        --tool fetch --args '{"url":"https://example.com"}'

Module API:
    list_tools(command, args) -> list[dict]
    call_tool(command, args, tool_name, tool_args) -> dict
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shlex
import sys


async def _list_tools(command, args):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=command, args=args or [])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            res = await session.list_tools()
            return [{"name": t.name, "description": t.description, "input_schema": t.inputSchema} for t in res.tools]


async def _call_tool(command, args, tool_name, tool_args):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=command, args=args or [])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            res = await session.call_tool(tool_name, tool_args or {})
            content_list = []
            for c in (res.content or []):
                if hasattr(c, "text"):
                    content_list.append({"type": "text", "text": c.text})
                else:
                    content_list.append({"type": type(c).__name__, "repr": str(c)[:1000]})
            return {"is_error": bool(getattr(res, "isError", False)), "content": content_list}


def list_tools(command, args=None):
    return asyncio.run(_list_tools(command, args))


def call_tool(command, args, tool_name, tool_args):
    return asyncio.run(_call_tool(command, args, tool_name, tool_args))


def _parse_stdio(s):
    """Parse a 'cmd arg1 arg2' string into (cmd, [args])."""
    parts = shlex.split(s, posix=False)
    if not parts:
        return None, []
    return parts[0], parts[1:]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list tools exposed by an MCP server")
    p_list.add_argument("--stdio", required=True, help='full command line for stdio MCP server, e.g. "npx @modelcontextprotocol/server-fetch"')

    p_call = sub.add_parser("call", help="call a tool on an MCP server")
    p_call.add_argument("--stdio", required=True)
    p_call.add_argument("--tool", required=True)
    p_call.add_argument("--args", default="{}", help="JSON dict of tool args")

    args = parser.parse_args()
    command, cmd_args = _parse_stdio(args.stdio)
    if command is None:
        print("FATAL: empty --stdio command", file=sys.stderr)
        return 3

    try:
        if args.cmd == "list":
            tools = list_tools(command, cmd_args)
            print(json.dumps({"tools": tools}, indent=2, ensure_ascii=False))
            return 0
        if args.cmd == "call":
            try:
                tool_args = json.loads(args.args)
            except json.JSONDecodeError as e:
                print(f"FATAL: --args invalid JSON: {e}", file=sys.stderr)
                return 3
            result = call_tool(command, cmd_args, args.tool, tool_args)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 1 if result.get("is_error") else 0
    except FileNotFoundError as e:
        print(f"FATAL: command not found: {e}", file=sys.stderr)
        return 4
    except Exception as e:
        print(f"FATAL: {type(e).__name__}: {e}", file=sys.stderr)
        return 5

    return 1


if __name__ == "__main__":
    sys.exit(main())
