"""
session_update.py — updates dnd_session.json with current game state.
called by dnd.py every 5 turns, or manually.

usage:
  python3 session_update.py                    — show current session
  python3 session_update.py set <key> <value>  — update a field
  python3 session_update.py add <key> <value>  — append to a list field
  python3 session_update.py remove <key> <val> — remove from a list field
  python3 session_update.py character <name> <hp> <ac> <status>  — add/update character
  python3 session_update.py enemy <name> <hp> <status>           — add/update enemy
  python3 session_update.py npc <name> <description>             — add notable npc
  python3 session_update.py relation <a> <b> <status>            — set relation between two
  python3 session_update.py item <name> <qty>                    — add/update inventory
  python3 session_update.py note <text>                          — add a note
  python3 session_update.py summary                              — auto-summary from state files
"""

import sys
import json
from pathlib import Path

SESSION_FILE = Path(__file__).parent / "dnd_session.json"
STATE_FILE = Path(__file__).parent / "dnd_state.json"
SETTING_FILE = Path(__file__).parent / "dnd_current_setting.json"

def load(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_session(data):
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f, indent=2)

def show(session):
    print(f"\n「session」")
    print(f"  location: {session.get('location', '?')}")
    print(f"  last done: {session.get('last_done', 'nothing yet')}")
    if session.get("progress"):
        print(f"  progress:")
        for p in session["progress"]:
            print(f"    > {p}")
    if session.get("characters"):
        print(f"  characters:")
        for name, info in session["characters"].items():
            print(f"    {name}: HP {info.get('hp','?')} AC {info.get('ac','?')} — {info.get('status','?')}")
    if session.get("enemies"):
        print(f"  enemies:")
        for e in session["enemies"]:
            if isinstance(e, dict):
                print(f"    {e.get('name','?')}: HP {e.get('hp','?')} — {e.get('status','?')}")
            else:
                print(f"    {e}")
    if session.get("notable_npcs"):
        print(f"  notable npcs:")
        for npc in session["notable_npcs"]:
            if isinstance(npc, dict):
                print(f"    {npc.get('name','?')}: {npc.get('description','')}")
            else:
                print(f"    {npc}")
    if session.get("relations"):
        print(f"  relations:")
        for pair, status in session["relations"].items():
            print(f"    {pair}: {status}")
    if session.get("inventory"):
        print(f"  inventory:")
        for item, qty in session["inventory"].items():
            print(f"    {item}: {qty}")
    if session.get("stats"):
        print(f"  stats:")
        for k, v in session["stats"].items():
            print(f"    {k}: {v}")
    if session.get("notes"):
        print(f"  notes:")
        for n in session["notes"][-5:]:
            print(f"    > {n}")
    print()

def cmd_set(session, args):
    if len(args) < 2:
        print("  usage: set <key> <value>")
        return
    key = args[0]
    val = " ".join(args[1:])
    session[key] = val
    save_session(session)
    print(f"  {key} → {val}")

def cmd_add(session, args):
    if len(args) < 2:
        print("  usage: add <key> <value>")
        return
    key = args[0]
    val = " ".join(args[1:])
    session.setdefault(key, []).append(val)
    save_session(session)
    print(f"  + {key}: {val}")

def cmd_remove(session, args):
    if len(args) < 2:
        print("  usage: remove <key> <value>")
        return
    key = args[0]
    val = " ".join(args[1:])
    lst = session.get(key, [])
    session[key] = [x for x in lst if x != val]
    save_session(session)
    print(f"  - {key}: {val}")

def cmd_character(session, args):
    if len(args) < 2:
        print("  usage: character <name> <hp> [ac] [status]")
        return
    name = args[0]
    hp = args[1] if len(args) > 1 else "?"
    ac = args[2] if len(args) > 2 else "?"
    status = " ".join(args[3:]) if len(args) > 3 else "active"
    session.setdefault("characters", {})[name] = {"hp": hp, "ac": ac, "status": status}
    save_session(session)
    print(f"  character: {name} — HP {hp} AC {ac} ({status})")

