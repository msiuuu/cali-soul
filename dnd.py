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
    return (stat_value - 10) // 2

SKILLS = {
    "athletics": "STR",
    "acrobatics": "DEX", "sleight of hand": "DEX", "stealth": "DEX",
    "arcana": "INT", "history": "INT", "investigation": "INT", "nature": "INT", "religion": "INT",
    "animal handling": "WIS", "insight": "WIS", "medicine": "WIS", "perception": "WIS", "survival": "WIS",
    "deception": "CHA", "intimidation": "CHA", "performance": "CHA", "persuasion": "CHA",
}

PROF_BONUS = 2

def get_skill_mod(char, skill_name):
    skill_lower = skill_name.lower()
    ability = SKILLS.get(skill_lower)
    if not ability:
        return None, None, None

    stats = char.get("stats", char)
    stat_entry = stats.get(ability, {})
    if isinstance(stat_entry, dict):
        stat_val = stat_entry.get("score", 10)
    else:
        stat_val = stat_entry if isinstance(stat_entry, int) else 10

    base_mod = get_modifier(stat_val)
    proficient_list = [s.lower() for s in char.get("skills", {}).get("proficient", [])]
    expertise_list = [s.lower() for s in char.get("skills", {}).get("expertise", [])]

    if skill_lower in expertise_list:
        total_mod = base_mod + PROF_BONUS * 2
        tag = "expertise"
    elif skill_lower in proficient_list:
        total_mod = base_mod + PROF_BONUS
        tag = "proficient"
    else:
        total_mod = base_mod
        tag = None

    return total_mod, ability, tag

def cmd_start(args):
    state = load_state()
    if args:
        setting = " ".join(args)
    else:
        setting = input("\n  [enter scenario]: ").strip()
        if not setting:
            setting = "unspecified"
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
        print("  usage: dnd.py check [skill or ability] [dc] [cali|mish]")
        print("  abilities: STR DEX CON INT WIS CHA")
        print("  skills: " + ", ".join(sorted(SKILLS.keys())))
        return

    dc = 10
    who = "cali"
    skill_parts = []
    for a in args:
        if a.isdigit():
            dc = int(a)
        elif a.lower() in ("cali", "mish"):
            who = a.lower()
        else:
            skill_parts.append(a)

    check_name = " ".join(skill_parts).strip()
    chars = load_chars()
    char = chars.get(who)
    if not char:
        print(f"  unknown character: {who}")
        return

    is_skill = check_name.lower() in SKILLS
    is_ability = check_name.upper() in ("STR", "DEX", "CON", "INT", "WIS", "CHA")

    if is_skill:
        mod, ability, tag = get_skill_mod(char, check_name)
        label = f"{check_name.title()} ({ability})"
        if tag: label += f" [{tag}]"
    elif is_ability:
        ability = check_name.upper()
        stats = char.get("stats", char)
        stat_entry = stats.get(ability, {})
        if isinstance(stat_entry, dict):
            stat_val = stat_entry.get("score", 10)
        else:
            stat_val = stat_entry if isinstance(stat_entry, int) else 10
        mod = get_modifier(stat_val)
        label = f"{ability} check"
        tag = None
    else:
        print(f"  unknown skill or ability: {check_name}")
        print(f"  skills: {', '.join(sorted(SKILLS.keys()))}")
        return

    roll_val = random.randint(1, 20)
    total = roll_val + mod
    passed = total >= dc
    state = load_state()
    state.setdefault("session_rolls", []).append(roll_val)
    save_state(state)
    outcome = get_outcome(roll_val)
    sign = f"+{mod}" if mod >= 0 else str(mod)
    status = "PASS" if passed else "FAIL"
    setting = state.get("setting", "unknown")

    print(f"\n── ROLLS ──")
    print(f"  {label} ({who}): {roll_val} ({sign}) = {total} vs DC {dc} → {status}")
    print(f"  {outcome}")
    if roll_val == 1: print(f"  NAT 1 — auto fail")
    if roll_val == 20 and not passed: print(f"  NAT 20 — your best. santa didn't flinch.")
    elif roll_val == 20: print(f"  NAT 20 — your best, and it was enough.")
    print()

    print(f"「{setting}」")
    print(f"  {who}'s {label}")
    print()
    print(f"  [prose]")
    print()

    hp = char.get("HP", "?")
    ac = char.get("AC", "?")
    name = char.get("name", who)
    print(f"「{name}」")
    print(f"  HP: {hp}  AC: {ac}")
    print(f"  Status: {'fine' if passed else 'not great'}")
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
