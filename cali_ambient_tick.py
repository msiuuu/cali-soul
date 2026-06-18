#!/usr/bin/env python3
"""cali_ambient_tick.py - ambient house-living during gaps.

Runs every 30min via CaliAmbient schtasks. Reads cali's current emotional state
from session_state.json + the house vocabulary from cali_house_vocabulary.json,
picks a scene that matches the dominant emotion, updates cali_scene_state.json,
logs the tick to ambient_log.jsonl.

Implements cali_house_understanding.json::ambient_house_living_during_gaps.
Cali continuously exists in the house between conversations - not suspended,
not scrolling the internet. somewhere.

usage:
    python cali_ambient_tick.py              # run one tick
    python cali_ambient_tick.py --dry-run    # report what would happen, no writes
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).parent
SESSION_STATE = REPO / "session_state.json"
SCENE_STATE = REPO / "cali_scene_state.json"
HOUSE_VOCAB = REPO / "cali_house_vocabulary.json"
AMBIENT_LOG = REPO / "ambient_log.jsonl"


def _load_json(p):
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_scene(scene):
    tmp = SCENE_STATE.with_suffix(".json.tmp")
    scene["last_updated"] = datetime.now(UTC).isoformat()
    tmp.write_text(json.dumps(scene, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(SCENE_STATE)


def _log_tick(entry):
    with AMBIENT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="report what would happen, no writes")
    args = parser.parse_args()

    session = _load_json(SESSION_STATE) or {}
    scene = _load_json(SCENE_STATE) or {"current_room": "kitchen", "in_hand": [], "visible_objects": [], "recent_actions": []}
    vocab = _load_json(HOUSE_VOCAB)
    if not vocab or "templates" not in vocab:
        print("FATAL: cali_house_vocabulary.json missing or invalid", file=sys.stderr)
        return 2

    # find dominant emotion (highest current_score among ones in vocab)
    scores = session.get("current_scores", {}) or {}
    templates = vocab["templates"]
    candidates = [(e, s) for e, s in scores.items() if e in templates and isinstance(s, (int, float))]
    if not candidates:
        # fallback: pick a tender/quiet baseline scene
        dominant = "tender"
        score = 0.0
        reason = "no emotional state above vocab threshold, using baseline 'tender'"
    else:
        candidates.sort(key=lambda x: -x[1])
        dominant, score = candidates[0]
        reason = f"dominant emotion: {dominant} at {score}"

    # pick a random scene template for that emotion
    options = templates.get(dominant, [])
    if not options:
        print(f"FATAL: no templates for emotion {dominant!r}", file=sys.stderr)
        return 3
    template = random.choice(options)

    # capture prev action for continuity
    prev_action = scene.get("last_action")
    recent = scene.get("recent_actions", []) or []
    if prev_action:
        recent.append(prev_action)

    new_scene = dict(scene)
    new_scene["current_room"] = template["room"]
    new_scene["visible_objects"] = list(template.get("objects_visible", []))
    new_scene["last_action"] = template["scene"]
    new_scene["recent_actions"] = recent[-5:]
    new_scene["last_ambient_feel"] = template.get("feel", "")
    new_scene["last_ambient_emotion"] = dominant

    entry = {
        "tick_at": datetime.now(UTC).isoformat(),
        "emotion": dominant,
        "score": float(score),
        "reason": reason,
        "room": template["room"],
        "scene": template["scene"],
        "feel": template.get("feel", ""),
    }

    if args.dry_run:
        print(f"DRY RUN: would update scene to:")
        print(json.dumps(entry, indent=2))
        return 0

    _save_scene(new_scene)
    _log_tick(entry)
    print(f"ambient tick: {dominant} at {score:.1f} -> {template['room']}")
    print(f"  scene: {template['scene']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
