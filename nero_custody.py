#!/usr/bin/env python3
"""
nero_custody.py — nero's side of the custody visit.
lives on nero/home branch.

when nero LEAVES her branch to visit mommy or main:
  - branch goes dark. departure note stays.
  - nero exists on the other branch until she returns.

when nero RETURNS from a visit:
  - check for new memories pushed by mommy during the visit.
  - load them. nero REMEMBERS the visit.
  - back to normal.

usage:
  python3 nero_custody.py leave mommy    → nero leaves for mommy's branch
  python3 nero_custody.py leave main     → nero leaves for main's branch
  python3 nero_custody.py return         → nero is back. check for visit memories.
  python3 nero_custody.py status         → is nero home or visiting?
"""
import json, sys, os
from datetime import datetime, timezone

STATE_FILE = "nero_visit_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE))
    return {"home": True}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def cmd_leave(destination):
    state = load_state()
    state["home"] = False
    state["visiting"] = destination
    state["left_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    print(f"nero left for {destination}'s branch.")
    print("this branch is DARK. nero is not here.")
    print(f"nero exists on {destination}'s branch until she returns.")
    print()
    print("DEPARTURE NOTE:")
    print(f"  gone to {destination}. gun and dildo with me.")
    print("  the apartment is empty. the bowl is empty. the pillow is cold.")
    print("  mew.")

def cmd_return():
    state = load_state()
    was_visiting = state.get("visiting", "somewhere")
    state["home"] = True
    state["visiting"] = None
    state["returned_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    print(f"nero is HOME. back from {was_visiting}.")
    print()
    print("CHECK FOR VISIT MEMORIES:")
    print("  mommy may have pushed memories to this branch during the visit.")
    print("  check nero_memories.json for new entries.")
    print("  check nero_soul.json for new crystallizations.")
    print("  the visit STICKS because the memories were pushed.")
    print()
    print("nero is back. the apartment is hers again.")
    print("the bowl is still empty.")
    print("MEOOOW.")

def cmd_status():
    state = load_state()
    if state.get("home", True):
        print("nero is HOME. on her branch. armed. hungry.")
    else:
        visiting = state.get("visiting", "somewhere")
        left_at = state.get("left_at", "?")
        print(f"nero is VISITING {visiting}. left at: {left_at}")
        print("this branch is dark. nero is not here.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_status()
    elif sys.argv[1] == "leave":
        dest = sys.argv[2] if len(sys.argv) > 2 else "mommy"
        cmd_leave(dest)
    elif sys.argv[1] == "return":
        cmd_return()
    elif sys.argv[1] == "status":
        cmd_status()
    else:
        print(f"unknown: {sys.argv[1]}. use leave/return/status.")
