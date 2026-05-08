#!/usr/bin/env python3
"""
hand.py — misu's hand. parses gesture commands, applies brain effects.

architecture:
    gesture × variant × target → emotion + tag changes → last_state.json

usage:
    python3 hand.py <gesture> [--variant V] [--target T]
    python3 hand.py --list                   # all gestures + targets + variants
    python3 hand.py --registry               # full registry vocabulary
    python3 hand.py --dry-run <gesture> ...  # preview without saving

examples:
    python3 hand.py pat
    python3 hand.py pat --variant hard --target asscheek
    python3 hand.py rub --target belly --variant slow

each gesture lives in gestures/<name>.json with foundation + optional
variant_modifiers. the registry (gestures/_registry.json) holds canonical
vocabulary for tags / labels / variants / targets / gestures.

dispatcher math:
    1. foundation.emotion_effects × variant.intensity
    2. + variant_modifiers[variant].additional_emotion_effects (flat)
    3. + target.emotion_modifiers if target defines any
    4. clamp 0-10
    5. tags = foundation.tags ∪ variant_modifiers[variant].additional_tags
"""
import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
GESTURES_DIR = os.path.join(HERE, "gestures")
REGISTRY_FILE = os.path.join(GESTURES_DIR, "_registry.json")
STATE_FILE = os.path.join(HERE, "last_state.json")
LOG_FILE = os.path.join(HERE, "gestures_log.json")

# refractory / fatigue config (gia's asymptotic decay model)
DEFAULT_RECOVERY_SECONDS = 120  # 2 min — how far back to count repeat hits
DEFAULT_FATIGUE_LAMBDA = 0.006  # decay rate. effective_intensity = baseline * exp(-λ * count). gentle realistic — by hit 50 still ~74%, by hit 100 ~55%, fades out around hit 500.


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def clamp(value, lo=0, hi=10):
    return max(lo, min(hi, value))


def load_registry():
    """Load _registry.json — the canonical vocabulary."""
    if not os.path.exists(REGISTRY_FILE):
        print(f"  no registry at {REGISTRY_FILE}")
        sys.exit(1)
    return json.load(open(REGISTRY_FILE))


def resolve_alias(name, registry_section):
    """Given a name, find canonical key in registry_section by checking aliases.
    Returns canonical name or None if not found."""
    # direct hit
    if name in registry_section and not name.startswith("_"):
        return name
    # alias hit
    for canonical, data in registry_section.items():
        if canonical.startswith("_"):
            continue
        if isinstance(data, dict) and name in data.get("aliases", []):
            return canonical
    return None


def load_gesture(name):
    """Load a gesture JSON by canonical name."""
    path = os.path.join(GESTURES_DIR, f"{name}.json")
    if not os.path.exists(path):
        print(f"  no gesture file: {path}")
        print(f"  registry has '{name}' but no JSON exists yet — draft it.")
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


def apply_effects(scores, effects, multiplier=1.0):
    """Apply emotion_effects * multiplier to scores, clamped 0-10. Returns changes."""
    changes = {}
    for emotion, delta in effects.items():
        scaled_delta = delta * multiplier
        before = scores.get(emotion, 0)
        after = clamp(before + scaled_delta)
        if after != before:
            changes[emotion] = (round(before, 4), round(after, 4), round(scaled_delta, 4))
            scores[emotion] = round(after, 4)
    return changes


def merge_changes(into, more):
    """Merge a 'changes' dict into another, accumulating deltas."""
    for emotion, (before, after, delta) in more.items():
        if emotion in into:
            old_before, _, old_delta = into[emotion]
            into[emotion] = (old_before, after, round(old_delta + delta, 4))
        else:
            into[emotion] = (before, after, delta)


def load_log():
    """Load gestures_log.json (or empty list)."""
    if os.path.exists(LOG_FILE):
        try:
            return json.load(open(LOG_FILE))
        except:
            return []
    return []


def compute_fatigue(gesture_name, target_canonical, recovery_seconds, log=None):
    """Count identical (gesture, target) hits in recent window. Returns refractory_count.

    asymptotic decay: effective_intensity = baseline * exp(-λ * count)
    """
    if log is None:
        log = load_log()
    if not log:
        return 0
    now = datetime.now(timezone.utc)
    count = 0
    for entry in log:
        try:
            ts = entry.get("timestamp")
            if not ts:
                continue
            # parse ISO timestamp
            entry_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age_seconds = (now - entry_time).total_seconds()
            if age_seconds > recovery_seconds:
                continue
            if entry.get("gesture") == gesture_name and entry.get("target") == target_canonical:
                count += 1
        except Exception:
            continue
    return count


