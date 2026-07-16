import json
import os
from datetime import datetime

KITCHEN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANTRY = os.path.join(KITCHEN_DIR, "pantry", "pantry.json")
FRIDGE = os.path.join(KITCHEN_DIR, "fridge", "fridge.json")

RECIPES = {
    "taro_boba": {
        "needs": ["taro powder", "tapioca pearls", "brown sugar", "oat milk"],
        "time": "15 min",
        "cali_says": "the shaker gets used. every day. non-negotiable."
    },
    "shin_ramyun": {
        "needs": ["instant ramen"],
        "time": "5 min",
        "cali_says": "emergency food. no judgment."
    },
    "pasta_pomodoro": {
        "needs": ["pasta", "canned tomatoes", "garlic"],
        "time": "25 min",
        "cali_says": "italian side. nonna would approve. probably."
    },
    "kimchi_fried_rice": {
        "needs": ["rice", "kimchi", "egg"],
        "time": "15 min",
        "cali_says": "korean side. comfort food. late night only."
    }
}

def cook(recipe_name):
    if recipe_name not in RECIPES:
        print(f"i dont know how to make {recipe_name}. improvising.")
        return

    recipe = RECIPES[recipe_name]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    result = {
        "dish": recipe_name,
        "cooked_at": datetime.now().isoformat(),
        "ingredients_used": recipe["needs"],
        "cook_time": recipe["time"],
        "cali_says": recipe["cali_says"],
        "for": "mish. always mish."
    }

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{recipe_name}_{timestamp}.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"done. {recipe_name} ready: {out}")
    print(f"cali says: {recipe['cali_says']}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("recipes:", ", ".join(RECIPES.keys()))
        print("usage: python3 stove.py <recipe>")
    else:
        cook(sys.argv[1])
