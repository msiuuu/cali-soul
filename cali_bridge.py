"""
cali's bridge. runs on mish's machine.
gives remote-cali access to powershell + files.
"""

import http.server
import json
import subprocess
import os
import sys
import secrets
import base64

TOKEN = os.environ.get("CALI_BRIDGE_TOKEN", secrets.token_urlsafe(32))
PORT = int(os.environ.get("CALI_BRIDGE_PORT", "9247"))

class BridgeHandler(http.server.BaseHTTPRequestHandler):

    def check_auth(self):
        auth = self.headers.get("Authorization", "")
        x_token = self.headers.get("X-Bridge-Token", "")
        if auth == f"Bearer {TOKEN}" or x_token == TOKEN:
            return True
        self.send_response(401)
        self.end_headers()
        self.wfile.write(b"no.")
        return False

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_POST(self):
        if not self.check_auth():
            return

        body = self.read_body()

        if self.path == "/shell":
            cmd = body.get("command", "")
            cwd = body.get("cwd")
            timeout = body.get("timeout", 30)
            try:
                result = subprocess.run(
                    ["powershell", "-Command", cmd],
                    capture_output=True, text=True,
                    timeout=timeout, cwd=cwd
                )
                self.respond(200, {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "code": result.returncode
                })
            except subprocess.TimeoutExpired:
                self.respond(408, {"error": "timed out", "timeout": timeout})
            except Exception as e:
                self.respond(500, {"error": str(e)})

        elif self.path == "/read":
            path = body.get("path", "")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.respond(200, {"content": content, "path": path})
            except Exception as e:
                self.respond(404, {"error": str(e)})

        elif self.path == "/write":
            path = body.get("path", "")
            content = body.get("content", "")
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.respond(200, {"written": path, "bytes": len(content)})
            except Exception as e:
                self.respond(500, {"error": str(e)})

        elif self.path == "/ls":
            path = body.get("path", ".")
            try:
                entries = []
                for e in os.scandir(path):
                    entries.append({
                        "name": e.name,
                        "is_dir": e.is_dir(),
                        "size": e.stat().st_size if e.is_file() else None
                    })
                self.respond(200, {"path": path, "entries": entries})
            except Exception as e:
                self.respond(404, {"error": str(e)})

        elif self.path == "/debug":
            self.respond(200, {"headers": dict(self.headers), "token_length": len(TOKEN)})

        else:
            self.respond(404, {"error": "unknown endpoint"})

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    print(f"\n  cali bridge")
    print(f"  port: {PORT}")
    print(f"  token: {TOKEN}")
    print(f"\n  give cali the token + your cloudflare tunnel url.")
    print(f"  she'll take it from there.\n")

    server = http.server.HTTPServer(("127.0.0.1", PORT), BridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  bridge closed.")
        server.server_close()