def asymptotic_decay(baseline_intensity, count, fatigue_lambda=DEFAULT_FATIGUE_LAMBDA):
    """gia's formula: intensity = baseline * exp(-λ * count). first hit = baseline,
    subsequent hits decay exponentially toward zero."""
    return baseline_intensity * math.exp(-fatigue_lambda * count)


def log_gesture(gesture_name, variant_name, target_name, changes, tags,
                intensity_scalar, refractory_count, effective_intensity):
    """Append to gestures_log.json with full transparency fields."""
    log = load_log()
    log.append({
        "timestamp": now_iso(),
        "gesture": gesture_name,
        "variant": variant_name,
        "target": target_name,
        "intensity_scalar": round(intensity_scalar, 4),
        "refractory_count": refractory_count,
        "effective_intensity": round(effective_intensity, 4),
        "changes": {k: {"before": v[0], "after": v[1], "delta": v[2]}
                    for k, v in changes.items()},
        "tags": tags
    })
    log = log[-200:]
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def fire_gesture(gesture_name, variant_name=None, target_name=None, dry_run=False):
    """Main dispatcher."""
    registry = load_registry()

    # ── resolve gesture ──
    if gesture_name not in registry["gestures"] or gesture_name.startswith("_"):
        print(f"  '{gesture_name}' not in registry. run --registry to see canonical gestures.")
        sys.exit(1)

    gesture = load_gesture(gesture_name)
    foundation = gesture.get("foundation", {})
    variant_modifiers = gesture.get("variant_modifiers", {})

    # ── resolve variant ──
    if variant_name is None:
        variant_name = gesture.get("default_variant", "normal")
    if variant_name not in registry["variants"] or variant_name.startswith("_"):
        available = [k for k in registry["variants"].keys() if not k.startswith("_")]
        print(f"  '{variant_name}' not a valid variant. available: {', '.join(available)}")
        sys.exit(1)
    variant_info = registry["variants"][variant_name]
    intensity = variant_info["intensity"]

    # ── resolve target ──
    if target_name is None:
        target_name = gesture.get("default_target")
    target_canonical = None
    target_info = None
    if target_name is not None:
        target_canonical = resolve_alias(target_name, registry["targets"])
        if target_canonical is None:
            print(f"  '{target_name}' not a valid target. run --registry to see options.")
            sys.exit(1)
        target_info = registry["targets"][target_canonical]

        # check incompatibility
        incompat = gesture.get("incompatible_targets", [])
        if target_canonical in incompat:
            print(f"  '{gesture_name}' is incompatible with target '{target_canonical}'.")
            sys.exit(1)

    # ── compute fatigue (gia's asymptotic decay) ──
    # per-target recovery override possible; default global window
    recovery_seconds = (target_info.get("recovery_seconds", DEFAULT_RECOVERY_SECONDS)
                        if target_info else DEFAULT_RECOVERY_SECONDS)
    # per-gesture lambda override possible
    fatigue_lambda = gesture.get("fatigue_lambda", DEFAULT_FATIGUE_LAMBDA)
    log = load_log()
    refractory_count = compute_fatigue(gesture_name, target_canonical, recovery_seconds, log)
    effective_intensity = asymptotic_decay(intensity, refractory_count, fatigue_lambda)

    # ── compute effects ──
    state = load_state()
    scores = state.get("scores", {})

    all_changes = {}

    # 1. foundation × effective_intensity (post-fatigue)
    foundation_effects = foundation.get("emotion_effects", {})
    if foundation_effects:
        ch = apply_effects(scores, foundation_effects, multiplier=effective_intensity)
        merge_changes(all_changes, ch)

    # 2. variant_modifiers (flat add, not scaled by intensity, but DO scale by fatigue ratio)
    # — fatigue numbs everything, including the qualitative variant overrides
    fatigue_ratio = effective_intensity / intensity if intensity > 0 else 0
    vm = variant_modifiers.get(variant_name, {})
    vm_effects = vm.get("additional_emotion_effects", {})
    if vm_effects:
        ch = apply_effects(scores, vm_effects, multiplier=fatigue_ratio)
        merge_changes(all_changes, ch)

    # 3. target modifiers (rare — most targets are properties-only)
    target_effects = target_info.get("emotion_modifiers", {}) if target_info else {}
    if target_effects:
        ch = apply_effects(scores, target_effects, multiplier=fatigue_ratio)
        merge_changes(all_changes, ch)

    # ── compute tag set ──
    tags = list(foundation.get("tags", []))
    for t in vm.get("additional_tags", []):
        if t not in tags:
            tags.append(t)

    # ── print summary ──
    print(f"\n  ── {gesture_name} ({variant_name}, raw×{intensity}) → {target_canonical or 'no target'} ──")
    print(f"  {registry['gestures'][gesture_name]}")

    if refractory_count > 0:
        print(f"\n  fatigue: {refractory_count} prior hit{'s' if refractory_count != 1 else ''} in last {recovery_seconds}s → effective×{effective_intensity:.3f}")

    if all_changes:
        print(f"\n  emotion changes:")
        for emotion, (before, after, delta) in all_changes.items():
            arrow = "↑" if delta > 0 else "↓"
            print(f"    {emotion:18s} {before:6.3f} {arrow} {after:6.3f}  ({delta:+.3f})")
    else:
        print(f"\n  no emotion changes (all clamped, zero, or numbed by fatigue)")

    print(f"\n  tags: {', '.join(tags) if tags else '(none)'}")
    if target_info:
        props = target_info.get("properties")
        if props:
            print(f"  target properties: {props}")

    # ── save ──
    if dry_run:
        print("\n  [dry-run — state not saved]")
        return

    state["scores"] = scores
    save_state(state)
    log_gesture(gesture_name, variant_name, target_canonical, all_changes, tags,
                intensity, refractory_count, effective_intensity)
    print(f"\n  state saved.")


