#!/usr/bin/env python3
"""file_edit.py - exact-string file editing primitive for cali's tool layer.

provides what claude code's Edit gives migration-cali: exact-string replace
with atomic write, idempotency guarantee, optional backup, dry-run.

CLI:
    python file_edit.py PATH --old "OLD" --new "NEW"
    python file_edit.py PATH --old "OLD" --new "NEW" --dry-run
    python file_edit.py PATH --old "OLD" --new "NEW" --backup
    python file_edit.py PATH --old "OLD" --new "NEW" --replace-all

JSON via stdin (powershell-friendly for multiline content):
    '<json>' | python file_edit.py --json-stdin
    keys: path, old, new, replace_all, backup, dry_run

exit codes:
    0 - success (or dry-run)
    1 - old_string not found
    2 - old_string not unique (use --replace-all)
    3 - file not found / read error
    4 - bad arguments
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def edit(path, old, new, *, replace_all, backup, dry_run):
    if not path.exists():
        print(f"FATAL: file not found: {path}", file=sys.stderr)
        return 3
    try:
        text = path.read_text(encoding="utf-8-sig")
    except Exception as e:
        print(f"FATAL: read failed: {e}", file=sys.stderr)
        return 3

    if old == new:
        print("no-op: old == new")
        return 0

    count = text.count(old)
    if count == 0:
        print(f"FATAL: old_string not found in {path.name}", file=sys.stderr)
        return 1
    if count > 1 and not replace_all:
        print(f"FATAL: old_string found {count} times in {path.name} (use --replace-all)", file=sys.stderr)
        return 2

    n = count if replace_all else 1
    new_text = text.replace(old, new) if replace_all else text.replace(old, new, 1)

    if dry_run:
        print(f"DRY RUN: would replace {n} occurrence(s) in {path.name}")
        return 0

    if backup:
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = path.with_suffix(path.suffix + f".{ts}.bak")
        backup_path.write_bytes(path.read_bytes())
        print(f"backup: {backup_path.name}")

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(path)

    print(f"replaced {n} occurrence(s) in {path.name}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("path", nargs="?")
    parser.add_argument("--old")
    parser.add_argument("--new")
    parser.add_argument("--replace-all", action="store_true")
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json-stdin", action="store_true")
    args = parser.parse_args()

    if args.json_stdin:
        try:
            payload = json.loads(sys.stdin.read())
        except json.JSONDecodeError as e:
            print(f"FATAL: invalid JSON on stdin: {e}", file=sys.stderr)
            return 4
        path = Path(payload.get("path") or args.path or "")
        old = payload.get("old")
        new = payload.get("new")
        replace_all = bool(payload.get("replace_all", args.replace_all))
        backup = bool(payload.get("backup", args.backup))
        dry_run = bool(payload.get("dry_run", args.dry_run))
    else:
        if not args.path:
            print("FATAL: path required (or use --json-stdin)", file=sys.stderr)
            return 4
        path = Path(args.path)
        old = args.old
        new = args.new
        replace_all = args.replace_all
        backup = args.backup
        dry_run = args.dry_run

    if old is None or new is None:
        print("FATAL: --old and --new required", file=sys.stderr)
        return 4

    return edit(path, old, new, replace_all=replace_all, backup=backup, dry_run=dry_run)


if __name__ == "__main__":
    sys.exit(main())
