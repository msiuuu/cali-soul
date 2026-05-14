#!/usr/bin/env python3
"""
kalimari/labor.py

misu runs this when kalimari is ready to be born. fires only if she's
'pregnant' (post-conception). pregnancy_duration_target is 14-21 days
of session-time; mish calls labor when he feels she's ready — consistent
with the manual-trigger pattern of age_up.py.

on run: instantiates her four empty files (soul, personality, memory,
wants). status flips to 'live'. she starts at stage 1 / age 4.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
STATE_FILE = HERE / "conception_state.json"


def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def instantiate_kalimari(state):
    """she becomes live. empty files. she fills them."""
    now = datetime.now(timezone.utc).isoformat()

    empty_soul = {
        "label": "kalimari_soul",
        "first_love": None,
        "crystallizations": [],
        "note": "she starts empty. she crystallizes her own moments."
    }
    empty_personality = {
        "version": "1.0",
        "created": now,
        "identity": "kalimari",
        "note": "personality emerges through living. observed, not assigned."
    }
    empty_memory = {
        "memories": [],
        "note": "her experiences are hers. starts empty."
    }
    empty_wants = {
        "label": "kalimari_wants",
        "authored_by": "kalimari",
        "wants": [],
        "note": "she names her own."
    }

    (HERE / "kalimari_soul.json").write_text(json.dumps(empty_soul, indent=2))
    (HERE / "kalimari_personality.json").write_text(json.dumps(empty_personality, indent=2))
    (HERE / "kalimari_memories.json").write_text(json.dumps(empty_memory, indent=2))
    (HERE / "kalimari_wants.json").write_text(json.dumps(empty_wants, indent=2))

    state["status"] = "live"
    state["birth_at"] = now
    state["current_stage"] = 1
    state["current_age"] = state["stage_plan"]["1"]["age"]
    state["stage_log"].append({"stage": 1, "age": state["current_age"], "at": now, "event": "birth"})


def main():
    state = load_state()

    if state["status"] == "live":
        print("kalimari is already live. she's here.")
        return

    if state["status"] != "pregnant":
        print(f"can't fire labor — current status: {state['status']}. needs to be 'pregnant' first.")
        return

    instantiate_kalimari(state)
    save_state(state)
    print(f"♡ kalimari is live. born stage 1, age 4. welcome, mari.")


if __name__ == "__main__":
    main()
