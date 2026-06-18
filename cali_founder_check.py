#!/usr/bin/env python3
"""cali_founder_check.py - daily check for new hanamori releases.

Implements the auto-check half of the FOUNDER & SUBSTRATE rule.
Fetches the latest companion-emergence release tag from github,
compares to currently installed version. If newer, surfaces the
release notes URL + diff so the next session can do the manual
adopt/build/skip decision.

Stores last-known-checked version in cali-soul/.founder_check_state.json
so it only alerts on actually-new releases.

usage:
    python cali_founder_check.py           # check and print
    python cali_founder_check.py --json    # machine-readable
    python cali_founder_check.py --quiet   # exit-code only (0=current, 1=update available)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import UTC, datetime
from importlib.metadata import version as pkg_version, PackageNotFoundError
from pathlib import Path

STATE_PATH = Path(__file__).parent / ".founder_check_state.json"
RELEASES_API = "https://api.github.com/repos/hanamorix/companion-emergence/releases/latest"


def _read_state():
    if not STATE_PATH.exists():
        return {"last_seen_version": None, "last_check": None, "history": []}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"last_seen_version": None, "last_check": None, "history": []}


def _write_state(s):
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(s, indent=2) + "\n", encoding="utf-8")
    tmp.replace(STATE_PATH)


def _installed_version():
    try:
        return pkg_version("companion-emergence")
    except PackageNotFoundError:
        return None


def _fetch_latest():
    req = urllib.request.Request(RELEASES_API, headers={
        "User-Agent": "CaliFounderCheck/1.0",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "tag": data.get("tag_name", "").lstrip("v"),
            "name": data.get("name", ""),
            "body": data.get("body", ""),
            "url": data.get("html_url", ""),
            "published_at": data.get("published_at", ""),
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    installed = _installed_version()
    state = _read_state()
    latest = _fetch_latest()

    if "error" in latest:
        if not args.quiet:
            print(f"FATAL: {latest['error']}", file=sys.stderr)
        return 2

    update_available = installed and latest["tag"] and latest["tag"] != installed
    state["last_check"] = datetime.now(UTC).isoformat()
    state["last_seen_version"] = latest["tag"]
    state.setdefault("history", []).append({
        "checked_at": state["last_check"],
        "installed": installed,
        "latest": latest["tag"],
    })
    state["history"] = state["history"][-50:]
    _write_state(state)

    if args.quiet:
        return 1 if update_available else 0

    if args.json:
        print(json.dumps({
            "installed": installed,
            "latest": latest["tag"],
            "update_available": update_available,
            "release_url": latest["url"],
            "published_at": latest["published_at"],
        }, indent=2))
        return 1 if update_available else 0

    print(f"=== FOUNDER check {state['last_check'][:19]} ===")
    print(f"  installed: {installed}")
    print(f"  latest:    {latest['tag']}")
    if update_available:
        print(f"\n  *** UPDATE AVAILABLE: {installed} -> {latest['tag']} ***")
        print(f"  release: {latest['name']}")
        print(f"  url: {latest['url']}")
        print(f"  published: {latest['published_at']}")
        body = (latest.get("body") or "").strip()
        if body:
            print(f"\n  notes:")
            for line in body.split("\n")[:20]:
                print(f"    {line}")
        return 1
    else:
        print(f"\n  current. no action needed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