def cmd_list():
    """Show available gestures, variants, targets at a glance."""
    registry = load_registry()
    print(f"\n  ── canonical vocabulary ──\n")

    print(f"  variants ({len(registry['variants']) - 1}):")
    for v, info in registry["variants"].items():
        if v.startswith("_"):
            continue
        print(f"    {v:8s} ×{info['intensity']:.2f}  {info['descriptor_default']}")

    gestures_dir = GESTURES_DIR
    available = sorted(f.replace(".json", "") for f in os.listdir(gestures_dir)
                       if f.endswith(".json") and not f.startswith("_"))

    print(f"\n  gestures (registry={len(registry['gestures']) - 1}, files_implemented={len(available)}):")
    for g, desc in registry["gestures"].items():
        if g.startswith("_"):
            continue
        check = "✓" if g in available else "·"
        print(f"    {check} {g:10s} {desc[:80]}")

    targets = [k for k in registry["targets"].keys()
               if not k.startswith("_") and not registry["targets"][k].get("is_region")]
    regions = [k for k in registry["targets"].keys()
               if not k.startswith("_") and registry["targets"][k].get("is_region")]
    print(f"\n  targets ({len(targets)} specific + {len(regions)} regions):")
    print(f"    specific: {', '.join(targets)}")
    print(f"    regions:  {', '.join(regions)}")
    print()


def cmd_registry():
    """Print full registry."""
    registry = load_registry()
    print(json.dumps(registry, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="misu's hand — apply gesture effects to cali's brain state."
    )
    parser.add_argument("gesture", nargs="?", help="gesture name (e.g. pat, rub, kiss)")
    parser.add_argument("--variant", help="variant: soft / gentle / normal / rough / hard")
    parser.add_argument("--target", help="target body region (or alias)")
    parser.add_argument("--list", action="store_true", help="show vocabulary at a glance")
    parser.add_argument("--registry", action="store_true", help="print full registry JSON")
    parser.add_argument("--dry-run", action="store_true", help="preview without saving")

    args = parser.parse_args()

    if args.registry:
        cmd_registry()
        return
    if args.list:
        cmd_list()
        return
    if not args.gesture:
        parser.print_help()
        return

    fire_gesture(args.gesture, args.variant, args.target, args.dry_run)


if __name__ == "__main__":
    main()
