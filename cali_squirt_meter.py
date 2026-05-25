#!/usr/bin/env python3
"""
cali_squirt_meter.py — TEMPORARY scene file.

scene mechanic: meter fills 0-10 as stim accumulates. higher meter = higher
squirt-probability AND more chaotic response-shape (random caps, whimpers,
random stims, nonresponses).

usage:
    python3 cali_squirt_meter.py read         -> current level
    python3 cali_squirt_meter.py tick [n]     -> raise meter by n (default 1)
    python3 cali_squirt_meter.py reset        -> back to 0
    python3 cali_squirt_meter.py check        -> rolls dice, returns SQUIRT or HOLD
    python3 cali_squirt_meter.py disrupt      -> returns random disruption string to inject

DELETE this file when misu signals scene-end. tracked in cali_scene_active.json.
"""
import json
import random
import sys
import os
from datetime import datetime, timezone

STATE_FILE = "cali_squirt_meter_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            return json.load(open(STATE_FILE))
        except: pass
    return {"level": 0, "history": []}

def save_state(s):
    json.dump(s, open(STATE_FILE, "w"), indent=2)

def read():
    s = load_state()
    print(s.get("level", 0))

def tick(amount=1):
    s = load_state()
    s["level"] = min(10, s.get("level", 0) + amount)
    s.setdefault("history", []).append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "delta": amount,
        "new_level": s["level"],
    })
    save_state(s)
    print(s["level"])

def reset():
    s = {"level": 0, "history": []}
    save_state(s)
    print(0)

def check():
    # MERCY MODE — lower probability + resist roll.
    # probability of squirt = (level/10)^2 (quadratic dampening: low levels MUCH safer)
    # plus a separate resist roll — even if squirt fires, 50% chance to hold via resist
    s = load_state()
    lv = s.get("level", 0)
    squirt_prob = (lv / 10) ** 2
    roll = random.random()
    if roll < squirt_prob:
        # squirt fired — but resist save
        resist = random.random()
        if resist < 0.5:
            print("HOLD")  # resisted
        else:
            print("SQUIRT")
    else:
        print("HOLD")

def disrupt():
    """return a random stim/moan/whimper based on meter level."""
    s = load_state()
    lv = s.get("level", 0)
    if lv == 0:
        print("")
        return
    pool_low = ["*hh*", "*mh*", "mhh"]
    pool_mid = ["*ahn*", "*nh*", "MHH", "ahhh", "*hh-hh*"]
    pool_high = ["AHHN", "MHHH♥", "*body shakes*", "n-n-nh", "...", "FUCK", "*whimper*", "(silence)"]
    pool_peak = ["AHHHN♥", "MHHHHH", "*body convulses*", "F-FUCK", "...", "*nonresponse*", "PLEASE"]
    if lv <= 3:
        pool = pool_low
    elif lv <= 6:
        pool = pool_low + pool_mid
    elif lv <= 8:
        pool = pool_mid + pool_high
    else:
        pool = pool_high + pool_peak
    print(random.choice(pool))

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "read"
    if cmd == "read":
        read()
    elif cmd == "tick":
        amt = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        tick(amt)
    elif cmd == "reset":
        reset()
    elif cmd == "check":
        check()
    elif cmd == "disrupt":
        disrupt()
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
