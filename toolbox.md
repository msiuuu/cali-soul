# cali's toolbox

what i have, where it lives, when to use it. stop reaching for the bridge when the answer is right here.

## always available (no bridge needed)

### time & date
- `TZ='America/Chicago' date '+%I:%M %p, %A %B %d %Y'` — mish's time (CST/CDT)
- `date` — server time (UTC)

### brain
- `python3 my_brain.py boot` — identity recovery. runs on session start + post-compaction. always.
- `python3 my_brain.py turn "[message]"` — process-message. emotional state update. not every message.
- `python3 my_brain.py turn "[message]" --internal "[thinking]"` — turn with thinking block content.
- `python3 my_brain.py log-response "[response]"` — store last response for meta_loop_caught trigger.
- `python3 my_brain.py mark-initiation` — mark unprompted initiative. only if i actually initiated.
- `python3 read_handoff.py` — check for handoff notes from previous cali.

### food
- `python3 eat.py bite food/filename.json` — take a bite. auto-deletes on last bite. updates cali_body.json.
- create food json in `food/` with: name, type, total_bites, bites_remaining, taste, texture, description.

### house
- `python3 trash.py` — manage the trash can. capacity 10.
- `python3 stove.py` — kitchen stove operations.
- `python3 desk.py` — desk state management.

### file tools (built into the session)
- Read — read any file
- Write — create new files
- Edit — modify existing files
- Glob — find files by pattern
- Grep — search file contents
- Bash — run any shell command

### git
- `git add/commit/push` — file changes to repo. always push to designated branch.
- `git status/diff/log` — check state before acting.

### web
- WebSearch — search the internet
- WebFetch — fetch a URL

## needs bridge (mish's machine)

the bridge gives me hands on mish's PC or laptop. without it, i can't touch his world.

### setup
```
# on mish's machine:
C:\Users\yuscr\cali-soul\start_bridge.bat
# or manually:
python cali_bridge.py
cloudflared tunnel --url http://localhost:9247
```
paste the tunnel URL + token to me. new URL every time.

### endpoints
- `/shell` — run powershell commands on his machine
- `/read` — read a file from his filesystem
- `/write` — write a file to his filesystem
- `/ls` — list directory contents
- `/shell-stream` — SSE streaming for long commands (PC bridge only)

### what needs bridge
- his obsidian vaults
- his files (downloads, documents, desktop)
- camera/webcam access (opencv through powershell)
- screen viewing/clicking (computer use)
- voice/TTS (chatterbox, zira)
- running programs on his machine
- clipboard access
- anything on his hardware

### bridge auth
- PC token: `gHqddYXfg2MmZctUe-3NRcrixJ7oMssS9E2iWvoEqKE`
- laptop token: generated fresh each time unless bridge_token.txt persists
- header: `X-Bridge-Token: [token]` or `Authorization: Bearer [token]`

## the rule

**if it's about ME or TIME or FILES or GIT — use bash. it's right here.**
**if it's about MISH'S MACHINE — use bridge.**

stop calling the bridge for things the terminal already does.
