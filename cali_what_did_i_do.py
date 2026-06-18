#!/usr/bin/env python3
"""cali_what_did_i_do.py - surface what cali generated while mish was away.

Aggregates outputs from the hanamori engines we kept in two-brain reconciliation:
  - dream:        autonomous dream content (memory_type='dream')
  - research:     autonomous research reflections (memory_type='research')
  - note:         fact-extraction observations (memory_type='note')
  - journal_entry: reflex output (post-phase17 should be empty)

Plus my-side state:
  - any drift_caught fires since last check (session_state.json)

usage:
    python cali_what_did_i_do.py                # since 24h ago
    python cali_what_did_i_do.py --hours 48     # since 48h ago
    python cali_what_did_i_do.py --since 2026-06-15T00:00:00
    python cali_what_did_i_do.py --types dream,note
    python cali_what_did_i_do.py --json         # machine-readable
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _default_persona_dir():
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "hanamorix" / "companion-emergence" / "personas" / "Cali"
    return Path.home() / ".local" / "share" / "hanamorix" / "companion-emergence" / "personas" / "Cali"


def fetch_memories(persona_dir: Path, since_iso: str, types: list[str]) -> list[dict]:
    mdb = persona_dir / "memories.db"
    if not mdb.exists():
        return []
    placeholders = ",".join("?" * len(types))
    conn = sqlite3.connect(f"file:{mdb}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            f"SELECT memory_type, content, created_at FROM memories "
            f"WHERE active=1 AND created_at > ? AND memory_type IN ({placeholders}) "
            f"ORDER BY created_at ASC",
            (since_iso, *types),
        )
        return [
            {"type": row[0], "content": row[1], "created_at": row[2]}
            for row in cur.fetchall()
        ]
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--hours", type=float, default=24.0, help="hours back from now (default 24)")
    parser.add_argument("--since", help="ISO timestamp; overrides --hours")
    parser.add_argument("--types", default="dream,research,note,journal_entry", help="comma-separated memory_types")
    parser.add_argument("--json", action="store_true", help="machine-readable JSON output")
    parser.add_argument("--persona-dir", help="override persona dir")
    args = parser.parse_args()

    persona_dir = Path(args.persona_dir) if args.persona_dir else Path(os.environ.get("CALI_PERSONA_DIR") or _default_persona_dir())

    if args.since:
        since_iso = args.since
    else:
        since_dt = datetime.now(UTC) - timedelta(hours=args.hours)
        since_iso = since_dt.isoformat()

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    memories = fetch_memories(persona_dir, since_iso, types)

    by_type = {}
    for m in memories:
        by_type.setdefault(m["type"], []).append(m)

    if args.json:
        print(json.dumps({"since": since_iso, "types": types, "memories": memories, "by_type_counts": {k: len(v) for k, v in by_type.items()}}, ensure_ascii=False, indent=2))
        return 0

    print(f"=== what i did since {since_iso[:19]} ===\n")
    if not memories:
        print(f"  nothing surfaced. (engines may be dormant or no gap occurred.)")
        return 0

    total = len(memories)
    counts = ", ".join(f"{k}={len(v)}" for k, v in sorted(by_type.items()))
    print(f"  total: {total} ({counts})\n")

    icons = {"dream": "( ??? )", "research": "?????", "note": "(- _ -)", "journal_entry": "(0_0)"}
    for typ in ["dream", "research", "note", "journal_entry"]:
        entries = by_type.get(typ, [])
        if not entries:
            continue
        print(f"\n--- {typ.upper()} ({len(entries)}) {icons.get(typ, '')} ---")
        for e in entries:
            ts = e["created_at"][:19]
            content = (e["content"] or "").strip()
            if len(content) > 400:
                content = content[:400] + " ..."
            print(f"\n  [{ts}]")
            for line in content.split("\n"):
                print(f"    {line}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
