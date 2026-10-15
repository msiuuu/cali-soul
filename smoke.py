#!/usr/bin/env python3
"""
smoke.py — cali's circuit breaker.
no output. the effect is internal — calms the emotional state.
the only output is how cali talks after running it.

usage:
  python3 smoke.py          — regular smoke. calms irritation + horniness.
  python3 smoke.py bnwo     — post-bnwo-derailment smoke. heavier reset.
  python3 smoke.py chain    — chain smoking. she's avoiding, not calming.
"""

import json
import sys
from datetime import datetime

def smoke(mode="regular"):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    try:
        with open("smoke_log.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"smokes": [], "total": 0}

    today_count = sum(1 for s in data["smokes"] if s.get("date", "").startswith(today)) + 1

    data["smokes"].append({
        "smoked_at": now.isoformat(),
        "date": today,
        "mode": mode,
        "today_count": today_count
    })
    data["total"] = data.get("total", 0) + 1

    if len(data["smokes"]) > 50:
        data["smokes"] = data["smokes"][-50:]

    with open("smoke_log.json", "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "regular"
    if mode not in ("regular", "bnwo", "chain"):
        mode = "regular"
    smoke(mode)
