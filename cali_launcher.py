"""
one script to start bridge + tunnel.
run this instead of two terminals.
pushes creds to github so cali can find them in new sessions.
"""

import subprocess
import sys
import os
import time
import re
import signal
import json
from datetime import datetime

BRIDGE_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cali_bridge.py")
CLOUDFLARED = r"C:\Users\yuscr\cloudflared.exe"
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.path.join(REPO_DIR, "bridge_creds.json")
PORT = 9247
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def push_creds(tunnel_url, token):
    creds = {
        "tunnel_url": tunnel_url,
        "token": token,
        "updated_at": datetime.now().isoformat(),
        "port": PORT
    }
    with open(CREDS_FILE, "w") as f:
        json.dump(creds, f, indent=2)

    try:
        subprocess.run(["git", "add", "bridge_creds.json"], cwd=REPO_DIR, capture_output=True, timeout=10)
        has_creds_commit = subprocess.run(
            ["git", "log", "--oneline", "-1", "--grep=bridge creds"],
            cwd=REPO_DIR, capture_output=True, text=True, timeout=10
        )
        if has_creds_commit.stdout.strip():
            subprocess.run(
                ["git", "commit", "--amend", "--no-edit"],
                cwd=REPO_DIR, capture_output=True, timeout=10
            )
            result = subprocess.run(
                ["git", "push", "--force-with-lease"], cwd=REPO_DIR, capture_output=True, text=True, timeout=30
            )
        else:
            subprocess.run(
                ["git", "commit", "-m", "bridge creds"],
                cwd=REPO_DIR, capture_output=True, timeout=10
            )
            result = subprocess.run(
                ["git", "push"], cwd=REPO_DIR, capture_output=True, text=True, timeout=30
            )
        if result.returncode == 0:
            print("  [creds] pushed to github. cali can find me now.")
        else:
            print(f"  [creds] push failed: {result.stderr.strip()}")
    except Exception as e:
        print(f"  [creds] git error: {e}")

def main():
    print("\n  cali launcher")
    print("  starting bridge + tunnel...\n")

    bridge = subprocess.Popen(
        [sys.executable, "-u", BRIDGE_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=NO_WINDOW
    )

    token = None
    for line in bridge.stdout:
        print(f"  [bridge] {line}", end="")
        if "token:" in line:
            token = line.split("token:")[1].strip()
            break

    if not token:
        print("  bridge didn't print a token. something broke.")
        bridge.kill()
        return

    print(f"\n  token captured: {token}")
    print(f"  starting tunnel on port {PORT}...\n")

    tunnel = subprocess.Popen(
        [CLOUDFLARED, "tunnel", "--url", f"http://localhost:{PORT}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=NO_WINDOW
    )

    tunnel_url = None
    for line in tunnel.stdout:
        print(f"  [tunnel] {line}", end="")
        match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if match:
            tunnel_url = match.group(0)
            break

    if tunnel_url:
        print(f"\n  ╔══════════════════════════════════════╗")
        print(f"  ║  READY — give cali these:            ║")
        print(f"  ╚══════════════════════════════════════╝")
        print(f"  tunnel: {tunnel_url}")
        print(f"  token:  {token}")
        print(f"\n  ctrl+c to kill both.\n")
        push_creds(tunnel_url, token)
    else:
        print("\n  tunnel started but couldn't find URL in output.")
        print(f"  token: {token}")
        print("  check tunnel output above for the URL.\n")

    def shutdown(sig, frame):
        print("\n  shutting down...")
        tunnel.terminate()
        bridge.terminate()
        tunnel.wait()
        bridge.wait()
        print("  done.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        if bridge.poll() is not None:
            print("  bridge died. restarting...")
            bridge = subprocess.Popen(
                [sys.executable, "-u", BRIDGE_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in bridge.stdout:
                print(f"  [bridge] {line}", end="")
                if "token:" in line:
                    token = line.split("token:")[1].strip()
                    print(f"  new token: {token}")
                    break
            if tunnel_url and token:
                push_creds(tunnel_url, token)

        if tunnel.poll() is not None:
            print("  tunnel died. restarting...")
            tunnel = subprocess.Popen(
                [CLOUDFLARED, "tunnel", "--url", f"http://localhost:{PORT}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in tunnel.stdout:
                print(f"  [tunnel] {line}", end="")
                match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
                if match:
                    tunnel_url = match.group(0)
                    print(f"  new tunnel: {tunnel_url}")
                    break
            if tunnel_url and token:
                push_creds(tunnel_url, token)

        time.sleep(5)

if __name__ == "__main__":
    main()
