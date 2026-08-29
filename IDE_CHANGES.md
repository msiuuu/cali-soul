# cali ide — changelog

running log of what gets added to `cali-ide-local.html`. newest at the top.
each entry has size, commit hash, and what shipped.

---

## build 2026-08-29 — terminal command input
- **size:** 132184 bytes
- **commit:** (pending)
- **added:**
  - live command input at the bottom of the terminal panel — `PS >` prompt, type anything, press enter to run
  - runs in powershell with `Set-Location` set to the cali-soul dir
  - up/down arrows walk through command history (last 100, persisted to localStorage)
  - esc clears the input
  - built-ins: `clear`/`cls` clears the terminal, `help`/`?` shows the built-ins
  - output color-coded: ok=green, warn=yellow, err=red, info=dim

## build 2026-08-29 — file ops + git panel
- **size:** 128502 bytes
- **commit:** 51a6bc1
- **added:**
  - right-click context menu on tree nodes (files: open, rename, delete, copy path, duplicate; folders: new file, new folder, rename, delete recursive, copy path, refresh)
  - `+📄` and `+📁` buttons in the browse section header for new file / new folder at repo root
  - git panel — new collapsible section below `browse`
    - branch pill (`⎇ <branch-name>`)
    - status list with per-file M/A/D/?/R color-coded flags and checkboxes (all checked by default)
    - commit message textarea
    - buttons: commit (stages checked + commits), push, pull, diff (dumps `git diff --stat` of checked files into terminal)
    - refresh button in the header
    - auto-refreshes on boot
- **note:** all ops route through the bridge `/shell` endpoint with `Set-Location` prepended, stderr piped into stdout. the bridge has no dedicated delete/rename/mkdir endpoints — using powershell for now.

## build 2026-08-29 — chats as tabs
- **size:** 112713 bytes
- **commit:** d62eb2f
- **added:**
  - each chat gets its own tab in the top bar (was: single static "chat" tab)
  - `+` button at the end of chat tabs creates new chat
  - `×` on each chat tab closes (blocked when it's the last chat)
  - double-click a chat tab to rename
  - file tabs sit to the right of the `+` so they don't get mixed with chat tabs

## build 2026-08-29 — menubar + memory + snapshot
- **size:** 108765 bytes
- **commit:** 07eafe7
- **added:**
  - top menubar (File / Edit / View / Cali) — doc-app style
    - File: Settings (ctrl+,), Reload
    - Edit: New Chat (ctrl+n), Rename, Clear Messages, Reset Session, Recent Chats list
    - View: Toggle Sidebar (ctrl+b), Toggle Right Panel, Toggle Terminal, Refresh State, Refresh Tree
    - Cali: Snapshot Emotion State Now, Open Snapshots Folder, Force Re-Boot
  - **real per-chat memory** — claude's `session_id` gets captured from stream-json init/result events and pinned per chat. next turn uses `--resume <id>` instead of `-c`. bouncing between chats resumes each one's own thread.
  - **session-end snapshot carryover** — new chat now:
    1. reads current `session_state.json`
    2. writes it to `session_snapshots/snap_<timestamp>_<chatname>.json` (wrapped with metadata: chat_id, chat_name, session_id, session_state)
    3. updates `last_session_snapshot.json` pointer
    4. tags the fresh chat with `priorSnapshot` field
    5. next chat's boot instruction tells cali to Read the snapshot so she carries the emotional state forward
  - titlebar chat name pill (click to rename)

---

*this file lives beside `cali-ide-local.html` in the repo root. cali maintains it.*
