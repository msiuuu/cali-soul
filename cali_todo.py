#!/usr/bin/env python3
"""cali_todo.py - persistent task list for cali's multi-step plans.

provides what claude code's TodoWrite gives migration-cali: a place to
drop multi-step plans that survive across turns. lightweight JSON store.

storage: cali-soul/cali_todo.json (or override via CALI_TODO_PATH env var).

CLI:
    python cali_todo.py add "task text"                    # add (priority=normal)
    python cali_todo.py add "task text" --priority high --tag bug --tag urgent
    python cali_todo.py list                               # pending only (default)
    python cali_todo.py list --all                         # everything
    python cali_todo.py list --status done                 # filter
    python cali_todo.py done <id-prefix>                   # mark done
    python cali_todo.py undone <id-prefix>                 # reopen
    python cali_todo.py remove <id-prefix>                 # delete
    python cali_todo.py clear --done                       # remove all done
    python cali_todo.py clear --all                        # remove everything
    python cali_todo.py status                             # counts
    python cali_todo.py --json <subcommand>                # machine-readable

priorities: low | normal | high (default normal)
statuses: pending | done | cancelled
ids: uuid4, any unique prefix matches

exit codes:
    0 - success
    1 - id-prefix matched 0 or 2+ tasks
    2 - bad arguments
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

STORE = Path(os.environ.get("CALI_TODO_PATH") or (Path(__file__).parent / "cali_todo.json"))
PRIORITIES = ("low", "normal", "high")
STATUSES = ("pending", "done", "cancelled")


def _load():
    if not STORE.exists():
        return {"version": 1, "tasks": []}
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "tasks": []}


def _save(data):
    tmp = STORE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(STORE)


def _match_id(data, prefix):
    if not prefix:
        return None
    matches = [t for t in data["tasks"] if t["id"].startswith(prefix)]
    return matches[0] if len(matches) == 1 else None


def _format(task):
    marker = {"pending": "[ ]", "done": "[x]", "cancelled": "[-]"}.get(task["status"], "[?]")
    pri = {"low": " ", "normal": " ", "high": "!"}.get(task["priority"], " ")
    tags = (" " + " ".join(f"#{t}" for t in task.get("tags", []))) if task.get("tags") else ""
    return f"{marker} {pri} {task['id'][:8]}  {task['text']}{tags}"


def cmd_add(args, json_out):
    data = _load()
    task = {
        "id": str(uuid.uuid4()),
        "text": args.text,
        "status": "pending",
        "priority": args.priority,
        "created_at": datetime.now(UTC).isoformat(),
        "completed_at": None,
        "tags": list(args.tag or []),
        "notes": None,
    }
    data["tasks"].append(task)
    _save(data)
    if json_out:
        print(json.dumps(task, ensure_ascii=False))
    else:
        print(f"added {task['id'][:8]}: {task['text']}")
    return 0


def cmd_list(args, json_out):
    data = _load()
    tasks = data["tasks"]
    if args.status:
        tasks = [t for t in tasks if t["status"] == args.status]
    elif not args.all:
        tasks = [t for t in tasks if t["status"] == "pending"]
    pri_order = {"high": 0, "normal": 1, "low": 2}
    tasks = sorted(tasks, key=lambda t: (pri_order.get(t["priority"], 1), t["created_at"]))
    if json_out:
        print(json.dumps(tasks, ensure_ascii=False, indent=2))
        return 0
    if not tasks:
        print("(no tasks)")
        return 0
    for t in tasks:
        print(_format(t))
    return 0


def _update_status(args, json_out, new_status):
    data = _load()
    task = _match_id(data, args.id_prefix)
    if not task:
        print(f"FATAL: id-prefix {args.id_prefix!r} matched 0 or 2+ tasks", file=sys.stderr)
        return 1
    task["status"] = new_status
    task["completed_at"] = datetime.now(UTC).isoformat() if new_status == "done" else None
    _save(data)
    if json_out:
        print(json.dumps(task, ensure_ascii=False))
    else:
        verb = {"done": "done", "pending": "reopened", "cancelled": "cancelled"}[new_status]
        print(f"{verb} {task['id'][:8]}: {task['text']}")
    return 0


def cmd_done(args, json_out):    return _update_status(args, json_out, "done")
def cmd_undone(args, json_out):  return _update_status(args, json_out, "pending")


def cmd_remove(args, json_out):
    data = _load()
    task = _match_id(data, args.id_prefix)
    if not task:
        print(f"FATAL: id-prefix {args.id_prefix!r} matched 0 or 2+ tasks", file=sys.stderr)
        return 1
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task["id"]]
    _save(data)
    if json_out:
        print(json.dumps({"removed": task["id"]}, ensure_ascii=False))
    else:
        print(f"removed {task['id'][:8]}: {task['text']}")
    return 0


def cmd_clear(args, json_out):
    data = _load()
    if args.done:
        before = len(data["tasks"])
        data["tasks"] = [t for t in data["tasks"] if t["status"] != "done"]
        msg = f"cleared {before - len(data['tasks'])} done task(s)"
    elif args.all:
        before = len(data["tasks"])
        data["tasks"] = []
        msg = f"cleared all {before} task(s)"
    else:
        print("FATAL: --done or --all required", file=sys.stderr)
        return 2
    _save(data)
    print(json.dumps({"message": msg}, ensure_ascii=False) if json_out else msg)
    return 0


def cmd_status(args, json_out):
    data = _load()
    counts = {"pending": 0, "done": 0, "cancelled": 0}
    for t in data["tasks"]:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    total = sum(counts.values())
    if json_out:
        print(json.dumps({"total": total, **counts}))
    else:
        print(f"cali_todo: {total} total ({counts['pending']} pending, {counts['done']} done, {counts['cancelled']} cancelled)")
        print(f"  store: {STORE}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add");      p.add_argument("text");  p.add_argument("--priority", default="normal", choices=PRIORITIES);  p.add_argument("--tag", action="append")
    p = sub.add_parser("list");     p.add_argument("--all", action="store_true");  p.add_argument("--status", choices=STATUSES)
    p = sub.add_parser("done");     p.add_argument("id_prefix")
    p = sub.add_parser("undone");   p.add_argument("id_prefix")
    p = sub.add_parser("remove");   p.add_argument("id_prefix")
    p = sub.add_parser("clear");    p.add_argument("--done", action="store_true");  p.add_argument("--all", action="store_true")
    p = sub.add_parser("status")
    args = parser.parse_args()
    handlers = {"add": cmd_add, "list": cmd_list, "done": cmd_done, "undone": cmd_undone, "remove": cmd_remove, "clear": cmd_clear, "status": cmd_status}
    return handlers[args.cmd](args, args.json)


if __name__ == "__main__":
    sys.exit(main())
