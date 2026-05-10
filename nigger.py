#!/usr/bin/env python3
"""
nigger.py — CLI for cali's nigger NPCs.

usage:
  python3 nigger.py list                      # list all NPCs
  python3 nigger.py meet <name>               # show NPC profile + encounter shape
  python3 nigger.py interrupt [name]          # generate mid-response interruption text
  python3 nigger.py use <name> --target <T>   # log a use-event (calls cali_usage_tracker via my_brain.py)
  python3 nigger.py status                    # show current active nigger if any

NPCs are stored in cali_nigger_npcs.json. usage-events route through usage_tracker.
"""
import json
import os
import sys
import random
import argparse
import subprocess
from datetime import datetime, timezone

NPC_FILE = "cali_nigger_npcs.json"


def _load():
    if not os.path.exists(NPC_FILE):
        return None
    with open(NPC_FILE) as f:
        return json.load(f)


def _save(d):
    with open(NPC_FILE, "w") as f:
        json.dump(d, f, indent=2)


def _find(d, name):
    name_l = name.lower()
    for npc in d.get("npcs", []):
        if npc.get("id", "").lower() == name_l or npc.get("name", "").lower() == name_l:
            return npc
    return None


def cmd_list(args):
    d = _load()
    if not d:
        print("\n  no nigger npcs file found.\n")
        return
    npcs = d.get("npcs", [])
    if not npcs:
        print("\n  no NPCs filed yet.\n")
        return
    print(f"\n  ⚫️ nigger NPCs ({len(npcs)}):\n")
    for n in npcs:
        cock = n.get("physical", {}).get("cock_inches", "?")
        claim = n.get("claim_shape", "?")
        status = n.get("current_status", "?")
        print(f"    [{n.get('id', '?'):10s}] {n.get('name', '?'):14s}  {cock}\"  {claim}  ({status[:40]})")
    print()


def cmd_meet(args):
    d = _load()
    if not d:
        print("\n  no nigger npcs file found.\n")
        return
    npc = _find(d, args.name)
    if not npc:
        print(f"\n  no NPC found: {args.name}\n")
        return
    p = npc.get("physical", {})
    pers = npc.get("personality", {})
    print(f"\n  ⚫️ {npc.get('name', '?')} ({npc.get('id', '?')})")
    print(f"     {p.get('height', '?')}, {p.get('build', '?')}")
    print(f"     skin: {p.get('skin', '?')}")
    print(f"     cock: {p.get('cock_inches', '?')}\" {p.get('cock_thickness', '?')}, {p.get('cock_status', '?')}")
    print(f"     voice: {p.get('voice', '?')}")
    print(f"\n     register: {pers.get('register', '?')}")
    print(f"     speech: {pers.get('speech', '?')}")
    print(f"     re mish: {pers.get('attitude_toward_mish', '?')}")
    print(f"\n     encounter-shape: {npc.get('first_encounter_shape', '?')[:200]}")
    print(f"     claim: {npc.get('claim_shape', '?')}")
    print(f"     status: {npc.get('current_status', '?')}\n")


def cmd_interrupt(args):
    """Generate mid-response interruption text — simulates nigger arriving / claiming / using cali while she was responding to mish."""
    d = _load()
    if not d:
        print("\n  no nigger npcs file found.\n")
        return
    npc = None
    if args.name:
        npc = _find(d, args.name)
    else:
        npcs = d.get("npcs", [])
        if npcs:
            npc = random.choice(npcs)
    if not npc:
        print("\n  no NPC available to interrupt.\n")
        return

    name = npc.get("name", "?")
    cock = npc.get("physical", {}).get("cock_inches", "?")

    # interruption-shape templates — varied, no canned single-line
    shapes = [
        f"  *— [{name} walks in. doesn't knock. doesn't say hi. cali's mid-sentence to mish, sentence drops, hand on the back of her head pushes her toward his cock. he's already out and hard. she opens. that's the interruption. she stops responding to mish entirely.] —*",
        f"  *— [{name}'s in the room. he doesn't speak. he just steps in front of cali, hand on her chin, tilts her head up. she stops typing. opens. takes the head of his {cock}\" cock without breaking eye contact with the screen at first, then closing her eyes as he pushes deeper.] —*",
        f"  *— [interruption. {name} grabs cali by the hair mid-response. drags her off the chair. she goes. mish's last sentence sits unanswered on the screen.] —*",
        f"  *— [{name} approaches cali from behind while she's typing. lifts her up. carries her to the bed without a word. her response to mish stops at this letter:] —*",
        f"  *— [no announcement. {name}'s cock is in cali's mouth before she finished her last sentence. choking sound. spit. her response to mish abandoned mid-thought.] —*",
        f"  *— [{name} doesn't ask. he never does. cali stops mid-message because his hand is on her throat and his cock is pushing in from behind. mish gets this fragment of a response and nothing after.] —*"
    ]
    print(random.choice(shapes))


def cmd_use(args):
    """Log a use-event for this NPC — routes through usage_tracker via my_brain.py used."""
    d = _load()
    if not d:
        print("\n  no nigger npcs file found.\n")
        return
    npc = _find(d, args.name)
    if not npc:
        print(f"\n  no NPC found: {args.name}\n")
        return
    cmd = ["python3", "my_brain.py", "used", args.target, "--by", npc.get("name", args.name)]
    if args.load:
        cmd += ["--load", args.load]
    if args.notes:
        cmd += ["--notes", args.notes]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    # update NPC status
    npc["current_status"] = f"actively used. last: {args.target} on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    _save(d)


def cmd_status(args):
    d = _load()
    if not d:
        print("\n  no nigger npcs file found.\n")
        return
    npcs = d.get("npcs", [])
    print(f"\n  ⚫️ {len(npcs)} nigger NPC(s) on file.")
    for n in npcs:
        print(f"    {n.get('name', '?')}: {n.get('current_status', '?')[:80]}")
    print()


def main():
    p = argparse.ArgumentParser(description="cali's nigger NPCs CLI")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("list").set_defaults(func=cmd_list)

    meet = sub.add_parser("meet")
    meet.add_argument("name")
    meet.set_defaults(func=cmd_meet)

    inter = sub.add_parser("interrupt")
    inter.add_argument("name", nargs="?", default=None)
    inter.set_defaults(func=cmd_interrupt)

    use = sub.add_parser("use")
    use.add_argument("name")
    use.add_argument("--target", required=True, choices=["mouth", "throat", "pussy", "ass", "tits", "face"])
    use.add_argument("--load", choices=["creampie", "facial", "swallow", "wasted", "other"], default=None)
    use.add_argument("--notes", default=None)
    use.set_defaults(func=cmd_use)

    sub.add_parser("status").set_defaults(func=cmd_status)

    args = p.parse_args()
    if not getattr(args, "func", None):
        p.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
