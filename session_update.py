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
    if session.get("spells"):
        print(f"  spells:")
        for who, data in session["spells"].items():
            known = data.get("known", [])
            slots = data.get("slots", {})
            print(f"    {who}: {', '.join(known) if known else 'none'} | slots: {slots.get('used',0)}/{slots.get('max',0)}")
    money = session.get("money", {})
    if any(v for v in money.values()):
        print(f"  money: {money.get('gold',0)}g {money.get('silver',0)}s {money.get('copper',0)}c")
    quests = session.get("quests", {})
    if quests.get("active"):
        print(f"  quests:")
        for q in quests["active"]:
            print(f"    ◈ {q}")
    if quests.get("completed"):
        for q in quests["completed"]:
            print(f"    ✓ {q}")
    if session.get("rumors"):
        print(f"  rumors:")
        for r in session["rumors"]:
            print(f"    ◇ {r}")
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

def cmd_spell(session, args):
    if not args:
        spells = session.get("spells", {})
        if not spells:
            print("  no spells tracked")
            return
        for who, data in spells.items():
            print(f"  {who}:")
            for s in data.get("known", []):
                print(f"    ✦ {s}")
            slots = data.get("slots", {})
            if slots:
                print(f"    slots: {slots.get('used',0)}/{slots.get('max',0)}")
            cast = data.get("cast_this_session", [])
            if cast:
                print(f"    cast: {', '.join(cast)}")
        return
    sub = args[0].lower()
    if sub == "learn" and len(args) >= 3:
        who = args[1]
        spell_name = " ".join(args[2:])
        session.setdefault("spells", {}).setdefault(who, {"known": [], "slots": {"used": 0, "max": 1}, "cast_this_session": []})
        session["spells"][who]["known"].append(spell_name)
        save_session(session)
        print(f"  {who} learned: {spell_name}")
    elif sub == "cast" and len(args) >= 3:
        who = args[1]
        spell_name = " ".join(args[2:])
        data = session.setdefault("spells", {}).setdefault(who, {"known": [], "slots": {"used": 0, "max": 1}, "cast_this_session": []})
        data["cast_this_session"].append(spell_name)
        data["slots"]["used"] = data["slots"].get("used", 0) + 1
        save_session(session)
        used = data["slots"]["used"]
        mx = data["slots"]["max"]
        print(f"  {who} cast: {spell_name} (slots: {used}/{mx})")
    elif sub == "slots" and len(args) >= 3:
        who = args[1]
        mx = int(args[2])
        session.setdefault("spells", {}).setdefault(who, {"known": [], "slots": {"used": 0, "max": 1}, "cast_this_session": []})
        session["spells"][who]["slots"]["max"] = mx
        save_session(session)
        print(f"  {who} max slots: {mx}")
    elif sub == "reset" and len(args) >= 2:
        who = args[1]
        if who in session.get("spells", {}):
            session["spells"][who]["slots"]["used"] = 0
            session["spells"][who]["cast_this_session"] = []
            save_session(session)
            print(f"  {who} spell slots reset")
    else:
        print("  usage: spell [learn|cast|slots|reset] <who> [spell_name|max]")

def cmd_money(session, args):
    money = session.setdefault("money", {"gold": 0, "silver": 0, "copper": 0})
    if not args:
        print(f"  money: {money.get('gold',0)}g {money.get('silver',0)}s {money.get('copper',0)}c")
        return
    if len(args) >= 2:
        amount = int(args[0])
        currency = args[1].lower()
        if currency in ("g", "gold"): currency = "gold"
        elif currency in ("s", "silver"): currency = "silver"
        elif currency in ("c", "copper"): currency = "copper"
        money[currency] = money.get(currency, 0) + amount
        save_session(session)
        print(f"  {'+'if amount>=0 else ''}{amount} {currency} → {money.get('gold',0)}g {money.get('silver',0)}s {money.get('copper',0)}c")
    else:
        print("  usage: money <amount> <gold|silver|copper>")

def cmd_quest(session, args):
    quests = session.setdefault("quests", {"active": [], "completed": []})
    if not args:
        if quests["active"]:
            print("  active quests:")
            for q in quests["active"]:
                print(f"    ◈ {q}")
        if quests["completed"]:
            print("  completed:")
            for q in quests["completed"]:
                print(f"    ✓ {q}")
        if not quests["active"] and not quests["completed"]:
            print("  no quests")
        return
    sub = args[0].lower()
    text = " ".join(args[1:])
    if sub == "add":
        quests["active"].append(text)
        save_session(session)
        print(f"  quest added: {text}")
    elif sub == "done":
        if text in quests["active"]:
            quests["active"].remove(text)
        quests["completed"].append(text)
        save_session(session)
        print(f"  quest completed: {text}")
    elif sub == "drop":
        quests["active"] = [q for q in quests["active"] if q != text]
        save_session(session)
        print(f"  quest dropped: {text}")
    else:
        print("  usage: quest [add|done|drop] <text>")

def cmd_rumor(session, args):
    rumors = session.setdefault("rumors", [])
    if not args:
        if rumors:
            print("  rumors:")
            for r in rumors:
                print(f"    ◇ {r}")
        else:
            print("  no rumors")
        return
    text = " ".join(args)
    rumors.append(text)
    save_session(session)
    print(f"  rumor: {text}")

def cmd_sheet(session, args):
    chars_file = Path(__file__).parent / "dnd_characters.json"
    chars = {}
    if chars_file.exists():
        with open(chars_file) as f:
            chars = json.load(f)
    if not args:
        for name, data in chars.items():
            print(f"\n「{data.get('name', name)}」")
            print(f"  class: {data.get('class', '?')} | race: {data.get('race', '?')}")
            stats = data.get("stats", data)
            for s in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
                entry = stats.get(s, {})
                if isinstance(entry, dict):
                    score = entry.get("score", "?")
                    mod = entry.get("mod", "?")
                    note = entry.get("note", "")
                    print(f"    {s}: {score} ({mod:+d}) {note}" if isinstance(mod, int) else f"    {s}: {score} ({mod}) {note}")
                elif isinstance(entry, int):
                    mod = (entry - 10) // 2
                    print(f"    {s}: {entry} ({mod:+d})")
            print(f"  HP: {data.get('HP', '?')}  AC: {data.get('AC', '?')}")
            print(f"  weapon: {data.get('weapon', data.get('combat', {}).get('weapon', '?'))}")
            print(f"  flaw: {data.get('flaw', '?')}")
        print()
        return
    who = args[0].lower()
    char = chars.get(who)
    if not char:
        print(f"  unknown character: {who}")
        return
    print(f"\n「{char.get('name', who)}」")
    stats = char.get("stats", char)
    for s in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
        entry = stats.get(s, {})
        if isinstance(entry, dict):
            print(f"  {s}: {entry.get('score','?')} ({entry.get('mod','?')}) — {entry.get('note','')}")
        elif isinstance(entry, int):
            print(f"  {s}: {entry} ({(entry-10)//2:+d})")
    print()

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
    "spell": cmd_spell,
    "money": cmd_money,
    "quest": cmd_quest,
    "rumor": cmd_rumor,
    "sheet": cmd_sheet,
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
