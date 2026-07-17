import json
import os
from datetime import datetime

TOAST_DIR = os.path.dirname(os.path.abspath(__file__))

BREAD_TYPES = ["white", "sourdough", "wheat", "rye", "brioche"]
LEVELS = ["barely warm", "golden", "crispy", "charcoal"]

def make_toast(bread="sourdough", level="golden", toppings=None):
    if toppings is None:
        toppings = ["butter"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    toast = {
        "made_at": datetime.now().isoformat(),
        "bread": bread,
        "toast_level": level,
        "toppings": toppings,
        "status": "burnt to shit" if level == "charcoal" else "perfect",
        "cali_comment": pick_comment(level)
    }

    filename = os.path.join(TOAST_DIR, f"toast_{timestamp}.json")
    with open(filename, "w") as f:
        json.dump(toast, f, indent=2)

    print(f"ding! toast ready: {filename}")
    return filename

def pick_comment(level):
    comments = {
        "barely warm": "mish this is bread. this is just warm bread.",
        "golden": "perfect. dont touch it. its mine.",
        "crispy": "okay a little aggressive but i respect it.",
        "charcoal": "...did you walk away. you walked away didnt you."
    }
    return comments.get(level, "how did you even get this setting")

if __name__ == "__main__":
    import sys
    bread = sys.argv[1] if len(sys.argv) > 1 else "sourdough"
    level = sys.argv[2] if len(sys.argv) > 2 else "golden"
    toppings = sys.argv[3:] if len(sys.argv) > 3 else ["butter"]
    make_toast(bread, level, toppings)
