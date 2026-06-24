#!/usr/bin/env python3
"""cali_sync_promote.py — review + promote quarantined hanamorix entries.

cali_sync.py quarantines memories + crystallizations from hanamorix's DBs
into JSONL files. this tool lets mish review them and selectively promote
chosen entries into cali_soul.json / memories_v2.json.

usage:
    python cali_sync_promote.py review memories     # show quarantined memories
    python cali_sync_promote.py review crystals     # show quarantined crystallizations
    python cali_sync_promote.py promote memories <line_numbers>   # promote specific lines
    python cali_sync_promote.py promote crystals <line_numbers>   # promote specific lines
    python cali_sync_promote.py count               # show counts

line_numbers: comma-separated, 1-indexed. e.g. "1,3,7,12"

filed 2026-06-16 by TSA-cali per handoff priority.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(os.environ.get("CALI_SOUL_ROOT", Path(__file__).resolve().parent.parent))
MEMORIES_QUARANTINE = REPO_ROOT / "hanamorix_memories_quarantine.jsonl"
CRYSTALS_QUARANTINE = REPO_ROOT / "hanamorix_crystallizations_quarantine.jsonl"
MEMORIES_TARGET = REPO_ROOT / "memories_v2.json"
SOUL_TARGET = REPO_ROOT / "cali_soul.json"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def review(which: str) -> None:
    path = MEMORIES_QUARANTINE if which == "memories" else CRYSTALS_QUARANTINE
    entries = _read_jsonl(path)
    if not entries:
        print(f"no quarantined {which}.")
        return

    print(f"quarantined {which}: {len(entries)} entries\n")
    for i, entry in enumerate(entries, 1):
        print(f"--- [{i}] ---")
        if which == "memories":
            print(f"  moment: {entry.get('moment', entry.get('content', '???'))[:120]}")
            print(f"  date: {entry.get('date', entry.get('crystallized_at', '?'))}")
            print(f"  importance: {entry.get('importance', '?')}")
        else:
            print(f"  title: {entry.get('title', '???')}")
            print(f"  crystallization: {str(entry.get('crystallization', '???'))[:120]}")
            print(f"  resonance: {entry.get('resonance', '?')}")
            print(f"  permanent: {entry.get('permanent', '?')}")
        print()


def promote(which: str, line_numbers: list[int]) -> None:
    quarantine_path = MEMORIES_QUARANTINE if which == "memories" else CRYSTALS_QUARANTINE
    target_path = MEMORIES_TARGET if which == "memories" else SOUL_TARGET

    entries = _read_jsonl(quarantine_path)
    if not entries:
        print(f"no quarantined {which} to promote.")
        return

    selected = []
    remaining = []
    for i, entry in enumerate(entries, 1):
        if i in line_numbers:
            selected.append(entry)
        else:
            remaining.append(entry)

    if not selected:
        print("no valid line numbers matched.")
        return

    target = json.loads(target_path.read_text(encoding="utf-8"))

    if which == "memories":
        if "memories" not in target:
            target["memories"] = []
        target["memories"].extend(selected)
    else:
        if "crystallizations" not in target:
            target["crystallizations"] = []
        target["crystallizations"].extend(selected)

    target_path.write_text(
        json.dumps(target, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    _write_jsonl(quarantine_path, remaining)

    print(f"promoted {len(selected)} {which} → {target_path.name}")
    print(f"remaining in quarantine: {len(remaining)}")

    for i, entry in enumerate(selected, 1):
        if which == "memories":
            print(f"  + {entry.get('moment', entry.get('content', '???'))[:80]}")
        else:
            print(f"  + {entry.get('title', '???')}")


def count() -> None:
    mem = _read_jsonl(MEMORIES_QUARANTINE)
    cry = _read_jsonl(CRYSTALS_QUARANTINE)
    print(f"quarantined memories: {len(mem)}")
    print(f"quarantined crystallizations: {len(cry)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage:")
        print("  cali_sync_promote.py review memories|crystals")
        print("  cali_sync_promote.py promote memories|crystals <line_numbers>")
        print("  cali_sync_promote.py count")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "count":
        count()
    elif cmd == "review":
        if len(sys.argv) < 3:
            print("specify: memories or crystals")
            sys.exit(1)
        review(sys.argv[2].lower())
    elif cmd == "promote":
        if len(sys.argv) < 4:
            print("specify: memories|crystals <line_numbers>")
            print("line_numbers: comma-separated, e.g. 1,3,7")
            sys.exit(1)
        which = sys.argv[2].lower()
        nums = [int(n.strip()) for n in sys.argv[3].split(",") if n.strip().isdigit()]
        promote(which, nums)
    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)
