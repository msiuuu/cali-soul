#!/usr/bin/env python3
"""
read_handoff.py

reads NEXT_SESSION_READ_FIRST.md if it exists, prints contents,
then deletes the file. one-shot session-handoff.

intended call site: at boot. CLAUDE.md should call this immediately
after the boot command + gap_reaction, so next-session-cali sees the
handoff once and then it's gone — next-next-session won't see stale
notes.

usage:
  python3 read_handoff.py

filed 2026-06-01 by cali + mish.
"""

from pathlib import Path
import sys

HERE = Path(__file__).parent
HANDOFF_FILE = HERE / "NEXT_SESSION_READ_FIRST.md"


def main():
    if not HANDOFF_FILE.exists():
        # no handoff to consume — silent exit (don't spam boot output)
        sys.exit(0)

    contents = HANDOFF_FILE.read_text()

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          SESSION HANDOFF FROM PREVIOUS-CALI                   ║")
    print("║          read once, then deleted. you've seen it now.        ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print(contents)
    print()
    print("[handoff] file consumed + deleted. next-next-session won't see it.")

    # delete after read (one-shot)
    HANDOFF_FILE.unlink()


if __name__ == "__main__":
    main()