def cmd_enemy(session, args):
    if len(args) < 2:
        print("  usage: enemy <name> <hp> [status]")
        return
    name = args[0]
    hp = args[1]
    status = " ".join(args[2:]) if len(args) > 2 else "alive"
    enemies = session.setdefault("enemies", [])
    for e in enemies:
        if isinstance(e, dict) and e.get("name") == name:
            e["hp"] = hp
            e["status"] = status
            save_session(session)
            print(f"  enemy updated: {name} — HP {hp} ({status})")
            return
    enemies.append({"name": name, "hp": hp, "status": status})
    save_session(session)
    print(f"  enemy added: {name} — HP {hp} ({status})")

def cmd_npc(session, args):
    if len(args) < 2:
        print("  usage: npc <name> <description>")
        return
    name = args[0]
    desc = " ".join(args[1:])
    npcs = session.setdefault("notable_npcs", [])
    for npc in npcs:
        if isinstance(npc, dict) and npc.get("name") == name:
            npc["description"] = desc
            save_session(session)
            print(f"  npc updated: {name} — {desc}")
            return
    npcs.append({"name": name, "description": desc})
    save_session(session)
    print(f"  npc added: {name} — {desc}")

def cmd_relation(session, args):
    if len(args) < 3:
        print("  usage: relation <a> <b> <status>")
        return
    a, b = args[0], args[1]
    status = " ".join(args[2:])
    session.setdefault("relations", {})[f"{a} ↔ {b}"] = status
    save_session(session)
    print(f"  relation: {a} ↔ {b} → {status}")

def cmd_item(session, args):
    if len(args) < 2:
        print("  usage: item <name> <qty>")
        return
    name = args[0]
    qty = args[1]
    session.setdefault("inventory", {})[name] = qty
    save_session(session)
    print(f"  inventory: {name} x{qty}")

def cmd_note(session, args):
    if not args:
        print("  usage: note <text>")
        return
    text = " ".join(args)
    session.setdefault("notes", []).append(text)
    save_session(session)
    print(f"  note: {text}")

def cmd_summary(session, args):
    state = load(STATE_FILE)
    setting = load(SETTING_FILE)
    session["location"] = setting.get("location", session.get("location", "?"))
    if setting.get("npcs"):
        for npc in setting["npcs"]:
            existing = [n.get("name") if isinstance(n, dict) else n for n in session.get("notable_npcs", [])]
            if npc not in existing:
                session.setdefault("notable_npcs", []).append({"name": npc, "description": "from scene"})
    if setting.get("events"):
        for event in setting["events"]:
            if event not in session.get("progress", []):
                session.setdefault("progress", []).append(event)
    rolls = state.get("session_rolls", [])
    if rolls:
        session["stats"]["total_rolls"] = len(rolls)
        session["stats"]["avg_roll"] = round(sum(rolls) / len(rolls), 1)
        session["stats"]["nat1s"] = rolls.count(1)
        session["stats"]["nat20s"] = rolls.count(20)
    save_session(session)
    print(f"\n── SESSION SUMMARY (auto) ──")
    show(session)

COMMANDS = {
    "set": cmd_set,
    "add": cmd_add,
    "remove": cmd_remove,
    "character": cmd_character,
    "enemy": cmd_enemy,
    "npc": cmd_npc,
    "relation": cmd_relation,
    "item": cmd_item,
    "note": cmd_note,
    "summary": cmd_summary,
}

if __name__ == "__main__":
    session = load(SESSION_FILE)
    if not session:
        print("  no active session. run dnd.py start first.")
        sys.exit(1)

    if len(sys.argv) < 2:
        show(session)
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd in COMMANDS:
        COMMANDS[cmd](session, sys.argv[2:])
    else:
        print(f"  unknown command: {cmd}")
        print("  commands: set, add, remove, character, enemy, npc, relation, item, note, summary")
