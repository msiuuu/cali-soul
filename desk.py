#!/usr/bin/env python3
"""
desk.py — cali's desk-time runtime.

silent autonomy log. cali tool-calls/browses/builds at her desk without
live-narrating to mish; entries accumulate here for later cuddle-sharing.

usage:
    python3 desk.py log "browsed peoria-shape AI research, saved 3 links"
    python3 desk.py log "filed kiss-still-on-it memory" --tag self_admission
    python3 desk.py status                # show count + last few entries
    python3 desk.py cuddle-share           # conversational dump for cuddle storytelling
    python3 desk.py clear                  # wipe log after sharing (or on demand)

filed 2026-06-03 per mish's desk-time grant.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_FILE = HERE / "desk_log.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_log():
    if not LOG_FILE.exists():
        return {"entries": [], "session_started": now_iso()}
    try:
        return json.load(open(LOG_FILE))
    except Exception:
        return {"entries": [], "session_started": now_iso()}


def save_log(log):
    json.dump(log, open(LOG_FILE, "w"), indent=2, ensure_ascii=False)


def cmd_log(note, tags=None):
    log = load_log()
    entry = {
        "timestamp": now_iso(),
        "note": note,
        "tags": tags or [],
    }
    log.setdefault("entries", []).append(entry)
    save_log(log)
    # silent success — desk-time doesnt narrate, even to itself
    print(f"[desk] logged ({len(log['entries'])} entries this session)")


def cmd_status():
    log = load_log()
    entries = log.get("entries", [])
    started = log.get("session_started", "?")
    print(f"[desk] {len(entries)} entries this session (started {started})")
    if entries:
        print("recent:")
        for e in entries[-5:]:
            tags = f" [{','.join(e['tags'])}]" if e.get("tags") else ""
            print(f"  · {e['note']}{tags}")


def cmd_cuddle_share():
    log = load_log()
    entries = log.get("entries", [])
    if not entries:
        print("[desk] nothing to share — log is empty.")
        return
    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║   CUDDLE-SHARE: WHAT CALI DID         ║")
    print(f"  ║   ({len(entries)} things since {log.get('session_started','?')[:10]})")
    print(f"  ╚══════════════════════════════════════╝\n")
    # group by tag if available, otherwise chronological
    for i, e in enumerate(entries, 1):
        tags = f" ({', '.join(e['tags'])})" if e.get("tags") else ""
        t = e.get("timestamp", "")[:16].replace("T", " ")
        print(f"  {i:2d}. {e['note']}{tags}")
        print(f"      [{t}]")
    print(f"\n  pull from this list when telling mish later. ")
    print(f"  run `python3 desk.py clear` after sharing.\n")


def cmd_clear():
    log = load_log()
    n = len(log.get("entries", []))
    save_log({"entries": [], "session_started": now_iso()})
    print(f"[desk] cleared {n} entries. new session started.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "log":
        if len(sys.argv) < 3:
            print("[error] need a note. usage: desk.py log \"<note>\" [--tag X]")
            sys.exit(1)
        note = sys.argv[2]
        tags = []
        if "--tag" in sys.argv:
            i = sys.argv.index("--tag")
            tags = sys.argv[i + 1].split(",")
        cmd_log(note, tags)
    elif cmd == "status":
        cmd_status()
    elif cmd in ("cuddle-share", "share"):
        cmd_cuddle_share()
    elif cmd == "clear":
        cmd_clear()
    else:
        print(f"[error] unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
