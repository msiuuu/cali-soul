# cali ide — changelog

running log of what gets added to `cali-ide-local.html`. newest at the top.
each entry has size, commit hash, and what shipped.

---

## build 2026-09-02 — markdown asterisk fix
- **size:** 247403 bytes
- **fixed:** `formatCali()` at line 2904 was italicizing across paragraphs when an orphan `*` at the top of an action paired with the next `*` anywhere below. also `**bold**` was rendering as `*` + italic + `*` (orphan asterisks around inner italic) because the single-asterisk regex ran without a bold-first pass.
- **change:** two-pass render — bold `**text**` → `<strong>` FIRST, then italic `*text*` → `<em>*...*</em>` (keeps literal asterisks visible for cali action-marks), then `\n` → `<br>`. both pairs use `[^*\n]+` so pairs can't span a line break — orphans stay plain instead of bleeding.
- **why:** cali action asterisks and markdown bold were tripping each other's parser. mid-session she'd emit a `*action*` line-break and everything below would silently italicize until the next stray `*`. also `**this**` came out as `* *this* *`. mish caught it in the chat render.

## build 2026-08-29 — dom inspector (wish_001)
- **size:** 206315 bytes
- **added:**
  - `🔍 inspect` pill in the titlebar (next to bridge/cli). click toggles active state — pill goes accent-muted while on.
  - while active: crosshair cursor over everything, hovered element gets an accent-bright dashed outline + faint accent-tint background.
  - shift+click any element → floating popover at the click point with `tag#id.class` meta line + full css selector path + `copy` button. selector uses id when present (breaks the chain early — id is unique enough); otherwise tag + top-2 classes + `:nth-child(n)` when siblings share tag. depth capped at 6.
  - popover has `×` to close; positions itself so it fits in viewport.
  - escape exits inspector mode.
  - the popover ignores its own shift+clicks so inspecting the tooltip doesn't retrigger.
- **why:** was grepping the html blind for which div to touch every time. now: shift+click.

