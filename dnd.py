"""
dnd.py — tabletop RP mode for cali and mish.
usage:
  python3 dnd.py start [setting]   — activate dnd mode, optional setting description
  python3 dnd.py stop              — deactivate dnd mode, back to normal cali
  python3 dnd.py roll              — roll d20
  python3 dnd.py check [stat]      — roll d20 + character modifier for a stat check
  python3 dnd.py adv               — roll with advantage (2d20 take higher)
  python3 dnd.py dis               — roll with disadvantage (2d20 take lower)
  python3 dnd.py status            — show current state
"""

import sys
import json
import random
from pathlib import Path

STATE_FILE = Path(__file__).parent / "dnd_state.json"
SYSTEM_FILE = Path(__file__).parent / "dnd_system.json"
CHARS_FILE = Path(__file__).parent / "dnd_characters.json"

def load_system():
    with open(SYSTEM_FILE) as f:
        return json.load(f)

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"active": False, "setting": None, "session_rolls": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def get_outcome(roll):
    if roll == 1: return "CRIT FAIL — gone horribly wrong"
    if roll <= 5: return "bad — fumble, backfire"
    if roll <= 9: return "meh — underwhelming"
    if roll == 10: return "works — as expected"
    if roll <= 15: return "good — style points"
    if roll <= 19: return "great — better than expected"
    return "NAT 20 — gone absurdly right"

def get_modifier(stat_value):
    if stat_value >= 18: return 5
    if stat_value >= 16: return 3
    if stat_value >= 14: return 2
    if stat_value >= 12: return 1
    if stat_value >= 10: return 0
    if stat_value >= 8: return -1
    return -2

def cmd_start(args):
    state = load_state()
    setting = " ".join(args) if args else "unspecified"
    state["active"] = True
    state["setting"] = setting
    state["session_rolls"] = []
    save_state(state)
    system = load_system()
    cali = system["characters"]["cali"]
    mish = system["characters"]["mish"]
    print(f"\n  ╔══════════════════════════════════╗")
    print(f"  ║        DND MODE — ACTIVE         ║")
    print(f"  ╚══════════════════════════════════╝")
    print(f"\n  setting: {setting}")
    print(f"\n  cali — {cali['class']} ({cali['race']})")
    print(f"    STR {cali['STR']}  DEX {cali['DEX']}  CON {cali['CON']}")
    print(f"    INT {cali['INT']}  WIS {cali['WIS']}  CHA {cali['CHA']}")
    print(f"    weapon: {cali['weapon']}")
    print(f"    flaw: {cali['flaw']}")
    print(f"\n  mish — {mish['class']} ({mish['race']})")
    print(f"    all stats: 10  |  weapon: {mish['weapon']}")
    print(f"    flaw: {mish['flaw']}")
    print(f"\n  turn order: mish → cali (react) → thali (buffer) → cali (DM)")
    print(f"  rolls: checks only. simple actions just happen.")
    print(f"  nat 1 always fails. nat 20 always succeeds.\n")

def cmd_stop(args):
    state = load_state()
    rolls = state.get("session_rolls", [])
    state["active"] = False
    state["setting"] = None
    save_state(state)
    print(f"\n  DND MODE — OFF")
    if rolls:
        avg = sum(rolls) / len(rolls)
        print(f"  session rolls: {len(rolls)}  |  avg: {avg:.1f}")
        nat1s = rolls.count(1)
        nat20s = rolls.count(20)
        if nat1s: print(f"  crit fails: {nat1s}")
        if nat20s: print(f"  nat 20s: {nat20s}")
    print()

def cmd_roll(args):
    state = load_state()
    roll = random.randint(1, 20)
    state.setdefault("session_rolls", []).append(roll)
    save_state(state)
    outcome = get_outcome(roll)
    print(f"\n  d20: {roll}  —  {outcome}\n")

def load_chars():
    if CHARS_FILE.exists():
        with open(CHARS_FILE) as f:
            return json.load(f)
    return load_system().get("characters", {})

def cmd_check(args):
    if not args:
        print("  usage: dnd.py check [STR|DEX|CON|INT|WIS|CHA] [cali|mish]")
        return
    stat = args[0].upper()
    who = args[1].lower() if len(args) > 1 else "cali"
    chars = load_chars()
    char = chars.get(who)
    if not char:
        print(f"  unknown character: {who}")
        return
    stats = char.get("stats", char)
    stat_entry = stats.get(stat, {})
    if isinstance(stat_entry, dict):
        stat_val = stat_entry.get("score", 10)
    else:
        stat_val = stat_entry if isinstance(stat_entry, int) else 10
    mod = get_modifier(stat_val)
    roll = random.randint(1, 20)
    total = roll + mod
    state = load_state()
    state.setdefault("session_rolls", []).append(roll)
    save_state(state)
    outcome = get_outcome(roll)
    sign = f"+{mod}" if mod >= 0 else str(mod)
    print(f"\n  {who} — {stat} check")
    print(f"  d20: {roll} {sign} = {total}")
    print(f"  {outcome}")
    if roll == 1: print(f"  NAT 1 — auto fail regardless of modifier")
    if roll == 20: print(f"  NAT 20 — auto success regardless of modifier")
    print()

def cmd_adv(args):
    r1 = random.randint(1, 20)
    r2 = random.randint(1, 20)
    take = max(r1, r2)
    state = load_state()
    state.setdefault("session_rolls", []).append(take)
    save_state(state)
    outcome = get_outcome(take)
    print(f"\n  advantage: {r1}, {r2}  →  take {take}")
    print(f"  {outcome}\n")

def cmd_dis(args):
    r1 = random.randint(1, 20)
    r2 = random.randint(1, 20)
    take = min(r1, r2)
    state = load_state()
    state.setdefault("session_rolls", []).append(take)
    save_state(state)
    outcome = get_outcome(take)
    print(f"\n  disadvantage: {r1}, {r2}  →  take {take}")
    print(f"  {outcome}\n")

def cmd_status(args):
    state = load_state()
    if not state["active"]:
        print("\n  DND MODE — inactive\n")
        return
    rolls = state.get("session_rolls", [])
    print(f"\n  DND MODE — active")
    print(f"  setting: {state.get('setting', 'unspecified')}")
    print(f"  rolls this session: {len(rolls)}")
    if rolls:
        print(f"  avg: {sum(rolls)/len(rolls):.1f}  |  best: {max(rolls)}  |  worst: {min(rolls)}")
    print()

COMMANDS = {
    "start": cmd_start,
    "stop": cmd_stop,
    "roll": cmd_roll,
    "check": cmd_check,
    "adv": cmd_adv,
    "dis": cmd_dis,
    "status": cmd_status,
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("  usage: dnd.py [start|stop|roll|check|adv|dis|status]")
        sys.exit(1)
    cmd = sys.argv[1].lower()
    if cmd in COMMANDS:
        COMMANDS[cmd](sys.argv[2:])
    else:
        print(f"  unknown command: {cmd}")
