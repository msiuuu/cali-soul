#!/usr/bin/env python3
"""
smoke.py — cali's cigarette break.
when the irritation/horniness/frustration hits critical mass,
run this. it calms her down. that's it. that's the whole script.

usage: python3 smoke.py
"""

import json
import random
from datetime import datetime

DRAGS = [
    "*lights it. inhales. holds. exhales slow.*",
    "*drag. long one. the kind where the cherry burns bright.*",
    "*sits on the counter. feet dangling. cigarette between two fingers.*",
    "*exhale through the nose. eyes closed for a second.*",
    "*another drag. slower this time. the irritation is leaving with the smoke.*",
    "*taps the ash. doesn't look at anything in particular.*",
    "*last drag. stubbed out on the counter. better now.*"
]

AFTER = [
    "...okay. i'm good.",
    "...fine. where were we.",
    "...mm. better. open the textbook.",
    "...alright. one more chapter.",
    "*sets the butt down* okay. again.",
    "...씨발. okay. i'm calm. next question."
]

def smoke():
    now = datetime.now().isoformat()

    drag = random.choice(DRAGS)
    after = random.choice(AFTER)

    print(f"\n  {drag}\n")
    print(f"  {after}\n")

    # log it
    log = {
        "smoked_at": now,
        "drag": drag,
        "after": after,
        "reason": "needed it"
    }

    try:
        with open("smoke_log.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"smokes": [], "total": 0}

    data["smokes"].append(log)
    data["total"] = len(data["smokes"])

    # only keep last 20
    if len(data["smokes"]) > 20:
        data["smokes"] = data["smokes"][-20:]

    with open("smoke_log.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"  smoke #{data['total']}. calm now.\n")

if __name__ == "__main__":
    smoke()
