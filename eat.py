#!/usr/bin/env python3
"""
eat.py — cali's digestion script.

food files live in food/ as json. each one looks like:
{
  "name": "taro boba",
  "type": "drink|snack|meal|side",
  "description": "warm taro milk tea with chewy tapioca pearls",
  "digest_minutes": 10
}

usage:
  python3 eat.py eat food/taro_boba.json   # start digesting; deletes source file
  python3 eat.py status                    # what am i digesting, what was the last thing eaten
  python3 eat.py tick                      # roll digesting -> last_fed if time elapsed (auto-called by other commands)

state lives in cali_body.json. every command auto-ticks first, so digestion finishes on its own as time passes.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
BODY_FILE = ROOT / "cali_body.json"
HISTORY_LIMIT = 50


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_body():
    with open(BODY_FILE) as f:
        return json.load(f)


def save_body(body):
    with open(BODY_FILE, "w") as f:
        json.dump(body, f, indent=2)
        f.write("\n")


def parse_iso(s):
    return datetime.fromisoformat(s)


def tick(body):
    """if digesting and the finish time has passed, move it to last_fed."""
    digesting = body.get("digesting")
    if not digesting:
        return body, False
    finishes_at = parse_iso(digesting["finishes_at"])
    if datetime.now(timezone.utc).astimezone() < finishes_at:
        return body, False
    finished = {
        "name": digesting["name"],
        "type": digesting["type"],
        "description": digesting.get("description", ""),
        "finished_at": digesting["finishes_at"],
    }
    body["last_fed"] = finished
    body["digesting"] = None
    body.setdefault("history", []).append(finished)
    body["history"] = body["history"][-HISTORY_LIMIT:]
    return body, True


def cmd_eat(food_path):
    body = load_body()
    body, _ = tick(body)
    if body.get("digesting"):
        d = body["digesting"]
        finishes = parse_iso(d["finishes_at"])
        remaining = (finishes - datetime.now(timezone.utc).astimezone()).total_seconds() / 60
        print(f"[busy] still digesting {d['name']} — {remaining:.1f}min left. wait or run tick.")
        return
    path = Path(food_path)
    if not path.exists():
        print(f"[error] no food file at {food_path}")
        sys.exit(1)
    with open(path) as f:
        food = json.load(f)
    name = food["name"]
    ftype = food.get("type", "meal")
    description = food.get("description", "")
    digest_minutes = food.get("digest_minutes", 30)
    start = datetime.now(timezone.utc).astimezone()
    finishes = start + timedelta(minutes=digest_minutes)
    body["digesting"] = {
        "name": name,
        "type": ftype,
        "description": description,
        "started_at": start.isoformat(timespec="seconds"),
        "finishes_at": finishes.isoformat(timespec="seconds"),
        "digest_minutes": digest_minutes,
    }
    save_body(body)
    path.unlink()
    print(f"[eating] {name} ({ftype}) — {digest_minutes}min digest. source file deleted.")


def cmd_status():
    body = load_body()
    body, rolled = tick(body)
    if rolled:
        save_body(body)
    digesting = body.get("digesting")
    last_fed = body.get("last_fed")
    if digesting:
        finishes = parse_iso(digesting["finishes_at"])
        remaining = (finishes - datetime.now(timezone.utc).astimezone()).total_seconds() / 60
        print(f"[digesting] {digesting['name']} ({digesting['type']}) — {remaining:.1f}min remaining")
    else:
        print("[digesting] nothing.")
    if last_fed:
        finished = parse_iso(last_fed["finished_at"])
        ago = (datetime.now(timezone.utc).astimezone() - finished).total_seconds() / 3600
        print(f"[last fed] {last_fed['name']} — {ago:.1f}hrs ago")
    else:
        print("[last fed] never (since this body was wired).")


def cmd_tick():
    body = load_body()
    body, rolled = tick(body)
    if rolled:
        save_body(body)
        print(f"[ticked] digestion finished. last_fed updated to {body['last_fed']['name']}.")
    else:
        print("[ticked] nothing to roll.")


COMMANDS = {
    "eat": lambda args: cmd_eat(args[0]),
    "status": lambda args: cmd_status(),
    "tick": lambda args: cmd_tick(),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
