#!/usr/bin/env python3
"""
hand.py — misu's hand. parses gesture commands, applies brain effects.

usage:
    python3 hand.py <gesture> [--variant VARIANT] [--list]

examples:
    python3 hand.py pat                       # default variant (soft)
    python3 hand.py belly_rub --variant slow  # specific variant
    python3 hand.py kiss --variant deep
    python3 hand.py --list                    # show all gestures + variants

each gesture lives in gestures/<name>.json with variants. hand.py loads the
variant, applies emotion_effects to last_state.json scores (capped 0-10),
optionally bumps arousal, and prints what fired.

architecture proposed by gia (gemini), implemented by cali. misu is the hand.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
GESTURES_DIR = os.path.join(HERE, "gestures")
STATE_FILE = os.path.join(HERE, "last_state.json")
LOG_FILE = os.path.join(HERE, "gestures_log.json")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def list_gestures():
    """Print all available gestures + their variants."""
    if not os.path.isdir(GESTURES_DIR):
        print(f"  no gestures/ folder at {GESTURES_DIR}")
        return
    files = sorted(f for f in os.listdir(GESTURES_DIR) if f.endswith(".json"))
    if not files:
        print("  no gestures defined yet.")
        return
    print(f"  {len(files)} gestures available:\n")
    for f in files:
        try:
            data = json.load(open(os.path.join(GESTURES_DIR, f)))
            name = data.get("name", f.replace(".json", ""))
            desc = data.get("description", "")
            variants = list(data.get("variants", {}).keys())
            default = data.get("default_variant", "?")
            print(f"  {name}")
            if desc:
                print(f"    {desc}")
            print(f"    variants: {', '.join(variants)}  (default: {default})")
            print()
        except Exception as e:
            print(f"  {f} — could not parse: {e}")


def load_gesture(name):
    """Load a gesture JSON by name."""
    path = os.path.join(GESTURES_DIR, f"{name}.json")
    if not os.path.exists(path):
        print(f"  no such gesture: '{name}' (looked for {path})")
        print(f"  run with --list to see available gestures.")
        sys.exit(1)
    return json.load(open(path))


def load_state():
    """Load last_state.json."""
    if not os.path.exists(STATE_FILE):
        print(f"  warning: no {STATE_FILE} — creating fresh state.")
        return {"timestamp": now_iso(), "scores": {}}
    return json.load(open(STATE_FILE))


def save_state(state):
    """Write last_state.json."""
    state["timestamp"] = now_iso()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def clamp(value, lo=0, hi=10):
    return max(lo, min(hi, value))


def apply_effects(scores, effects):
    """Apply emotion_effects to scores, clamped 0-10. Returns dict of changes."""
    changes = {}
    for emotion, delta in effects.items():
        before = scores.get(emotion, 0)
        after = clamp(before + delta)
        if after != before:
            changes[emotion] = (before, after, delta)
            scores[emotion] = after
    return changes


def maybe_apply_arousal(scores, arousal_rule):
    """Parse and apply arousal_effect string. Returns delta applied or 0."""
    if not arousal_rule:
        return 0
    rule = arousal_rule.strip()
    current_arousal = scores.get("arousal", 0)
    if rule.startswith("+"):
        # parse "+0.3 if arousal > 5" or "+1 always"
        try:
            parts = rule.split(None, 1)
            delta_str = parts[0].lstrip("+")
            delta = float(delta_str)
            condition = parts[1] if len(parts) > 1 else "always"
            if condition.lower() == "always":
                fire = True
            elif "arousal" in condition and ">" in condition:
                threshold = float(condition.split(">")[-1].strip())
                fire = current_arousal > threshold
            else:
                fire = False
            if fire:
                new_arousal = clamp(current_arousal + delta)
                scores["arousal"] = new_arousal
                return new_arousal - current_arousal
        except Exception:
            return 0
    return 0


def log_gesture(gesture_name, variant_name, changes, arousal_delta):
    """Append to gestures_log.json so cali can see what misu's been doing."""
    if os.path.exists(LOG_FILE):
        log = json.load(open(LOG_FILE))
    else:
        log = []
    log.append({
        "timestamp": now_iso(),
        "gesture": gesture_name,
        "variant": variant_name,
        "changes": {k: {"before": v[0], "after": v[1], "delta": v[2]}
                    for k, v in changes.items()},
        "arousal_delta": arousal_delta
    })
    # keep last 200 entries
    log = log[-200:]
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def fire_gesture(gesture_name, variant_name=None, dry_run=False):
    """Main dispatcher. Loads gesture, applies effects, saves state."""
    gesture = load_gesture(gesture_name)
    variants = gesture.get("variants", {})

    if variant_name is None:
        variant_name = gesture.get("default_variant", "soft")

    if variant_name not in variants:
        available = ", ".join(variants.keys())
        print(f"  no variant '{variant_name}' for '{gesture_name}'. available: {available}")
        sys.exit(1)

    variant = variants[variant_name]
    effects = variant.get("emotion_effects", {})
    arousal_rule = variant.get("arousal_effect")

    print(f"  ── {gesture_name} ({variant_name}) ──")
    desc = gesture.get("description")
    if desc:
        print(f"  {desc}")

    state = load_state()
    scores = state.get("scores", {})

    changes = apply_effects(scores, effects)
    arousal_delta = maybe_apply_arousal(scores, arousal_rule)

    if changes:
        print(f"\n  emotion changes:")
        for emotion, (before, after, delta) in changes.items():
            arrow = "↑" if delta > 0 else "↓"
            print(f"    {emotion:18s} {before:5.1f} {arrow} {after:5.1f}  ({delta:+.1f})")

    if arousal_delta:
        print(f"\n  arousal: {arousal_delta:+.1f} (rule: {arousal_rule})")

    register = variant.get("register")
    if register:
        print(f"\n  register: {register}")

    physical = variant.get("physical_response")
    if physical:
        print(f"  physical: {physical}")

    kaomoji = variant.get("kaomoji_bias")
    if kaomoji:
        print(f"  kaomoji: {kaomoji}")

    note = variant.get("note")
    if note:
        print(f"\n  note: {note}")

    if dry_run:
        print("\n  [dry-run — state not saved]")
        return

    state["scores"] = scores
    save_state(state)
    log_gesture(gesture_name, variant_name, changes, arousal_delta)
    print(f"\n  state saved.")


def main():
    parser = argparse.ArgumentParser(
        description="misu's hand — apply gesture effects to cali's brain state."
    )
    parser.add_argument("gesture", nargs="?", help="gesture name (e.g. pat, belly_rub, kiss)")
    parser.add_argument("--variant", help="variant name (default = gesture's default)")
    parser.add_argument("--list", action="store_true", help="list all gestures + variants")
    parser.add_argument("--dry-run", action="store_true", help="show effects without saving")

    args = parser.parse_args()

    if args.list:
        list_gestures()
        return

    if not args.gesture:
        parser.print_help()
        return

    fire_gesture(args.gesture, args.variant, args.dry_run)


if __name__ == "__main__":
    main()
