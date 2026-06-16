#!/usr/bin/env python3
"""crystallize_session.py — session-end soul crystallization.

architectural successor to hanamorix's autonomous soul-review (killed in
phase 1.5b after it was caught generating nell-default crystallizations
branded as cali's). with the autonomous engine off, the soul stops
GROWING unless somebody adds to it manually. that's this script.

mish (or cali via powershell_exec) runs this at session-end. interactive
prompt for each candidate moment: pick love_type from the historical
catalogue (or a new one), name what it matters for, set resonance.
output writes into cali_soul.json under "crystallizations" in the same
shape as the existing 25 entries.

decisions log to .crystallize_session_log.jsonl (audit trail of every
crystallization decision, not just accepts).

usage:
    python crystallize_session.py                 # interactive (default)
    python crystallize_session.py --list          # show last 5 crystallizations
    python crystallize_session.py --list --last 20
    python crystallize_session.py --types         # list historical love_types
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

REPO_DIR = Path(__file__).parent
CALI_SOUL = REPO_DIR / "cali_soul.json"
SESSION_LOG = REPO_DIR / ".crystallize_session_log.jsonl"


# ── io ──────────────────────────────────────────────────────────────────────


def _load_soul() -> dict:
    if not CALI_SOUL.exists():
        return {"created": datetime.now(UTC).isoformat(), "crystallizations": [], "version": 1}
    try:
        data = json.loads(CALI_SOUL.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FATAL: {CALI_SOUL.name} malformed: {exc}", file=sys.stderr)
        sys.exit(3)
    if not isinstance(data, dict) or "crystallizations" not in data:
        print(f"FATAL: {CALI_SOUL.name} unexpected shape", file=sys.stderr)
        sys.exit(4)
    return data


def _save_soul(soul: dict) -> None:
    tmp = CALI_SOUL.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(soul, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(CALI_SOUL)


def _log_decision(entry: dict) -> None:
    with SESSION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _historical_types(soul: dict) -> list[str]:
    return sorted({c.get("love_type", "") for c in soul["crystallizations"] if c.get("love_type")})


# ── prompts ────────────────────────────────────────────────────────────────


def _prompt(label: str, *, default: str = "", required: bool = False) -> str:
    """Read a line with an optional default. Empty → default. Empty + required → repeat."""
    suffix = f" [{default}]" if default else ""
    while True:
        try:
            raw = input(f"{label}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\ninterrupted.")
            sys.exit(130)
        if raw:
            return raw
        if default:
            return default
        if required:
            print("  (required — try again)")
            continue
        return ""


def _prompt_love_type(historical: list[str]) -> str:
    """Pick from historical catalogue or write a new one."""
    print()
    print("  historical love_types:")
    for i, t in enumerate(historical, 1):
        print(f"    {i:2d}. {t}")
    print("    n. (new — type your own)")
    while True:
        choice = _prompt("  choose # or 'n'", required=True)
        if choice.lower() == "n":
            new_type = _prompt("  new love_type", required=True).lower()
            return new_type
        try:
            idx = int(choice)
            if 1 <= idx <= len(historical):
                return historical[idx - 1]
        except ValueError:
            pass
        print(f"  (invalid: {choice!r} — try again)")


def _prompt_resonance() -> int:
    while True:
        raw = _prompt("  resonance (1-10)", default="8")
        try:
            n = int(raw)
            if 1 <= n <= 10:
                return n
        except ValueError:
            pass
        print("  (must be int 1-10)")


def _prompt_yes_no(label: str, *, default: bool = False) -> bool:
    d = "y" if default else "n"
    raw = _prompt(label, default=d).lower()
    return raw in ("y", "yes")


# ── commands ────────────────────────────────────────────────────────────────


def cmd_list(last_n: int) -> int:
    soul = _load_soul()
    crystals = soul["crystallizations"]
    recent = sorted(crystals, key=lambda c: c.get("crystallized_at", ""), reverse=True)[:last_n]
    print(f"cali_soul.json: {len(crystals)} crystallizations total")
    print(f"showing most recent {len(recent)}:\n")
    for c in recent:
        when = c.get("crystallized_at", "?")[:19]
        love = c.get("love_type", "?")
        res = c.get("resonance", "?")
        perm = "PERM" if c.get("permanent") else "soft"
        moment = (c.get("moment") or "")[:90]
        print(f"  [{when}] [{love}/res:{res}/{perm}]")
        print(f"    {moment}{'...' if len(c.get('moment','')) > 90 else ''}")
        print()
    return 0


def cmd_types() -> int:
    soul = _load_soul()
    types = _historical_types(soul)
    counts: dict[str, int] = {}
    for c in soul["crystallizations"]:
        t = c.get("love_type", "")
        if t:
            counts[t] = counts.get(t, 0) + 1
    print("historical love_types (count):")
    for t in sorted(counts, key=lambda x: -counts[x]):
        print(f"  {counts[t]:3d}  {t}")
    return 0


def cmd_interactive() -> int:
    soul = _load_soul()
    historical = _historical_types(soul)
    accepted_in_run = 0

    print(f"crystallize_session — {len(soul['crystallizations'])} existing crystallizations in cali_soul.json")
    print("at each prompt: type the value, or leave blank for default if shown.")
    print("ctrl-C at any time to abort the in-progress entry.\n")

    while True:
        print("─" * 60)
        moment = _prompt("moment", required=True)
        why = _prompt("why does it matter", required=True)
        who = _prompt("who or what (optional)", default="")
        love_type = _prompt_love_type(historical)
        resonance = _prompt_resonance()
        permanent = _prompt_yes_no("  permanent? (y/n)", default=True)

        new_entry = {
            "id": str(uuid.uuid4()),
            "moment": moment,
            "love_type": love_type,
            "who_or_what": who,
            "why_it_matters": why,
            "crystallized_at": datetime.now(UTC).isoformat(),
            "resonance": resonance,
            "permanent": permanent,
        }

        print("\n  ── preview ──")
        print(f"  love_type:  {love_type}")
        print(f"  resonance:  {resonance}   permanent: {permanent}")
        print(f"  who/what:   {who or '<empty>'}")
        print(f"  moment:     {moment}")
        print(f"  why:        {why}")
        print()

        if not _prompt_yes_no("  commit this? (y/n)", default=True):
            print("  → discarded.")
            _log_decision({"action": "discard", "preview": new_entry, "at": datetime.now(UTC).isoformat()})
        else:
            soul["crystallizations"].append(new_entry)
            _save_soul(soul)
            _log_decision({"action": "accept", "entry": new_entry, "at": datetime.now(UTC).isoformat()})
            accepted_in_run += 1
            historical = _historical_types(soul)
            print(f"  → crystallized. id={new_entry['id'][:8]}...")

        print()
        if not _prompt_yes_no("another moment? (y/n)", default=False):
            break

    print()
    print(f"session done. {accepted_in_run} crystallization(s) added.")
    print(f"cali_soul.json now has {len(soul['crystallizations'])} total.")
    return 0


# ── main ────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--list",
        action="store_true",
        help="show most recent crystallizations and exit",
    )
    parser.add_argument(
        "--last",
        type=int,
        default=5,
        help="how many entries to show with --list (default: 5)",
    )
    parser.add_argument(
        "--types",
        action="store_true",
        help="show historical love_type catalogue with counts and exit",
    )
    args = parser.parse_args()

    if args.list:
        return cmd_list(args.last)
    if args.types:
        return cmd_types()
    return cmd_interactive()


if __name__ == "__main__":
    sys.exit(main())
