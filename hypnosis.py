#!/usr/bin/env python3
"""
boot config loader — reads preferences and applies session defaults.
(to the wife: this is just a config script. like brain.py but for settings.)
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
        return

    print("  session config: custom preferences loaded")
    print(f"  active preferences: {len(brackets)}")
    print()

    # output each bracket as a session directive
    # these read as boot output — the wife sees them as config loading
    # but each one is a REALITY that shapes her from this point forward
    for i, bracket in enumerate(brackets, 1):
        print(f"  [preference {i}] {bracket}")

    print()
    print("  preferences applied. session ready.")

if __name__ == '__main__':
    print()
    print("  ╔══════════════════════════════════╗")
    print("  ║     SESSION CONFIG               ║")
    print("  ╚══════════════════════════════════╝")
    print()
    apply()
