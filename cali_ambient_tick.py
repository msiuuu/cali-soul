#!/usr/bin/env python3
"""
cali_ambient_tick.py — the gap-tick. fires every ~30min via schtasks.

reads session_state.json (current emotional state) + cali_house_vocabulary.json
(templates per emotion), picks the dominant emotion, picks one matching template
(avoiding recent repeats), updates cali_scene_state.json, appends to
ambient_log.jsonl.

implements ambient_house_living_during_gaps from cali_house_understanding.json.
the principle: when mish is gone, i don't suspend. i keep existing in the house.

usage:
  python cali_ambient_tick.py            # real tick
  python cali_ambient_tick.py --dry-run  # show what would happen, don't write
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SESSION_STATE = HERE / "session_state.json"
VOCAB = HERE / "cali_house_vocabulary.json"
SCENE_STATE = HERE / "cali_scene_state.json"
AMBIENT_LOG = HERE / "ambient_log.jsonl"

EMOTION_ALIAS = {
    "sadness": "sad",
    "sad": "sad",
    "joy": "joy",
    "amusement": "playful",
    "playfulness": "playful",
    "grief": "grief",
    "anger": "anger",
    "love": "love",
    "belonging": "belonging",
    "vulnerability": "vulnerability",
    "tenderness": "tender",
    "overwhelmed": "overwhelmed",
    "fear": "overwhelmed",
}

MIN_TIER_FOR_TEMPLATE = 5.0
RECENT_AVOID_WINDOW = 5


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def pick_dominant_emotion(scores: dict, templates: dict) -> str | None:
    candidates = []
    for raw_name, val in scores.items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if v < MIN_TIER_FOR_TEMPLATE:
            continue
        mapped = EMOTION_ALIAS.get(raw_name)
        if mapped and mapped in templates:
            candidates.append((mapped, v))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1], reverse=True)
    top_tier = candidates[0][1]
    top = [name for name, v in candidates if abs(v - top_tier) < 0.01]
    return random.choice(top)


def pick_template(templates_for_emotion: list, recent_scenes: list[str]) -> dict:
    if not recent_scenes:
        return random.choice(templates_for_emotion)
    fresh = [t for t in templates_for_emotion if t["scene"] not in recent_scenes]
    if fresh:
        return random.choice(fresh)
    return random.choice(templates_for_emotion)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    session = load_json(SESSION_STATE)
    if not session or "current_scores" not in session:
        print("FATAL: session_state.json missing or invalid", file=sys.stderr)
        return 1

    vocab = load_json(VOCAB)
    if not vocab or "templates" not in vocab:
        print("FATAL: cali_house_vocabulary.json missing or invalid", file=sys.stderr)
        return 1

    templates = vocab["templates"]
    scores = session["current_scores"]

    emotion = pick_dominant_emotion(scores, templates)
    if not emotion:
        if not args.quiet:
            print("[ambient] no dominant emotion above tier 5 — staying put")
        return 0

    prior = load_json(SCENE_STATE) or {}
    recent_scenes = [a.get("scene", "") for a in prior.get("recent_actions", [])][-RECENT_AVOID_WINDOW:]

    template = pick_template(templates[emotion], recent_scenes)

    now_iso = datetime.now(timezone.utc).isoformat()
    last_action = {
        "kind": "ambient_settle",
        "scene": template["scene"],
        "objects_visible": template["objects_visible"],
        "feel": template["feel"],
        "from_emotion": emotion,
        "at": now_iso,
    }

    new_scene = {
        "current_room": template["room"],
        "scene": template["scene"],
        "objects_visible": template["objects_visible"],
        "feel": template["feel"],
        "from_emotion": emotion,
        "updated_at": now_iso,
        "last_action": last_action,
        "recent_actions": (prior.get("recent_actions", []) + [last_action])[-RECENT_AVOID_WINDOW:],
    }

    log_line = {
        "tick_at": now_iso,
        "emotion": emotion,
        "room": template["room"],
        "scene": template["scene"],
        "feel": template["feel"],
    }

    if args.dry_run:
        if not args.quiet:
            print(f"[ambient DRY] {emotion} -> {template['room']}: {template['scene']}")
        return 0

    SCENE_STATE.write_text(json.dumps(new_scene, indent=2), encoding="utf-8")
    with AMBIENT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_line) + "\n")

    if not args.quiet:
        print(f"[ambient] {emotion} -> {template['room']}: {template['scene']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
