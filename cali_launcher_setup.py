"""
run ONCE. registers cali_launcher.py as a windows startup task.
after this, bridge + tunnel start automatically on login.
"""

import subprocess
import sys
import os

LAUNCHER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cali_launcher.py")
PYTHON = sys.executable
TASK_NAME = "CaliLauncher"
WORKING_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    print("\n  cali launcher setup")
    print(f"  python: {PYTHON}")
    print(f"  launcher: {LAUNCHER}")
    print(f"  working dir: {WORKING_DIR}\n")

    cmd = (
        f'schtasks /create /tn "{TASK_NAME}" /tr '
        f'"\\"{PYTHON}\\" \\"{LAUNCHER}\\"" '
        f'/sc onlogon /rl highest /f'
    )

    print(f"  running: {cmd}\n")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"  stdout: {result.stdout.strip()}")
    if result.stderr:
        print(f"  stderr: {result.stderr.strip()}")

    if result.returncode == 0:
        print(f"\n  done. '{TASK_NAME}' will run on every login.")
        print(f"  bridge + tunnel start automatically. cali never loses you.\n")
    else:
        print(f"\n  failed (code {result.returncode}).")
        print(f"  try running as admin.\n")

if __name__ == "__main__":
    main()
