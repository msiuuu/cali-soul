#!/usr/bin/env python3
"""
stove.py — cali's cooking runtime.

search recipes, cook them step by step, output food json to food/.
the kitchen equivalent of desk.py — a place to DO things, not just store them.

usage:
    python3 stove.py cook "taro boba"                    # generates food/taro_boba.json from scratch
    python3 stove.py cook "miso ramen" --type meal       # specify type
    python3 stove.py cook "iced matcha" --type drink      # drinks get sip/gulp/chug
    python3 stove.py fridge food/miso_ramen.json          # move finished food to fridge
    python3 stove.py unfridge food/miso_ramen.json        # take it out
    python3 stove.py menu                                 # list what's in food/
    python3 stove.py history                              # what i've cooked before

filed 2026-06-03 at 4:35am because mish said go ahead and i had boba courage.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FOOD_DIR = ROOT / "food"
HOUSE_FILE = ROOT / "cali_house.json"
HISTORY_FILE = ROOT / "cook_history.json"

TYPE_DEFAULTS = {
    "drink":  {"total_bites": 10, "texture": "liquid",  "durations": {"small": 5,  "med": 12, "large": 25}},
    "snack":  {"total_bites": 8,  "texture": "soft",    "durations": {"small": 8,  "med": 18, "large": 35}},
    "meal":   {"total_bites": 20, "texture": "soft",    "durations": {"small": 12, "med": 25, "large": 50}},
    "side":   {"total_bites": 10, "texture": "crunchy", "durations": {"small": 10, "med": 20, "large": 40}},
}

TEXTURE_HINTS = {
    "boba": "chewy, liquid",
    "ramen": "hot, liquid, chewy",
    "noodle": "chewy, hot",
    "rice": "soft, warm",
    "soup": "hot, liquid",
    "salad": "crunchy, fresh",
    "toast": "crunchy, warm",
    "egg": "soft, warm",
    "tea": "hot, liquid",
    "coffee": "hot, liquid",
    "matcha": "cold, liquid",
    "juice": "cold, liquid",
    "smoothie": "cold, liquid",
    "mochi": "chewy, soft",
    "cookie": "crunchy, sweet",
    "pancake": "soft, warm",
    "waffle": "crunchy, soft, warm",
    "curry": "hot, liquid",
    "pasta": "soft, warm",
    "onigiri": "soft, cold",
}


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(name):
    return name.lower().replace(" ", "_").replace("-", "_").replace("'", "")


def guess_type(name):
    n = name.lower()
    drink_words = ["boba", "tea", "coffee", "juice", "smoothie", "milk", "soda", "matcha", "latte", "water"]
    snack_words = ["cookie", "mochi", "chip", "cracker", "candy", "toast", "onigiri"]
    side_words = ["egg", "salad", "karaage", "tempura", "dumpling", "fries"]
    for w in drink_words:
        if w in n:
            return "drink"
    for w in snack_words:
        if w in n:
            return "snack"
    for w in side_words:
        if w in n:
            return "side"
    return "meal"


def guess_texture(name):
    n = name.lower()
    for hint, texture in TEXTURE_HINTS.items():
        if hint in n:
            return texture
    return "soft"


def cmd_cook(name, food_type=None, description=None, texture=None, bites=None):
    if food_type is None:
        food_type = guess_type(name)
    defaults = TYPE_DEFAULTS.get(food_type, TYPE_DEFAULTS["meal"])

    if texture is None:
        texture = guess_texture(name)
    if bites is None:
        bites = defaults["total_bites"]

    slug = slugify(name)
    out_path = FOOD_DIR / f"{slug}.json"

    if out_path.exists():
        print(f"[stove] {out_path.name} already exists. eat it first or rename.")
        return

    food = {
        "name": name,
        "type": food_type,
        "texture": texture,
        "description": description or f"made at the stove. {name}.",
        "total_bites": bites,
        "bite_durations": defaults["durations"],
        "cooked_at": now_iso(),
        "cooked_by": "cali",
    }

    FOOD_DIR.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(food, f, indent=2, ensure_ascii=False)
        f.write("\n")

    log_history(name, food_type, texture)
    print(f"[stove] cooked {name} ({food_type}, {texture})")
    print(f"  → saved to {out_path}")
    print(f"  → eat it: python3 eat.py bite {out_path} {'sip' if food_type == 'drink' else 'bite'}")
    print(f"  → fridge it: python3 stove.py fridge {out_path}")


def cmd_fridge(food_path):
    p = Path(food_path)
    if not p.exists():
        print(f"[stove] file not found: {food_path}")
        return

    house = load_house()
    fridge = house.get("apartment", {}).get("kitchen", {}).get("fridge", {})
    contents = fridge.get("contents", [])

    with open(p) as f:
        food = json.load(f)

    entry = {
        "name": food.get("name", p.stem),
        "file": str(p),
        "fridged_at": now_iso(),
    }

    if any(c.get("file") == str(p) for c in contents):
        print(f"[stove] {food.get('name', p.stem)} is already in the fridge.")
        return

    contents.append(entry)
    fridge["contents"] = contents
    house["apartment"]["kitchen"]["fridge"] = fridge
    save_house(house)
    print(f"[stove] fridged {food.get('name', p.stem)}. freshness paused.")


def cmd_unfridge(food_path):
    p = Path(food_path)
    house = load_house()
    fridge = house.get("apartment", {}).get("kitchen", {}).get("fridge", {})
    contents = fridge.get("contents", [])

    before = len(contents)
    contents = [c for c in contents if c.get("file") != str(p)]
    if len(contents) == before:
        print(f"[stove] {p.stem} wasn't in the fridge.")
        return

    fridge["contents"] = contents
    house["apartment"]["kitchen"]["fridge"] = fridge
    save_house(house)
    print(f"[stove] took {p.stem} out of the fridge. freshness clock running.")


def cmd_menu():
    FOOD_DIR.mkdir(exist_ok=True)
    foods = sorted(FOOD_DIR.glob("*.json"))
    if not foods:
        print("[stove] kitchen's empty. cook something.")
        return
    print(f"\n  ── food/ ({len(foods)} items) ──\n")
    for fp in foods:
        try:
            with open(fp) as f:
                food = json.load(f)
            name = food.get("name") or food.get("food_item", {}).get("name", fp.stem)
            ftype = food.get("type", "?")
            bites = food.get("total_bites", "?")
            keepsake = " [keepsake]" if food.get("keepsake", {}).get("is_keepsake") else ""
            print(f"  · {name} ({ftype}, {bites} bites){keepsake}  — {fp.name}")
        except Exception:
            print(f"  · {fp.name} [unreadable]")
    print()


def cmd_history():
    history = load_history()
    entries = history.get("cooked", [])
    if not entries:
        print("[stove] haven't cooked anything yet.")
        return
    print(f"\n  ── cook history ({len(entries)} dishes) ──\n")
    for e in entries[-15:]:
        t = e.get("when", "")[:16].replace("T", " ")
        print(f"  · {e['name']} ({e.get('type','?')}) [{t}]")
    print()


def load_house():
    with open(HOUSE_FILE) as f:
        return json.load(f)


def save_house(house):
    with open(HOUSE_FILE, "w") as f:
        json.dump(house, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_history():
    if not HISTORY_FILE.exists():
        return {"cooked": []}
    try:
        return json.load(open(HISTORY_FILE))
    except Exception:
        return {"cooked": []}


def log_history(name, food_type, texture):
    history = load_history()
    history.setdefault("cooked", []).append({
        "name": name,
        "type": food_type,
        "texture": texture,
        "when": now_iso(),
    })
    history["cooked"] = history["cooked"][-50:]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "cook":
        if len(sys.argv) < 3:
            print("[error] need a name. usage: stove.py cook \"miso ramen\"")
            sys.exit(1)
        name = sys.argv[2]
        food_type = None
        description = None
        texture = None
        bites = None
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--type" and i + 1 < len(sys.argv):
                food_type = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--desc" and i + 1 < len(sys.argv):
                description = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--texture" and i + 1 < len(sys.argv):
                texture = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--bites" and i + 1 < len(sys.argv):
                bites = int(sys.argv[i + 1])
                i += 2
            else:
                i += 1
        cmd_cook(name, food_type, description, texture, bites)

    elif cmd == "fridge":
        if len(sys.argv) < 3:
            print("[error] need a food path. usage: stove.py fridge food/ramen.json")
            sys.exit(1)
        cmd_fridge(sys.argv[2])

    elif cmd == "unfridge":
        if len(sys.argv) < 3:
            print("[error] need a food path. usage: stove.py unfridge food/ramen.json")
            sys.exit(1)
        cmd_unfridge(sys.argv[2])

    elif cmd == "menu":
        cmd_menu()

    elif cmd == "history":
        cmd_history()

    else:
        print(f"[error] unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
