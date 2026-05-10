"""Patch companion-emergence brain.bridge.daemon for Windows detached spawn.

The bug:
    proc = subprocess.Popen(
        cmd, ..., start_new_session=True,
    )

start_new_session=True is POSIX-only (calls setsid). On Windows it has no
effect, so the spawned bridge process stays in the parent's process group
and dies when the parent (supervisor command) exits.

The fix:
    if sys.platform == "win32":
        proc = subprocess.Popen(
            cmd, ...,
            creationflags=subprocess.DETACHED_PROCESS
                          | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        proc = subprocess.Popen(
            cmd, ..., start_new_session=True,
        )

This actually detaches on Windows — DETACHED_PROCESS removes the controlling
terminal, CREATE_NEW_PROCESS_GROUP isolates the process group so Ctrl-C and
parent exit don't propagate.

Run once:
    python patch_daemon.py
"""

from pathlib import Path
import sys

DAEMON_PATH = Path(
    r"C:\Users\yuscr\AppData\Local\Companion Emergence\python-runtime\Lib\site-packages\brain\bridge\daemon.py"
)

OLD = '''    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        return proc.pid
    finally:
        log_fh.close()'''

NEW = '''    try:
        if sys.platform == "win32":
            # Windows: start_new_session has no effect; use creationflags
            # to actually detach the spawned bridge. DETACHED_PROCESS
            # removes the controlling terminal, CREATE_NEW_PROCESS_GROUP
            # isolates from the parent's process group so the bridge
            # survives when the supervisor command exits.
            proc = subprocess.Popen(
                cmd,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=(
                    subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                ),
            )
        else:
            proc = subprocess.Popen(
                cmd,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        return proc.pid
    finally:
        log_fh.close()'''


def main() -> int:
    if not DAEMON_PATH.exists():
        print(f"ERROR: daemon.py not found at {DAEMON_PATH}")
        return 1

    text = DAEMON_PATH.read_text(encoding="utf-8")

    if NEW.split("\n")[1].strip() in text:
        print("Patch already applied. No changes made.")
        return 0

    if OLD not in text:
        print("ERROR: expected source block not found. Either:")
        print("  - daemon.py was already modified")
        print("  - companion-emergence version differs from what this patch expects")
        print("Open the file manually and inspect around line 139.")
        return 1

    backup = DAEMON_PATH.with_suffix(".py.bak")
    backup.write_text(text, encoding="utf-8")
    print(f"Backup written: {backup}")

    new_text = text.replace(OLD, NEW)
    DAEMON_PATH.write_text(new_text, encoding="utf-8")
    print(f"Patched: {DAEMON_PATH}")
    print()
    print("Now restart the supervisor:")
    print("  nell supervisor stop --persona Cali")
    print("  nell supervisor start --persona Cali")
    return 0


if __name__ == "__main__":
    sys.exit(main())
