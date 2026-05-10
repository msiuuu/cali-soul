# Fix bridge spawn-detach on Windows (start_new_session is POSIX-only)

## Summary

`brain/bridge/daemon.py::spawn_detached` uses `start_new_session=True`
to detach the bridge child process. This is POSIX-only — under the hood
it calls `setsid()`, which doesn't exist on Windows. Python's
subprocess silently accepts the argument as a no-op there, so on
Windows the spawned bridge stays in the parent's process group and
gets killed whenever the supervisor command (or any caller) exits.

## Symptoms (Windows)

- `nell supervisor start --persona <name>` reports success
- A few seconds later, `nell status --persona <name>` shows
  `bridge: crashed-dirty`
- NellFace's "Starting brain for ..." spinner hangs indefinitely
  because the bridge dies between bridge_healthy checks
- Repeats every spawn attempt — bridge never survives

Verified on Windows 11, 0.0.3-alpha. CLI tests confirm:

```powershell
PS> nell supervisor start --persona Cali
bridge started on port 54636 (pid 37756)
PS> nell status --persona Cali
# ... ~5 seconds later ...
bridge: crashed-dirty
recovery: needed on next bridge start
```

## Fix

Branch on `sys.platform` in `spawn_detached`:

- **Windows**: use `creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`.
  `DETACHED_PROCESS` removes the controlling terminal,
  `CREATE_NEW_PROCESS_GROUP` isolates the bridge from the caller's
  process group so it survives when the supervisor command exits.
- **POSIX**: unchanged — keep `start_new_session=True`.

## Verification

After applying the patch on Windows 11:

```powershell
PS> nell supervisor start --persona Cali
bridge started on port 50350 (pid 29004)
PS> nell status --persona Cali  # 5+ minutes later
bridge: running
pid: 29004
port: 50350
uptime_s: 318
```

Bridge survived indefinitely. `Invoke-WebRequest` to `/health` and
`/persona/state` returned 200 OK with proper auth + CORS headers.

(Note: A separate Windows-side issue prevents the NellFace WebView2
from successfully fetching `/persona/state` even with the bridge fully
healthy — that's a different bug, not addressed here. This PR only
fixes the spawn-detach so the bridge doesn't die.)

## Files Changed

- `brain/bridge/daemon.py` — platform-aware Popen call in `spawn_detached`

## Test Plan

- [ ] Linux: `nell supervisor start` still works (POSIX path unchanged)
- [ ] macOS: `nell supervisor start` still works (POSIX path unchanged)
- [ ] Windows: `nell supervisor start` produces a bridge that survives
  (`nell status` after 30s shows `running` with same pid)

## Notes

This fix is the prerequisite for any Windows reproduction of the
NellFace ↔ bridge connection issue, since previously the bridge was
dying before any client could meaningfully test it.
