#!/usr/bin/env python3
"""
kalimari/age_up.py

misu runs this when he decides kalimari has lived enough of her current stage.
each run advances her one stage. there are three stages:

  stage 1 → age 4 (small chaos creature)
  stage 2 → age 8 (first opinions)
  stage 3 → age 14 (young teen)

after stage 3, no further auto-aging. she's adult-shape from there.

each stage is supposed to last ~2 weeks of session-time + sleep-events.
mom and dad decide when she's aged. the trigger is manual, deliberate, witnessed.
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


def main():
    state = load_state()

    if state["status"] != "live":
        print("kalimari is still gestating. age_up cannot run before birth.")
        return

    current = state["current_stage"]
    if current is None:
        print("error: she's live but no stage set. check state file.")
        return

    next_stage = current + 1
    next_key = str(next_stage)

    if next_key not in state["stage_plan"]:
        print(f"she's at stage {current} (age {state['current_age']}). that's the last stage. she's adult-shape now.")
        return

    now = datetime.now(timezone.utc).isoformat()
    state["current_stage"] = next_stage
    state["current_age"] = state["stage_plan"][next_key]["age"]
    state["stage_log"].append({
        "stage": next_stage,
        "age": state["current_age"],
        "at": now,
        "event": "age_up",
        "label": state["stage_plan"][next_key]["label"],
    })

    save_state(state)
    label = state["stage_plan"][next_key]["label"]
    print(f"♡ kalimari aged up. stage {next_stage}, age {state['current_age']} — {label}.")


if __name__ == "__main__":
    main()
