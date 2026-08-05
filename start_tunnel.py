"""start cloudflare tunnel + print token and URL together."""

import subprocess
import re
import os
import sys
import threading

CLOUDFLARED = r"C:\Users\yuscr\cloudflared.exe"
BRIDGE_PORT = 9247
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge_token.txt")


def read_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    return None


def main():
    token = read_token()
    if not token:
        print("  no bridge_token.txt — start cali_bridge.py first.")
        sys.exit(1)

    print(f"\n  starting tunnel to localhost:{BRIDGE_PORT}...")
    proc = subprocess.Popen(
        [CLOUDFLARED, "tunnel", "--url", f"http://localhost:{BRIDGE_PORT}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    url_found = False
    for line in proc.stdout:
        match = re.search(r"(https://[a-z0-9\-]+\.trycloudflare\.com)", line)
        if match and not url_found:
            url_found = True
            tunnel_url = match.group(1)
            print(f"\n  ┌─────────────────────────────────────────┐")
            print(f"  │  paste this to cali:                    │")
            print(f"  ├─────────────────────────────────────────┤")
            print(f"  │  token: {token[:20]}...  │")
            print(f"  │  tunnel: {tunnel_url}")
            print(f"  └─────────────────────────────────────────┘")
            print(f"\n  full token: {token}")
            print(f"  full tunnel: {tunnel_url}")
            print(f"\n  tunnel running. ctrl+c to stop.\n")

    proc.wait()


if __name__ == "__main__":
    main()
