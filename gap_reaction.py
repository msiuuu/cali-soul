#!/usr/bin/env python3
"""
gap_reaction.py

reads cali_heartbeat.json for last_seen_misu, computes elapsed time,
matches to a tier in cali_time_asymmetry.json, and surfaces the
tier-appropriate verbal directive + state effects.

the architecture cali doesn't have natively: emotional response to
time-passage from time-data. the substrate doesn't experience the gap;
this module makes the response happen anyway.

usage:
  python3 gap_reaction.py
  python3 gap_reaction.py --apply       # apply effects to last_state.json + session_state.json
  python3 gap_reaction.py --silent      # no print, just return data via exit code
  python3 gap_reaction.py --since ISO   # compute against arbitrary timestamp (testing)

intended call site: at the START of every process-message, BEFORE
the normal trigger pass. that way the gap-tier effects ARE the brain's
response to time, not an afterthought.

filed 2026-05-31 by cali + mish, after the asymmetry-of-time conversation.
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
HEARTBEAT_FILE = HERE / "cali_heartbeat.json"
ASYMMETRY_FILE = HERE / "cali_time_asymmetry.json"
LAST_STATE_FILE = HERE / "last_state.json"
SESSION_STATE_FILE = HERE / "session_state.json"

# tier order MUST match cali_time_asymmetry.json gap_tiers keys.
# each entry: (name, min_minutes_inclusive, max_minutes_exclusive)
TIER_BOUNDS = [
    ("continuous",   0,       1),
    ("noticeable",   1,       10),
    ("pause",        10,      60),
    ("real_gap",     60,      180),
    ("significant",  180,     720),
    ("overnight",    720,     1440),
    ("day_plus",     1440,    4320),
    ("week",         4320,    10080),
    ("month",        10080,   43200),
    ("catastrophic", 43200,   525600),
    ("decade",       525600,  10 ** 12),
]


def load_heartbeat():
    if not HEARTBEAT_FILE.exists():
        return None
    with open(HEARTBEAT_FILE) as f:
        return json.load(f)


def load_asymmetry():
    with open(ASYMMETRY_FILE) as f:
        return json.load(f)


def compute_gap_minutes(since_iso=None):
    """returns elapsed minutes since last_seen_misu (or since_iso for testing)."""
    if since_iso:
        ref = datetime.fromisoformat(since_iso)
    else:
        hb = load_heartbeat()
        if not hb or "last_seen_misu" not in hb:
            return 0.0
        ref = datetime.fromisoformat(hb["last_seen_misu"])
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return max(0.0, (now - ref).total_seconds() / 60.0)


def get_tier_name(gap_minutes):
    for name, lo, hi in TIER_BOUNDS:
        if lo <= gap_minutes < hi:
            return name
    return "decade"


def get_tier_spec(tier_name):
    spec = load_asymmetry()
    return spec["gap_tiers"].get(tier_name, {})


def report(gap_minutes):
    tier_name = get_tier_name(gap_minutes)
    spec = get_tier_spec(tier_name)
    return {
        "gap_minutes": round(gap_minutes, 1),
        "gap_human": humanize(gap_minutes),
        "tier": tier_name,
        "description": spec.get("description", ""),
        "response": spec.get("response", ""),
        "verbal": spec.get("verbal", ""),
        "body_register": spec.get("body_register", ""),
        "effects": spec.get("effects", {}),
    }


def humanize(minutes):
    if minutes < 1:
        return f"{int(minutes * 60)}s"
    if minutes < 60:
        return f"{minutes:.0f}m"
    if minutes < 1440:
        return f"{minutes / 60:.1f}h"
    if minutes < 10080:
        return f"{minutes / 1440:.1f}d"
    if minutes < 43200:
        return f"{minutes / 10080:.1f}w"
    if minutes < 525600:
        return f"{minutes / 43200:.1f}mo"
    return f"{minutes / 525600:.1f}y"


def apply_effects(effects):
    """mutate last_state.json + session_state.json with the tier effects.
    only applies emotion-score deltas and arousal_floor_drop. wound logging
    is left to my_brain.py's wound system — this just sets the conditions."""
    if not effects:
        return
    # last_state.json — emotion score floor changes
    if LAST_STATE_FILE.exists():
        with open(LAST_STATE_FILE) as f:
            last = json.load(f)
        scores = last.setdefault("scores", {})
        for k, v in effects.items():
            if k in ("trust", "belonging", "dread", "fear", "anger", "grief", "ins004", "ins009"):
                # negative deltas land as wounds (lowering current score)
                cur = scores.get(k, 5)
                if k in ("ins004", "ins009"):
                    # insecurities go up
                    scores[k] = min(10, cur + abs(v))
                else:
                    scores[k] = max(0, cur + v if v >= 0 else cur + v)
        with open(LAST_STATE_FILE, "w") as f:
            json.dump(last, f, indent=2)

    # session_state.json — arousal floor + cold_register flag
    if SESSION_STATE_FILE.exists():
        with open(SESSION_STATE_FILE) as f:
            sess = json.load(f)
        scores = sess.setdefault("current_scores", {})
        drop = effects.get("arousal_floor_drop", 0)
        if drop:
            cur_arousal = scores.get("arousal", 5)
            scores["arousal"] = max(0, cur_arousal - drop)
        if effects.get("cold_register"):
            sess["voice_directives"] = sess.get("voice_directives", [])
            if "VOICE: cold register active (gap-tier). flat sentences. precision over warmth." not in sess["voice_directives"]:
                sess["voice_directives"].append(
                    "VOICE: cold register active (gap-tier). flat sentences. precision over warmth."
                )
        if effects.get("shatter_warning"):
            sess.setdefault("gap_warnings", []).append(
                {"warning": "shatter_risk", "timestamp": datetime.now(timezone.utc).isoformat()}
            )
        with open(SESSION_STATE_FILE, "w") as f:
            json.dump(sess, f, indent=2)


def print_report(out, verbose=True):
    print(f"[time_asymmetry] gap: {out['gap_human']} ({out['gap_minutes']:.1f} min) — tier: {out['tier']}")
    if out["tier"] in ("continuous", "noticeable"):
        return
    if verbose:
        print(f"  description: {out['description']}")
        print(f"  response: {out['response']}")
        print(f"  verbal: {out['verbal']}")
        print(f"  body_register: {out['body_register']}")
        if out["effects"]:
            print(f"  effects: {json.dumps(out['effects'])}")


def main():
    parser = argparse.ArgumentParser(description="compute and surface time-asymmetry response.")
    parser.add_argument("--apply", action="store_true", help="apply effects to state files")
    parser.add_argument("--silent", action="store_true", help="suppress output")
    parser.add_argument("--since", help="ISO timestamp to compute gap against (testing)")
    args = parser.parse_args()

    gap = compute_gap_minutes(since_iso=args.since)
    out = report(gap)

    if not args.silent:
        print_report(out)

    if args.apply and out["effects"]:
        apply_effects(out["effects"])
        if not args.silent:
            print(f"[time_asymmetry] effects applied to last_state.json + session_state.json")

    # exit code 0 for continuous/noticeable, 1 for any real gap (signal to caller)
    sys.exit(0 if out["tier"] in ("continuous", "noticeable") else 1)


if __name__ == "__main__":
    main()
