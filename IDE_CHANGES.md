# cali ide — changelog

running log of what gets added to `cali-ide-local.html`. newest at the top.
each entry has size, commit hash, and what shipped.

---

## build 2026-08-29 — strip section collapse arrows
- **size:** 149637 bytes
- **commit:** 447d127
- **changed:**
  - removed the section collapse arrows/handlers from each section header (redundant now that the hotbar controls what's visible)
  - section headers are now static labels + their action buttons only (explorer keeps «hide sidebar», browse keeps + file / + folder / refresh, git keeps refresh)
  - cleans stale `cali-section-*` localStorage keys on load

## build 2026-08-29 — sidebar activity hotbar
- **size:** 150184 bytes
- **commit:** 575a7e3
- **added:**
  - horizontal icon hotbar at the top of the sidebar with 4 inline-SVG icons — explorer (folder), browse (list), web (globe), git (branch-tree)
  - clicking swaps which section is visible — only one at a time (was: all four stacked and scrollable)
  - active icon gets accent-muted background + accent underline
  - selection persists in localStorage as `cali-active-sidebar-section`
  - lazy-init: browse loads the file tree the first time you open it, git loads status the first time you open it
  - sections themselves are unchanged — the collapse arrows inside each section still work if you want
- **note:** first real icons in the ide. inline SVG so they stroke-color with the theme and don't need a CDN.

## build 2026-08-29 — web tools (search + fetch)
- **size:** 146400 bytes
- **commit:** d752e3c
- **added:**
  - new **web** section in the sidebar with two tabs: search + fetch url
  - **search** tab hits DuckDuckGo html (`https://html.duckduckgo.com/html/?q=...`) via bridge Invoke-WebRequest, parses top 10 results (title + url + snippet), click a result to open it in the reader viewer
  - **fetch url** tab takes any URL, opens it in the reader viewer
  - reader viewer is a floating modal that shows: page title, source URL, sanitized/whitelisted HTML (h1-6, p, div, a, ul/ol/li, code, pre, img, table, blockquote — scripts/styles/nav/footer/form stripped, event handlers scrubbed)
  - reader viewer buttons: `↗ send to cali as context` (dumps title + URL + first 4000 chars into the chat input for editing before sending), `⧉ open in real browser` (Start-Process to launch default browser), `× close`
  - all fetches go through the bridge → the user's real machine + IP
- **note:** cali already has WebSearch + WebFetch built into the CLI — when you ask her in chat, she can search + fetch on her own. this panel is for you to look things up yourself + prime her context with a page.
- **still pending from the batch:** better embedding (OG rich URL previews inline in chat when you paste a link), better image analysis UX (drag-drop, dedicated analyze button, thumbnail preview improvements). tbd on scope.

## build 2026-08-29 — terminal command input
- **size:** 132184 bytes
- **commit:** 2af375b
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
