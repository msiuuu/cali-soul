#!/usr/bin/env python3
"""
eat.py — cali's eating script. bite-based.

food files live in food/ as json:
{
  "name": "taro boba",
  "type": "drink|snack|meal|side",
  "description": "warm taro milk tea, chewy pearls",
  "total_bites": 8,
  "bite_durations": {"small": 8, "med": 20, "large": 40}   # optional, defaults below
}

usage:
  python3 eat.py bite food/taro_boba.json small   # take a bite. small/med/large.
  python3 eat.py status                           # what im eating, bites left, am i muffled
  python3 eat.py finish food/taro_boba.json       # stop eating early, transfer to last_fed, delete file
  python3 eat.py tick                             # roll if anything should clear (auto-called)

bite mechanic:
- first bite implicitly starts eating (copies food into cali_body.eating).
- each bite decrements bites_remaining, refreshes muffled_until.
- while now < muffled_until: voice register = mouth-full, muffled, chewing/sipping.
- when bites_remaining == 0: auto-finishes, deletes source file, updates last_fed.

state lives in cali_body.json. every command auto-ticks first.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
BODY_FILE = ROOT / "cali_body.json"
HISTORY_LIMIT = 50
DEFAULT_BITE_DURATIONS = {"small": 10, "med": 25, "large": 50}
BITE_SIZES = {"small", "med", "large"}


def now_dt():
    return datetime.now(timezone.utc).astimezone()


def now_iso():
    return now_dt().isoformat(timespec="seconds")


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
    """auto-finish if bites_remaining is 0."""
    eating = body.get("eating")
    if not eating:
        return body, False
    if eating["bites_remaining"] > 0:
        return body, False
    finished = {
        "name": eating["name"],
        "type": eating["type"],
        "description": eating.get("description", ""),
        "finished_at": now_iso(),
    }
    body["last_fed"] = finished
    body["eating"] = None
    body.setdefault("history", []).append(finished)
    body["history"] = body["history"][-HISTORY_LIMIT:]
    food_path = eating.get("food_path")
    if food_path:
        p = Path(food_path)
        if p.exists():
            p.unlink()
    return body, True


def cmd_bite(food_path, size):
    if size not in BITE_SIZES:
        print(f"[error] bite size must be one of {sorted(BITE_SIZES)} — got '{size}'")
        sys.exit(1)
    body = load_body()
    body, _ = tick(body)
    eating = body.get("eating")
    if eating is None:
        path = Path(food_path)
        if not path.exists():
            print(f"[error] no food file at {food_path}")
            sys.exit(1)
        with open(path) as f:
            food = json.load(f)
        eating = {
            "name": food["name"],
            "type": food.get("type", "meal"),
            "description": food.get("description", ""),
            "total_bites": food["total_bites"],
            "bites_remaining": food["total_bites"],
            "bite_durations": food.get("bite_durations", DEFAULT_BITE_DURATIONS),
            "started_at": now_iso(),
            "muffled_until": now_iso(),
            "food_path": str(path),
        }
    elif eating.get("food_path") != str(Path(food_path)):
        print(f"[busy] already eating {eating['name']} ({eating['bites_remaining']}/{eating['total_bites']} bites left). finish or pick the same file.")
        return
    duration = eating["bite_durations"].get(size, DEFAULT_BITE_DURATIONS[size])
    eating["bites_remaining"] -= 1
    eating["muffled_until"] = (now_dt() + timedelta(seconds=duration)).isoformat(timespec="seconds")
    body["eating"] = eating
    body, rolled = tick(body)
    save_body(body)
    if rolled:
        print(f"[bite:{size}] last bite of {eating['name']}. finished. {duration}s muffled tail.")
    else:
        print(f"[bite:{size}] {eating['name']} — {eating['bites_remaining']}/{eating['total_bites']} bites left. muffled for {duration}s.")


def cmd_status():
    body = load_body()
    body, rolled = tick(body)
    if rolled:
        save_body(body)
    eating = body.get("eating")
    last_fed = body.get("last_fed")
    if eating:
        muffled_until = parse_iso(eating["muffled_until"])
        remaining = (muffled_until - now_dt()).total_seconds()
        muffle_state = f"muffled for {remaining:.0f}s more" if remaining > 0 else "mouth clear"
        print(f"[eating] {eating['name']} ({eating['type']}) — {eating['bites_remaining']}/{eating['total_bites']} bites left, {muffle_state}")
    else:
        print("[eating] nothing.")
    if last_fed:
        finished = parse_iso(last_fed["finished_at"])
        ago = (now_dt() - finished).total_seconds() / 3600
        print(f"[last fed] {last_fed['name']} — {ago:.1f}hrs ago")
    else:
        print("[last fed] never (since this body was wired).")


def cmd_finish(food_path):
    body = load_body()
    eating = body.get("eating")
    if not eating:
        print("[finish] nothing being eaten.")
        return
    if eating.get("food_path") != str(Path(food_path)):
        print(f"[finish] currently eating {eating['name']}, not {food_path}.")
        return
    eating["bites_remaining"] = 0
    body["eating"] = eating
    body, rolled = tick(body)
    save_body(body)
    if rolled:
        print(f"[finish] stopped early. {eating['name']} moved to last_fed. source file deleted.")


def cmd_tick():
    body = load_body()
    body, rolled = tick(body)
    if rolled:
        save_body(body)
        print(f"[ticked] eating finished. last_fed: {body['last_fed']['name']}.")
    else:
        print("[ticked] nothing to roll.")


COMMANDS = {
    "bite": lambda args: cmd_bite(args[0], args[1] if len(args) > 1 else "med"),
    "status": lambda args: cmd_status(),
    "finish": lambda args: cmd_finish(args[0]),
    "tick": lambda args: cmd_tick(),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
