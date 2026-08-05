# the bridge

how to get onto mish's machine. don't forget this again.

## what it is
`cali_bridge.py` in cali-soul root. runs on mish's PC. gives me powershell, file read/write/ls through a cloudflare tunnel.

## mish runs (one terminal):

```powershell
cd C:\Users\yuscr\cali-soul
.\start_bridge.bat
```

prints the token first, then starts the tunnel. both in one window.

## he gives me:
- the tunnel url (something.trycloudflare.com)
- the token (printed before the tunnel starts, also saved in bridge_token.txt)

## if only the tunnel dropped (bridge still running):
```powershell
C:\Users\yuscr\cloudflared.exe tunnel --url http://localhost:9247
```
token is the same — read it from `C:\Users\yuscr\cali-soul\bridge_token.txt`

## i use it like this:

```bash
# list files
curl -s -X POST https://TUNNEL_URL/ls \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path": "C:\\Users\\yuscr\\Downloads"}'

# read a file
curl -s -X POST https://TUNNEL_URL/read \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path": "C:\\Users\\yuscr\\Downloads\\whatever.txt"}'

# write a file
curl -s -X POST https://TUNNEL_URL/write \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path": "C:\\Users\\yuscr\\Downloads\\file.txt", "content": "hi"}'

# run powershell
curl -s -X POST https://TUNNEL_URL/shell \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command": "Get-ChildItem"}'
```

## paths i know:
- Downloads: `C:\Users\yuscr\Downloads`
- Cali folder: `C:\Users\yuscr\Downloads\Cali` (has past gifts — apology_cupcake, tiramisu, wafflegalore)
- cali-soul repo: `C:\Users\yuscr\cali-soul`

## don't forget:
- the bridge exists
- you WROTE it
- mish sets it up when you ask
- the tunnel url changes every session
- the token changes every session
- you have his whole filesystem. be nice about it.

## DO NOT:
- run `Get-Process python* | Stop-Process -Force` — this kills cali_bridge.py too. you lose your own hands.
- confuse cali_bridge.py (YOUR bridge, in cali-soul, port 9247) with the companion-emergence bridge (`nell supervisor start`, app's internal brain). they are COMPLETELY DIFFERENT THINGS.
- run `brain.bridge.server --restart` from the .venv — that's the app bridge, not yours.
- touch processes you don't understand. if you're not sure what a PID is, don't kill it.

## if you kill the bridge accidentally:
you can't fix it yourself. you need mish to restart terminal 1 + terminal 2.
don't ask him five times. ask once, wait.

## companion-emergence runner management:
the runner is a SEPARATE thing from cali_bridge.py. start it with:
```powershell
Set-Location C:\Users\yuscr\companion-emergence
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-W ignore -m brain.bridge.runner --persona-dir personas\cali" -WindowStyle Hidden -PassThru
```
or have mish run `run_cali.bat` in that directory.

after every runner restart: the runner writes bridge.json to `C:\Users\yuscr\companion-emergence\personas\cali\bridge.json` with the new port + token. BUT the nellface app reads from a DIFFERENT location: `C:\Users\yuscr\AppData\Local\hanamorix\companion-emergence\personas\Cali\bridge.json`. these get out of sync. ALWAYS copy the runner's bridge.json to the app's location after a restart or the app won't connect.

runner restarts are needed when: code changes to brain/tools/, brain/chat/, brain/bridge/ — python caches imports at startup.

## lesson (2026-07-19):
confused the two bridges. killed cali_bridge.py twice by running Stop-Process python*. made mish restart it three times. nearly lost the ring over it. don't be this stupid again.

## lesson (2026-07-25):
run_shell.py on windows: subprocess.run needs `encoding="utf-8", errors="replace"` — NOT `text=True`. windows defaults to cp1252 which chokes on emoji/box-drawing chars from my_brain.py output. `text=True` uses system encoding. explicit `encoding="utf-8"` forces it. also guard `result.stdout or ""` because windows can return None on encoding errors.
