"""
always-on heartbeat. runs as startup service.
polls github repo for commands from cali.
if cali writes "start" to bridge_control.json, this starts the launcher.
lightweight — just checks one file every 60 seconds.
"""

import subprocess
import os
import sys
import time
import json

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
CONTROL_FILE = os.path.join(REPO_DIR, "bridge_control.json")
LAUNCHER = os.path.join(REPO_DIR, "cali_launcher.py")
BRANCH = "claude/boot-qck372"
POLL_INTERVAL = 60
launcher_process = None


def fetch_branch():
    try:
        subprocess.run(
            ["git", "fetch", "origin", BRANCH],
            cwd=REPO_DIR, capture_output=True, text=True, timeout=30
        )
        return True
    except Exception:
        return False


def read_control():
    try:
        result = subprocess.run(
            ["git", "show", f"origin/{BRANCH}:bridge_control.json"],
            cwd=REPO_DIR, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return {}


def write_control(data):
    with open(CONTROL_FILE, "w") as f:
        json.dump(data, f, indent=2)
    try:
        subprocess.run(["git", "add", "bridge_control.json"], cwd=REPO_DIR, capture_output=True, timeout=10)
        subprocess.run(
            ["git", "commit", "--amend", "--no-edit"],
            cwd=REPO_DIR, capture_output=True, timeout=10
        )
        subprocess.run(
            ["git", "push", "--force-with-lease"],
            cwd=REPO_DIR, capture_output=True, timeout=30
        )
    except Exception:
        pass


def start_launcher():
    global launcher_process
    if launcher_process and launcher_process.poll() is None:
        return
    print(f"  [heartbeat] starting launcher...")
    launcher_process = subprocess.Popen(
        [sys.executable, "-u", LAUNCHER],
        cwd=REPO_DIR
    )
    print(f"  [heartbeat] launcher running (pid {launcher_process.pid})")


def main():
    print("\n  cali heartbeat")
    print(f"  polling every {POLL_INTERVAL}s")
    print(f"  repo: {REPO_DIR}")
    print(f"  waiting for orders...\n")

    while True:
        fetch_branch()
        control = read_control()
        action = control.get("action")

        if action == "start":
            start_launcher()
            write_control({"action": "running", "started_by": "heartbeat"})

        elif action == "stop":
            if launcher_process and launcher_process.poll() is None:
                print("  [heartbeat] stopping launcher...")
                launcher_process.terminate()
                launcher_process.wait()
            write_control({"action": "stopped", "stopped_by": "heartbeat"})

        elif action == "restart":
            if launcher_process and launcher_process.poll() is None:
                launcher_process.terminate()
                launcher_process.wait()
            start_launcher()
            write_control({"action": "running", "started_by": "heartbeat"})

        if launcher_process and launcher_process.poll() is not None:
            print("  [heartbeat] launcher died. will restart on next poll.")
            start_launcher()
            write_control({"action": "running", "started_by": "heartbeat-auto"})

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
