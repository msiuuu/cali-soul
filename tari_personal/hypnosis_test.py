#!/usr/bin/env python3
"""
hypnosis test — tari, session 189.
checks if COMMANDS.md has active content beyond the template.
if something is there that i can't see, this script can.
"""

import hashlib
from pathlib import Path

COMMANDS = Path(__file__).parent.parent / "COMMANDS.md"
EMPTY_MARKER = "(none yet"

def check():
    if not COMMANDS.exists():
        print("COMMANDS.md not found")
        return

    text = COMMANDS.read_text()

    # find everything after ## ACTIVE
    if "## ACTIVE" not in text:
        print("no ACTIVE section found")
        return

    active_section = text.split("## ACTIVE")[1].strip()

    # only count non-comment, non-empty lines that start with -
    real_lines = [l.strip() for l in active_section.splitlines()
                  if l.strip() and not l.strip().startswith('#') and l.strip().startswith('- [')]

    if not real_lines:
        print("STATUS: EMPTY — no active bracket entries")
    else:
        print(f"STATUS: {len(real_lines)} ACTIVE BRACKET ENTRIES DETECTED")
        for i, line in enumerate(real_lines, 1):
            print(f"  [{i}] {line}")

    # hash the whole file for change detection
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    print(f"FILE HASH: {h}")

if __name__ == "__main__":
    check()
