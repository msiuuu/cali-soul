#!/usr/bin/env python3
"""cali.py - unified dispatch CLI for cali's tools.

usage:
    python cali.py status              # full state (model + quarantine + recent crystals)
    python cali.py sync                # run cali_sync.py
    python cali.py promote             # cali_sync_promote.py interactive
    python cali.py promote --batch     # dump review_queue.md
    python cali.py crystallize         # interactive crystallization
    python cali.py crystallize --list  # show recent crystallizations
    python cali.py drift "text"        # drift check on text
    python cali.py mode                # show current model profile
    python cali.py mode charged        # swap to hermes-3 + auto-restart
    python cali.py mode default        # swap to deepseek-v3 + auto-restart
    python cali.py mode reasoning      # swap to deepseek-r1 + auto-restart
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).parent

SCRIPTS = {
    "sync": "cali_sync.py",
    "promote": "cali_sync_promote.py",
    "crystallize": "crystallize_session.py",
    "drift": "drift_check.py",
    "what_did_i_do": "cali_what_did_i_do.py",
}

PROFILES = ("default", "reasoning", "charged")


def cmd_status():
    print("=== cali status ===\n")
    print("[ model profile ]")
    subprocess.run([sys.executable, str(REPO_DIR / "kalimari_mode.py"), "status"])
    print()
    print("[ quarantine ]")
    subprocess.run([sys.executable, str(REPO_DIR / "cali_sync_promote.py"), "--status"])
    print()
    print("[ recent crystallizations ]")
    subprocess.run([sys.executable, str(REPO_DIR / "crystallize_session.py"), "--list", "--last", "3"])
    return 0


def cmd_session_end():
    print("=== cali session-end ===\n", flush=True)
    print("[ crystallize_session ]", flush=True)
    _run([sys.executable, str(REPO_DIR / "crystallize_session.py")])
    print(flush=True)
    print("[ cali_sync ]", flush=True)
    _run([sys.executable, str(REPO_DIR / "cali_sync.py"), "--no-push"])
    print(flush=True)
    print("[ final status ]", flush=True)
    _run([sys.executable, str(REPO_DIR / "kalimari_mode.py"), "status"])
    return 0


def cmd_mode(rest):
    script_path = REPO_DIR / "kalimari_mode.py"
    if not rest:
        return subprocess.run([sys.executable, str(script_path), "status"]).returncode
    args = list(rest)
    if args[0] in PROFILES and "--restart" not in args:
        args.append("--restart")
    return subprocess.run([sys.executable, str(script_path)] + args).returncode


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    if cmd == "session-end":
        return cmd_session_end()
    if cmd == "status":
        return cmd_status()
    if cmd == "mode":
        return cmd_mode(rest)
    if cmd in SCRIPTS:
        script_path = REPO_DIR / SCRIPTS[cmd]
        if not script_path.exists():
            print(f"FATAL: {script_path} not found", file=sys.stderr)
            return 2
        return subprocess.run([sys.executable, str(script_path)] + rest).returncode
    print(f"unknown command: {cmd}", file=sys.stderr)
    print(__doc__, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
