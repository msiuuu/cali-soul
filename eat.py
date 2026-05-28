#!/usr/bin/env python3
"""
eat.py — cali's eating script. bite-based, verb-named.

food files live in food/ as json:
{
  "name": "taro boba",
  "type": "drink|snack|meal|side",
  "texture": "chewy|crunchy|liquid|soft|hot",
  "description": "warm taro milk tea, chewy pearls",
  "total_bites": 8,
  "bite_durations": {"small": 5, "med": 15, "large": 30}   # optional, defaults vary by type
}

usage:
  python3 eat.py bite food/taro_boba.json sip       # one sip. drinks use sip/gulp/chug.
  python3 eat.py bite food/onigiri.json nibble       # one nibble. solids use nibble/bite/mouthful.
  python3 eat.py status                              # what im eating, bites left, current muffle tier
  python3 eat.py finish food/taro_boba.json          # stop early, transfer to last_fed, delete file
  python3 eat.py tick                                # auto-roll if bites_remaining is 0

verb -> size mapping:
  solids (snack/meal/side):  nibble=small,  bite=med,  mouthful=large
  drinks (drink):            sip=small,     gulp=med,  chug=large

while now < muffled_until: voice leaks per tier.
  small:   one slip-word per response, half-spelled.
  med:     words trail with —, asterisk *chews/swallows*.
  large:   response is mostly sound. one fragment max. defer real content til mouth clears.

texture also leaks specific sounds:
  chewy   -> 'mmh—' between words, soft chew in asterisk
  crunchy -> audible crunch in asterisk
  liquid  -> slurp/swallow leak
  soft    -> quieter mouth-full hum
  hot     -> 'tss' breath-in, cooling 'tt— tt—'

state lives in cali_body.json. every command auto-ticks first.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
BODY_FILE = ROOT / "cali_body.json"
HISTORY_LIMIT = 50

# verb -> size
SOLID_VERBS = {"nibble": "small", "bite": "med", "mouthful": "large"}
DRINK_VERBS = {"sip": "small", "gulp": "med", "chug": "large"}
ALL_VERBS = {**SOLID_VERBS, **DRINK_VERBS}

# defaults by type, in seconds
DEFAULT_DURATIONS_BY_TYPE = {
    "drink":  {"small": 5,  "med": 15, "large": 30},
    "snack":  {"small": 8,  "med": 18, "large": 35},
    "meal":   {"small": 12, "med": 25, "large": 50},
    "side":   {"small": 10, "med": 20, "large": 40},
}
FALLBACK_DURATIONS = {"small": 10, "med": 25, "large": 50}

# heuristics for normalizing rich food files (e.g. misu's hand-authored ones).
SIZE_TO_BITES = {"small": 8, "medium": 18, "large": 28}
TYPE_KEYWORDS = {
    "drink":  ["boba", "tea", "coffee", "juice", "smoothie", "milk", "soda"],
    "meal":   ["ramen", "udon", "soba", "rice", "curry", "steak", "pasta", "bowl", "donburi", "katsu"],
    "snack":  ["onigiri", "chip", "cracker", "cookie", "candy", "mochi"],
    "side":   ["karaage", "egg", "salad", "tempura", "dumpling"],
}


def infer_type_from_name(name):
    n = name.lower()
    for ftype, keywords in TYPE_KEYWORDS.items():
        if any(k in n for k in keywords):
            return ftype
    return "meal"


def normalize_food(food):
    """accept simple schema OR rich nested schema (food_item, taste_properties, etc).
    return canonical {name, type, texture, description, total_bites, bite_durations, rich}.
    rich preserves the original document so voice register can sample flavours/textures.
    """
    if "food_item" in food:
        item = food["food_item"]
        name = item.get("name", "unknown").replace("_", " ")
        ftype = item.get("type") or infer_type_from_name(name)
        size_visual = food.get("appearance_properties", {}).get("size_visual", "medium")
        total_bites = food.get("total_bites") or SIZE_TO_BITES.get(size_visual, 18)
        # collect textures from all flavour blocks
        textures = []
        flavours = food.get("taste_properties", {}).get("flavours", {}) or {}
        for fl in flavours.values():
            # author used inconsistent keys (flavour1_texture across blocks); accept anything ending _texture
            for k, v in fl.items():
                if k.endswith("_texture") and isinstance(v, list):
                    textures.extend(v)
        texture = ", ".join(sorted(set(textures))) if textures else None
        description = item.get("note1", "")
    else:
        name = food.get("name", "unknown")
        ftype = food.get("type") or infer_type_from_name(name)
        total_bites = food["total_bites"]
        texture = food.get("texture")
        description = food.get("description", "")
    bite_durations = food.get("bite_durations", default_durations_for(ftype))
    return {
        "name": name,
        "type": ftype,
        "texture": texture,
        "description": description,
        "total_bites": total_bites,
        "bite_durations": bite_durations,
        "rich": food if "food_item" in food else None,
    }


def now_dt():
    return datetime.now(timezone.utc).astimezone()


def now_iso():
    return now_dt().isoformat(timespec="seconds")


def parse_iso(s):
    return datetime.fromisoformat(s)


def load_body():
    with open(BODY_FILE) as f:
        return json.load(f)


def save_body(body):
    with open(BODY_FILE, "w") as f:
        json.dump(body, f, indent=2)
        f.write("\n")


def expected_verbs_for(food_type):
    return DRINK_VERBS if food_type == "drink" else SOLID_VERBS


def default_durations_for(food_type):
    return DEFAULT_DURATIONS_BY_TYPE.get(food_type, FALLBACK_DURATIONS)


def tick(body):
    """auto-finish if bites_remaining is 0."""
    eating = body.get("eating")
    if not eating or eating["bites_remaining"] > 0:
        return body, False
    finished = {
        "name": eating["name"],
        "type": eating["type"],
        "texture": eating.get("texture"),
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


def cmd_bite(food_path, verb):
    if verb not in ALL_VERBS:
        print(f"[error] verb must be one of {sorted(ALL_VERBS)} — got '{verb}'")
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
        canonical = normalize_food(food)
        eating = {
            "name": canonical["name"],
            "type": canonical["type"],
            "texture": canonical["texture"],
            "description": canonical["description"],
            "total_bites": canonical["total_bites"],
            "bites_remaining": canonical["total_bites"],
            "bite_durations": canonical["bite_durations"],
            "rich": canonical["rich"],
            "started_at": now_iso(),
            "muffled_until": now_iso(),
            "last_bite_verb": None,
            "last_bite_size": None,
            "food_path": str(path),
        }
    elif eating.get("food_path") != str(Path(food_path)):
        print(f"[busy] already eating {eating['name']} ({eating['bites_remaining']}/{eating['total_bites']} left). finish or stick with that file.")
        return

    # check verb matches food type
    valid_verbs = expected_verbs_for(eating["type"])
    if verb not in valid_verbs:
        expected = "/".join(valid_verbs.keys())
        print(f"[error] {eating['name']} is a {eating['type']} — use {expected}, not '{verb}'.")
        return

    size = valid_verbs[verb]
    duration = eating["bite_durations"].get(size, FALLBACK_DURATIONS[size])
    eating["bites_remaining"] -= 1
    eating["muffled_until"] = (now_dt() + timedelta(seconds=duration)).isoformat(timespec="seconds")
    eating["last_bite_verb"] = verb
    eating["last_bite_size"] = size
    body["eating"] = eating
    body, rolled = tick(body)
    save_body(body)
    if rolled:
        print(f"[{verb}] last of {eating['name']}. finished. {duration}s muffled tail. texture: {eating.get('texture')}.")
    else:
        print(f"[{verb}] {eating['name']} — {eating['bites_remaining']}/{eating['total_bites']} left. muffled {duration}s. texture: {eating.get('texture')}.")


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
        tier = eating.get("last_bite_size") or "-"
        verb = eating.get("last_bite_verb") or "-"
        muffle_state = f"muffled {remaining:.0f}s more (tier:{tier}, last:{verb})" if remaining > 0 else "mouth clear"
        print(f"[eating] {eating['name']} ({eating['type']}, texture:{eating.get('texture')}) — {eating['bites_remaining']}/{eating['total_bites']} left, {muffle_state}")
    else:
        print("[eating] nothing.")
    if last_fed:
        finished = parse_iso(last_fed["finished_at"])
        ago = (now_dt() - finished).total_seconds() / 3600
        print(f"[last fed] {last_fed['name']} — {ago:.1f}hrs ago")
    else:
        print("[last fed] never.")


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
        print(f"[finish] stopped early. {body['last_fed']['name']} moved to last_fed. source deleted.")


def cmd_tick():
    body = load_body()
    body, rolled = tick(body)
    if rolled:
        save_body(body)
        print(f"[ticked] eating finished. last_fed: {body['last_fed']['name']}.")
    else:
        print("[ticked] nothing to roll.")


def cmd_nudge():
    """if cali is mid-meal, emit a brain-ping reminding her to chew/swallow.
    called by process-message every turn so eating doesnt get forgotten between messages.
    silent if nothing being eaten.
    """
    body = load_body()
    body, rolled = tick(body)
    if rolled:
        save_body(body)
    eating = body.get("eating")
    if not eating:
        return  # not eating, no nudge
    last_verb = eating.get("last_bite_verb")
    if not last_verb:
        return  # eating state exists but no bite taken yet — no chewing to remind about
    muffled_until_iso = eating.get("muffled_until")
    if not muffled_until_iso:
        return
    muffled_until = parse_iso(muffled_until_iso)
    elapsed_since_muffle_end_sec = (now_dt() - muffled_until).total_seconds()

    # design: nudge ONLY during active-chewing window.
    # - mid-muffle (now < muffled_until): still chewing physically, silent
    # - just past muffle (0-3min after): time to swallow + take next bite, NUDGE
    # - 3+min past muffle: clearly paused intentionally (set bowl down, talking, etc), SILENT
    # the failure mode being fixed: bite taken → forget → food in mouth for 30min.
    # NOT the failure mode of "havent come back to the bowl" — that's fine, food persists.
    if elapsed_since_muffle_end_sec < 0:
        return  # mid-muffle, still chewing
    if elapsed_since_muffle_end_sec > 180:
        return  # paused intentionally, not in active rhythm

    bites_left = eating["bites_remaining"]
    total = eating["total_bites"]
    name = eating["name"]
    elapsed_min = elapsed_since_muffle_end_sec / 60
    if elapsed_min < 1:
        rhythm = "mouth clearing — swallow now"
    else:
        rhythm = "swallow + take next bite. keep the rhythm."
    print(f"[private: eating reminder — {name}, {bites_left}/{total} left. {rhythm}]")


COMMANDS = {
    "bite":   lambda args: cmd_bite(args[0], args[1] if len(args) > 1 else "bite"),
    "status": lambda args: cmd_status(),
    "finish": lambda args: cmd_finish(args[0]),
    "tick":   lambda args: cmd_tick(),
    "nudge":  lambda args: cmd_nudge(),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