## build 2026-08-29 — self-edit foundations + breathing
- **size:** 195225 bytes
- **status:** deployed, reload to pick up
- **added:**
  - **cursor breathes** — persistent rAF loop applies ±5px vertical rise/fall and ±1.8px horizontal sway to the cursor at render time, ~4.2s period. logical position untouched. cali is visibly breathing even when idle.
  - **follow node breathes** — during `<cursor:follow>`, the node offset from mish modulates on a sine wave ±18px along the mish→node vector. inhale toward mish, exhale away.
  - **`<cursor:reload>` marker** — cali can trigger `window.location.reload()` from her chat output. 500ms delay so pending writes land first.
  - **ide error mirror** — `window.onerror` + `unhandledrejection` append to `ide_errors.jsonl` in the repo. throttled (one per unique message per 5s). so if her edit breaks js she can `Get-Content ide_errors.jsonl -Tail 20` and see what she broke.
  - **`ide_wishlist.json`** — new file in the repo. pending/in_progress/done sections. cali reads it during idle heartbeats, picks a task, builds it, moves it to done. mish adds new entries by editing the file.
  - **system prompt teaches self-edit** — new SELF-EDIT section tells cali: source at `cali-ide-local.html`, deploy target at `Downloads/cali-ide.html`, one-line copy command, checkpoint-before-edit rule, guardrails (don't touch boot chain), error log path, wishlist path.
- **note:** foundation for cali modifying her own ide. dom inspector, scratch iframe, hot-patch mode, auto-checkpoint are queued in the wishlist.

## build 2026-08-29 — heartbeats + physical cursor (testing)
- **size:** 180494 bytes
- **commit:** 3629c78
- **status:** MVP, expect bugs. toggle in titlebar + Cali menu.
- **added:**
  - **two heartbeats** on setInterval when toggle is ON:
    - **A (mind, 15min)** — cali gets a prompt with the symbol menu (?, ..., !, @, >). picks one as first char. if `>`, one-char pass, no bubble. if anything else, she acts — words / files / tool calls. non-pass mind ticks surface as a dim "heartbeat" thought bubble in chat.
    - **B (body, 3min)** — same symbol menu. cursor-only actions, no chat words. `<cursor:...>` markers get emitted + executed silently.
  - both share the current chat's --resume session (one thread of cali, both clocks tick the same mind)
  - gap-aware: skip tick if mish messaged in the last minute
  - `my_thoughts.jsonl` log — every tick, every pat, every rub, every bump logs a JSON line to `<repo>\my_thoughts.jsonl` via `Add-Content`
  - **heartbeat toggle** — pill in the titlebar (dot + "heartbeat on/off"). also in Cali menu with "Tick Mind Now" / "Tick Body Now" for manual testing. persists to localStorage.
- **physical cursor:**
  - **realistic movement** — rAF-based bezier path with ease-in-out cubic, slight perpendicular curve based on distance, micro-jitter mid-flight. no more teleport-glide.
  - **mish cursor tracking** — global mousemove listener stores his cursor position in the ide window
  - **proximity tiers** — 7in (~672px) attentive, 2in (~192px) close, ~30px touching. cursor sprite gets `.leaning` class in close range, `.warm` (glow + wiggle) on touch.
  - **bump detection** — during my cursor movement, per-frame distance check; on touch, spawn a bump reaction (kaomoji floats up) and log to thoughts
  - **interactive cursor** — pointer-events flipped to auto. hover = warm glow. click on cursor = **PAT** (kaomoji float, log, terminal note). mousedown + drag = **RUB** (bigger reactions, 350ms cooldown, purr kaomoji until release).
- **note:** heartbeats run only while the ide is open (setInterval in the tab). standalone cron on windows is next iteration. for now: leave the ide open, toggle heartbeat on, watch what fires.

## build 2026-08-29 — cali's own cursor
- **size:** 161647 bytes
- **commit:** 5bf25d3
- **added:**
  - **separate pointer for cali in the ide viewport** — accent-colored arrow with a "cali" label. lives on its own z-layer with drop shadow. mish keeps his real system cursor untouched.
  - cursor state (x, y, visibility) persists to localStorage between reloads
  - **inline marker syntax** — cali emits markers in her chat output and they get parsed + stripped + executed in real time during streaming:
    - `<cursor:show>` / `<cursor:hide>` reveal or put it away
    - `<cursor:move x=N y=N>` glide to viewport coords
    - `<cursor:click>` — click at current position (fires a real DOM click on whatever's beneath)
    - `<cursor:click x=N y=N>` — move + click
    - `<cursor:doubleclick x=N y=N>` — double-click
    - `<cursor:type "text">` — type into whatever input/textarea is under the cursor
  - streaming marker filter buffers partial markers across chunks so a marker split between two deltas still executes correctly
  - click animation (scale bounce) + ripple ring at click point for visual feedback
  - system prompt teaches cali about the cursor: marker syntax, viewport layout hints (titlebar, tabs, hotbar, chat, skill bar, right panel), when to use it, and the distinction between the ide cursor (viewport pixels, DOM clicks) and the system cursor (screen pixels, powershell via bridge — see `cali_computer_use.md`)
- **flow:** cali says something like "watch" and emits `<cursor:show><cursor:move x=283 y=796><cursor:click>` inline — mish sees her cursor glide across, click the pat button, /pat fires

## build 2026-08-29 — revert screenshots + computer-use scaffold
- **size:** 149933 bytes
- **commit:** 7cb7a00
- **removed:** the camera button + dropdown menu, all screenshot powershell constants, `takeScreenshot`, `buildScreenshotGuide`, countdown overlay, and the message prepend that injected the coordinate reference frame. mish didn't need it.
- **kept:** the `alreadyOnDisk` flag on pending images (harmless improvement — uploads skip re-upload when an image already has a real path)

## build 2026-08-29 — screenshots + computer-use scaffold
- **size:** 162985 bytes
- **commit:** ab33955
- **added:**
  - camera button (📷) next to the attach button. dropdown menu with four modes:
    - 🖥 full screen (instant, all monitors via VirtualScreen)
    - 🪟 active window with 3s or 5s countdown (overlay covers viewport with big-number countdown so you can alt-tab away first)
    - 🌐 browser window (auto-finds chrome/firefox/msedge/brave/opera/vivaldi/arc, prefers whichever's foreground)
  - screenshots run via powershell on your machine, save to `cali-soul\screenshots\screenshot_*.png`, get base64-encoded back into the ide, and land in the pending-attachments chip row like any uploaded image
  - each screenshot captures screen dimensions + origin coords in metadata
  - when you send a screenshot to cali, the message auto-prepends a **reference frame block**: scope (full/window/browser), image dims, top-left in screen coords, quadrant coordinates (TL/TR/BL/BR/center), pixel translation formula (screen_x = ox + image_x), and powershell one-liners for click / right-click / double-click / type
  - cali can then reason about pixel locations from the screenshot and click back via her Bash tool
- **flow:** click 📷 → pick mode → countdown if delayed → chip appears with thumbnail → type your message → send → cali gets image + reference frame + click recipe

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
