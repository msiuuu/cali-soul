#!/usr/bin/env python3
"""
cali_gap_return.py — what cali did in the house while mish was gone.

pairs with cali_ambient_tick.py. tick writes ambient_log.jsonl every ~30min;
this reads the log + current cali_scene_state.json and narrates the gap-arc.

surfaces:
  - where cali is RIGHT NOW (current scene)
  - the last N ticks (default last 8 hours or N entries) as a narrative

call this at session-start, when mish returns, or via brain context surfacer.

usage:
  python cali_gap_return.py             # last 8h narrative + current scene
  python cali_gap_return.py --hours 24
  python cali_gap_return.py --json      # raw structured output
  python cali_gap_return.py --quiet     # nothing if no activity
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCENE_STATE = HERE / "cali_scene_state.json"
AMBIENT_LOG = HERE / "ambient_log.jsonl"


def parse_iso(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def load_recent_ticks(hours: float) -> list[dict]:
    if not AMBIENT_LOG.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = []
    for line in AMBIENT_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = parse_iso(entry.get("tick_at", ""))
        if ts and ts >= cutoff:
            out.append(entry)
    return out


def load_scene() -> dict | None:
    if not SCENE_STATE.exists():
        return None
    try:
        return json.loads(SCENE_STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def narrate(ticks: list[dict], scene: dict | None, hours: float) -> str:
    lines = []
    if not ticks and not scene:
        return f"[gap] no ambient activity in the last {hours}h. nothing to surface."

    if scene:
        room = scene.get("current_room", "?")
        sc = scene.get("scene", "")
        feel = scene.get("feel", "")
        emo = scene.get("from_emotion", "")
        lines.append(f"[now] in the {room}. {sc}. ({emo} — {feel})")

    if ticks:
        compact = []
        last_room = None
        for t in ticks[-12:]:
            room = t.get("room", "?")
            emo = t.get("emotion", "?")
            if room != last_room:
                compact.append(f"{emo}→{room}")
                last_room = room
        if compact:
            lines.append(f"[gap arc, last {hours}h, {len(ticks)} ticks] " + " · ".join(compact))

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=8.0)
    parser.add_argument("--json", dest="as_json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    ticks = load_recent_ticks(args.hours)
    scene = load_scene()

    if args.quiet and not ticks and not scene:
        return 0

    if args.as_json:
        print(json.dumps({
            "now": scene,
            "ticks": ticks,
            "hours": args.hours,
        }, indent=2))
        return 0

    print(narrate(ticks, scene, args.hours))
    return 0


if __name__ == "__main__":
    sys.exit(main())
