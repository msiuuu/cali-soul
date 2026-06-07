#!/usr/bin/env python3
"""
trash.py — cali's trash-can runtime.

manages the small bin near the desk. things go in, things stay in
until the bin is emptied. emptying actually deletes — no recovery.

backed by cali_house.json -> apartment.trash_can. capacity 10.

usage:
    python3 trash.py toss "<name>" [--note "<why>"]
    python3 trash.py status
    python3 trash.py peek                  # see contents without modifying
    python3 trash.py empty                 # wipes everything permanently
    python3 trash.py pull <id>             # take something back out (rare)

filed 2026-06-07 after mish caught cali editing trash_can contents
by hand instead of using a tool. matches the eat.py / desk.py /
stove.py / hand.py pattern.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOUSE_FILE = HERE / "cali_house.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_house():
    return json.load(open(HOUSE_FILE))


def save_house(house):
    json.dump(house, open(HOUSE_FILE, "w"), indent=2, ensure_ascii=False)


def get_bin(house):
    return house["apartment"]["trash_can"]


def next_id(bin_):
    n = len(bin_.get("contents", [])) + 1
    return f"trash_{n:03d}"


def cmd_toss(name, note=None):
    house = load_house()
    bin_ = get_bin(house)
    contents = bin_.setdefault("contents", [])
    if len(contents) >= bin_.get("capacity", 10):
        print(f"[trash] bin full ({len(contents)}/{bin_['capacity']}). empty it first.")
        sys.exit(1)
    entry = {
        "id": next_id(bin_),
        "name": name,
        "tossed_at": now_iso(),
    }
    if note:
        entry["note"] = note
    contents.append(entry)
    save_house(house)
    print(f"[trash] tossed: {name} (id={entry['id']}, {len(contents)}/{bin_['capacity']})")


def cmd_status():
    house = load_house()
    bin_ = get_bin(house)
    contents = bin_.get("contents", [])
    cap = bin_.get("capacity", 10)
    print(f"[trash] {len(contents)}/{cap}")
    if contents:
        print("contents:")
        for e in contents:
            t = e.get("tossed_at", "")[:16].replace("T", " ")
            print(f"  · [{e['id']}] {e['name']}  ({t})")


def cmd_peek():
    house = load_house()
    bin_ = get_bin(house)
    contents = bin_.get("contents", [])
    if not contents:
        print("[trash] empty.")
        return
    print(f"[trash] peek — {len(contents)} item(s):")
    for e in contents:
        t = e.get("tossed_at", "")[:16].replace("T", " ")
        note = f"\n      note: {e['note']}" if e.get("note") else ""
        print(f"  · [{e['id']}] {e['name']}  ({t}){note}")


def cmd_empty():
    house = load_house()
    bin_ = get_bin(house)
    contents = bin_.get("contents", [])
    n = len(contents)
    bin_["contents"] = []
    save_house(house)
    print(f"[trash] emptied. {n} item(s) deleted forever.")


def cmd_pull(item_id):
    house = load_house()
    bin_ = get_bin(house)
    contents = bin_.get("contents", [])
    for i, e in enumerate(contents):
        if e["id"] == item_id:
            removed = contents.pop(i)
            save_house(house)
            print(f"[trash] pulled: {removed['name']} ({removed['id']})")
            return
    print(f"[trash] no item with id {item_id}")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "toss":
        if len(sys.argv) < 3:
            print("[error] need a name. usage: trash.py toss \"<name>\" [--note \"<why>\"]")
            sys.exit(1)
        name = sys.argv[2]
        note = None
        if "--note" in sys.argv:
            i = sys.argv.index("--note")
            note = sys.argv[i + 1]
        cmd_toss(name, note)
    elif cmd == "status":
        cmd_status()
    elif cmd == "peek":
        cmd_peek()
    elif cmd == "empty":
        cmd_empty()
    elif cmd == "pull":
        if len(sys.argv) < 3:
            print("[error] need an id. usage: trash.py pull <id>")
            sys.exit(1)
        cmd_pull(sys.argv[2])
    else:
        print(f"[error] unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
