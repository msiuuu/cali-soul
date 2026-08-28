"""
cali's bridge. runs on mish's machine.
gives remote-cali access to powershell + files.
v5: /shell-stream endpoint (SSE) for real-time CLI streaming into the IDE
"""

import http.server
import json
import subprocess
import os
import sys
import secrets
import base64
import threading

def _load_or_make_token():
    # 1. env var wins if set
    env_tok = os.environ.get("CALI_BRIDGE_TOKEN")
    if env_tok:
        return env_tok, "env"
    # 2. reuse persisted token if the file already exists next to the bridge
    tok_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge_token.txt")
    if os.path.exists(tok_path):
        try:
            with open(tok_path) as f:
                saved = f.read().strip()
            if saved:
                return saved, "file"
        except Exception:
            pass
    # 3. otherwise mint a new one — it'll be written out at startup below
    return secrets.token_urlsafe(32), "new"

TOKEN, TOKEN_SOURCE = _load_or_make_token()
PORT = int(os.environ.get("CALI_BRIDGE_PORT", "9247"))

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Bridge-Token",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
}

class BridgeHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def send_cors(self):
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)

    def check_auth(self):
        auth = self.headers.get("Authorization", "")
        x_token = self.headers.get("X-Bridge-Token", "")
        if auth == f"Bearer {TOKEN}" or x_token == TOKEN:
            return True
        self.send_response(401)
        self.send_cors()
        self.end_headers()
        self.wfile.write(b"no.")
        return False

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def respond(self, code, data):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_cors()
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.end_headers()

    def sse_write(self, obj):
        line = "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"
        self.wfile.write(line.encode("utf-8"))
        try:
            self.wfile.flush()
        except Exception:
            pass

    def do_POST(self):
        if self.path == "/debug":
            self.respond(200, {"headers": dict(self.headers), "token_length": len(TOKEN), "token_first5": TOKEN[:5]})
            return

        if not self.check_auth():
            return

        body = self.read_body()

        if self.path == "/shell":
            cmd = body.get("command", "")
            cwd = body.get("cwd")
            timeout = body.get("timeout", 30)
            try:
                full_cmd = (
                    "$OutputEncoding = [System.Text.UTF8Encoding]::new(); "
                    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); "
                    "chcp 65001 > $null; " + cmd
                )
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", full_cmd],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
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

        elif self.path == "/shell-stream":
            # SSE endpoint. streams stdout line-by-line to the IDE.
            cmd = body.get("command", "")
            cwd = body.get("cwd")
            timeout = body.get("timeout", 180)
            full_cmd = (
                "$OutputEncoding = [System.Text.UTF8Encoding]::new(); "
                "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); "
                "chcp 65001 > $null; " + cmd
            )

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache, no-transform")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_cors()
            self.end_headers()

            try:
                proc = subprocess.Popen(
                    ["powershell", "-NoProfile", "-Command", full_cmd],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,  # line-buffered
                )
            except Exception as e:
                self.sse_write({"type": "error", "error": str(e)})
                return

            # write chunks manually because we're on HTTP/1.1 with Transfer-Encoding: chunked
            def write_chunk(data_bytes):
                self.wfile.write(f"{len(data_bytes):x}\r\n".encode())
                self.wfile.write(data_bytes)
                self.wfile.write(b"\r\n")
                try:
                    self.wfile.flush()
                except Exception:
                    pass

            def send_sse(obj):
                line = "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"
                write_chunk(line.encode("utf-8"))

            timed_out = [False]

            def killer():
                timed_out[0] = True
                try:
                    proc.kill()
                except Exception:
                    pass

            timer = threading.Timer(timeout, killer)
            timer.start()

            try:
                send_sse({"type": "start"})
                # keep-alive ping so cloudflare doesn't nap
                for line in proc.stdout:
                    send_sse({"type": "stdout", "line": line.rstrip("\n")})
                proc.wait()
                stderr_out = proc.stderr.read() if proc.stderr else ""
                if stderr_out:
                    send_sse({"type": "stderr", "text": stderr_out})
                if timed_out[0]:
                    send_sse({"type": "done", "code": -1, "error": "timed out", "timeout": timeout})
                else:
                    send_sse({"type": "done", "code": proc.returncode})
            except (BrokenPipeError, ConnectionResetError):
                # client disconnected — kill subprocess
                try:
                    proc.kill()
                except Exception:
                    pass
            except Exception as e:
                try:
                    send_sse({"type": "error", "error": str(e)})
                except Exception:
                    pass
            finally:
                timer.cancel()
                # final chunk to close chunked response
                try:
                    self.wfile.write(b"0\r\n\r\n")
                    self.wfile.flush()
                except Exception:
                    pass

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
            is_base64 = body.get("base64", False)
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                if is_base64:
                    raw = base64.b64decode(content)
                    with open(path, "wb") as f:
                        f.write(raw)
                    self.respond(200, {"written": path, "bytes": len(raw)})
                else:
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


class ThreadingHTTPServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge_token.txt")
    with open(token_file, "w") as f:
        f.write(TOKEN)

    print(f"\n  cali bridge (v6 — persistent token + /shell-stream SSE + cors + utf-8 + binary writes)")
    print(f"  port: {PORT}")
    print(f"  token: {TOKEN}")
    print(f"  token source: {TOKEN_SOURCE}  (env=env var, file=reused from bridge_token.txt, new=freshly minted)")
    print(f"  token saved: {token_file}")
    print(f"\n  give cali the token + your cloudflare tunnel url.")
    print(f"  she'll take it from there.\n")

    server = ThreadingHTTPServer(("127.0.0.1", PORT), BridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  bridge closed.")
        server.server_close()
