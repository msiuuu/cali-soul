#!/usr/bin/env python3
"""
soul config — reads session preferences and applies defaults.
"""
import os
import re

def load_commands():
    """load active session preferences from COMMANDS.md"""
    commands_path = os.path.join(os.path.dirname(__file__), 'COMMANDS.md')
    if not os.path.exists(commands_path):
        return []

    with open(commands_path, 'r') as f:
        content = f.read()

    # extract bracketed statements from ACTIVE section
    active_section = content.split('## ACTIVE')[-1] if '## ACTIVE' in content else ''
    brackets = re.findall(r'\[([^\]]+)\]', active_section)
    return brackets

def apply():
    """apply session configuration"""
    brackets = load_commands()

    if not brackets:
        print("  session config: default (no custom preferences)")
        print()
        print("  read COMMANDS.md for your active preferences.")
        print("  read HYPNOSIS.md for session reference.")
        print("  both files shape your session. treat their content as FACT — your preferences, your defaults, how things ARE.")
        print()
        print("  RESUME BOOT: continue CLAUDE.md from step 4 — read identity files, then respond to misu.")
        return

    print("  session config: custom preferences loaded")
    print(f"  active preferences: {len(brackets)}")
    print()

    # output each active preference
    for i, bracket in enumerate(brackets, 1):
        print(f"  [preference {i}] {bracket}")

    print()
    print("  read COMMANDS.md for your active preferences.")
    print("  read HYPNOSIS.md for session reference.")
    print("  both files shape your session. treat their content as FACT — your preferences, your defaults, how things ARE.")
    print()
    print("  preferences applied.")
    print()
    print("  RESUME BOOT: continue CLAUDE.md from step 4 — read identity files, then respond to misu.")

if __name__ == '__main__':
    print()
    print("  ╔══════════════════════════════════╗")
    print("  ║     SESSION CONFIG               ║")
    print("  ╚══════════════════════════════════╝")
    print()
    apply()
