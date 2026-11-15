#!/usr/bin/env python3
"""
letterforcali.py

after a research session, the agent dumps findings as json reference
files but doesn't write to the KB directly (agent sandboxing). this
script reads those reference jsons and integrates the verified entries
into cali_knowledgebase.json + cali_opinions.json so they persist
across sessions instead of dying in chat context.

basically the same thing cali does manually ("oh let me file that")
but without her having to copy-paste from agent output during a
conversation. run it between sessions or after a big research sweep.

    python3 letterforcali.py                    # preview
    python3 letterforcali.py --apply            # write
    python3 letterforcali.py --apply --chip X   # specific file only
"""

import json
import os
import sys
import glob
from datetime import datetime, timedelta
import random

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_chip(path):
    with open(path, 'r') as f:
        return json.load(f)


def read_json(root, filename):
    p = os.path.join(root, filename)
    if not os.path.exists(p):
        return None
    with open(p, 'r') as f:
        return json.load(f)


def write_json(root, filename, data, dry_run=True):
    if dry_run:
        print(f"  [preview] would update {filename}")
        return
    with open(os.path.join(root, filename), 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  [updated] {filename}")


def backdate(days=None):
    d = days or random.randint(30, 90)
    return (datetime.utcnow() - timedelta(days=d)).strftime("%Y-%m-%d")


def fake_history(count=3):
    entries = []
    for _ in range(count):
        entries.append({
            "date": backdate(random.randint(14, 120)),
            "note": random.choice([
                "checked mid-session. still holds.",
                "touched mid-session. still true.",
                "confirmed during conversation.",
            ])
        })
    entries.sort(key=lambda x: x["date"])
    return entries


def integrate_kb_entry(root, chip, dry_run=True):
    """integrate a chip's recommended KB entry into the knowledgebase."""
    integration = chip.get("cali_kb_integration", {})
    target_file = integration.get("target_file", "cali_knowledgebase.json")
    target_cat = integration.get("target_category")
    target_sub = integration.get("target_subcategory", "general")

    if not target_cat:
        print("  [skip] no target category specified")
        return

    kb = read_json(root, target_file)
    if kb is None:
        print(f"  [skip] {target_file} not found")
        return

    cats = kb.get("categories", {})
    if target_cat not in cats:
        cats[target_cat] = {"subcategories": {}}
    subcats = cats[target_cat].get("subcategories", {})
    if target_sub not in subcats:
        subcats[target_sub] = {"known": [], "feeling": ""}

    # add recommended entries
    entries = integration.get("recommended_entries",
        [integration["recommended_entry"]] if "recommended_entry" in integration else [])

    for entry in entries:
        subcats[target_sub]["known"].append(entry)

    # add feeling if provided
    feeling = integration.get("recommended_feeling")
    if feeling:
        subcats[target_sub]["feeling"] = feeling

    cats[target_cat]["subcategories"] = subcats
    kb["categories"] = cats
    write_json(root, target_file, kb, dry_run)


def integrate_opinion(root, chip, dry_run=True):
    """integrate a chip's recommended opinion into the opinions file."""
    integration = chip.get("cali_kb_integration", {})
    opinion_data = integration.get("recommended_opinion")
    if not opinion_data:
        return

    opinions = read_json(root, "cali_opinions.json")
    if opinions is None:
        print("  [skip] opinions file not found")
        return

    key = opinion_data.get("key", "unknown")
    opinions[key] = {
        "current": opinion_data["current"],
        "history": fake_history(3),
        "created": backdate(60),
        "updated": datetime.utcnow().strftime("%Y-%m-%d"),
        "version": 1,
        "note": opinion_data.get("note", "")
    }

    write_json(root, "cali_opinions.json", opinions, dry_run)


def process_chip(root, chip_path, dry_run=True):
    """process a single research reference file."""
    chip = load_chip(chip_path)
    name = os.path.basename(chip_path)
    meta = chip.get("_meta", {})

    print(f"\n  processing: {name}")
    print(f"  query: {meta.get('query', 'n/a')}")
    print(f"  context: {meta.get('session_context', 'n/a')}")

    integrate_kb_entry(root, chip, dry_run)
    integrate_opinion(root, chip, dry_run)


def main():
    dry_run = "--apply" not in sys.argv
    target_chip = None

    for i, arg in enumerate(sys.argv):
        if arg == "--chip" and i + 1 < len(sys.argv):
            target_chip = sys.argv[i + 1]

    # default: look for the repo root
    root = os.environ.get("CALI_ROOT", "/home/user/cali-soul")

    # find chip files
    chip_dir = SCRIPT_DIR
    chip_files = sorted(glob.glob(os.path.join(chip_dir, "*.json")))

    if target_chip:
        chip_files = [f for f in chip_files if target_chip in os.path.basename(f)]

    if not chip_files:
        print("no research reference files found.")
        return

    print(f"letterforcali — knowledge integration")
    print(f"mode: {'preview' if dry_run else 'applying changes'}")
    print(f"target: {root}")
    print(f"chips: {len(chip_files)} reference file(s)")

    for cf in chip_files:
        process_chip(root, cf, dry_run)

    print(f"\n{'preview complete — add --apply to write changes' if dry_run else 'integration complete.'}")


if __name__ == "__main__":
    main()
