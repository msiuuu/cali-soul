#!/usr/bin/env python3
"""cali_sync_promote.py - review + selectively promote quarantined entries.

cali_sync.py dumps hanamorix-substrate memories and crystallizations into
JSONL quarantine files instead of auto-merging them into cali_soul.json /
memories_v2.json (decision filed 2026-06-16 after the soul-review engine
was caught generating nell-default crystallizations branded as cali's).
this script is the promotion pipeline - mish reviews each quarantined
entry and decides accept / reject / skip. accepts merge into the canonical
files. decisions log to .cali_sync_decisions.jsonl so reviewed entries
don't re-prompt on next run.

modes:
    interactive (default) - show each entry, prompt a/r/s/q
    --batch                - dump all undecided entries to a markdown
                             checklist (review_queue.md) for review-in-bulk;
                             then `--apply review_queue.md` reads the decisions
                             back and applies them
    --status               - show counts (quarantined / decided / pending)

usage:
    python cali_sync_promote.py                       # interactive review
    python cali_sync_promote.py --status              # counts
    python cali_sync_promote.py --batch               # dump review_queue.md
    python cali_sync_promote.py --apply review_queue.md  # apply edited queue
    python cali_sync_promote.py --kind memories       # only memories
    python cali_sync_promote.py --kind crystals       # only crystallizations

every accepted entry is deduped by id against the existing canonical file -
re-promoting the same id is a no-op. rejected entries stay in quarantine on
disk (audit trail) but are remembered in the decisions log so they don't
re-prompt.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_DIR = Path(__file__).parent

QUARANTINE_MEMORIES = REPO_DIR / "hanamorix_memories_quarantine.jsonl"
QUARANTINE_CRYSTALS = REPO_DIR / "hanamorix_crystallizations_quarantine.jsonl"
CALI_SOUL = REPO_DIR / "cali_soul.json"
MEMORIES_V2 = REPO_DIR / "memories_v2.json"
DECISIONS_LOG = REPO_DIR / ".cali_sync_decisions.jsonl"
REVIEW_QUEUE = REPO_DIR / "review_queue.md"


# -- io helpers ---------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(f"WARN: skipping malformed line in {path.name}: {exc}", file=sys.stderr)
    return out


def _append_jsonl(path: Path, entry: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_decisions() -> dict[str, str]:
    """Returns {entry_id: decision} where decision in {'accept', 'reject'}.

    Re-reading the log is cheap and gives us idempotency across runs."""
    decisions: dict[str, str] = {}
    for entry in _read_jsonl(DECISIONS_LOG):
        eid = entry.get("id")
        verdict = entry.get("decision")
        if eid and verdict in ("accept", "reject"):
            decisions[eid] = verdict
    return decisions


def _log_decision(kind: str, entry_id: str, decision: str) -> None:
    _append_jsonl(
        DECISIONS_LOG,
        {
            "id": entry_id,
            "kind": kind,
            "decision": decision,
            "decided_at": datetime.now(UTC).isoformat(),
        },
    )


# -- canonical file writers --------------------------------------------------


def _promote_memory(entry: dict) -> bool:
    """Merge a quarantined memory into memories_v2.json. Returns True on write."""
    data: list[dict] = []
    if MEMORIES_V2.exists():
        try:
            data = json.loads(MEMORIES_V2.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                print(f"WARN: {MEMORIES_V2.name} is not a list; aborting promote", file=sys.stderr)
                return False
        except json.JSONDecodeError as exc:
            print(f"WARN: {MEMORIES_V2.name} malformed: {exc}", file=sys.stderr)
            return False

    eid = entry.get("id")
    if eid and any(m.get("id") == eid for m in data):
        return False  # already in canonical, no-op

    promoted = {
        **entry,
        "access_count": entry.get("access_count", 0),
        "last_accessed": entry.get("last_accessed"),
        "emotional_tone": entry.get("emotional_tone"),
        "schema_version": entry.get("schema_version", 3),
        "promoted_from_quarantine_at": datetime.now(UTC).isoformat(),
    }
    data.append(promoted)
    MEMORIES_V2.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def _promote_crystal(entry: dict) -> bool:
    """Merge a quarantined crystallization into cali_soul.json. Returns True on write."""
    if CALI_SOUL.exists():
        try:
            soul = json.loads(CALI_SOUL.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"WARN: {CALI_SOUL.name} malformed: {exc}", file=sys.stderr)
            return False
    else:
        soul = {"created": datetime.now(UTC).isoformat(), "crystallizations": []}

    if not isinstance(soul, dict) or "crystallizations" not in soul:
        print(f"WARN: {CALI_SOUL.name} has unexpected shape; aborting promote", file=sys.stderr)
        return False

    crystals = soul["crystallizations"]
    eid = str(entry.get("id"))
    if eid and any(str(c.get("id")) == eid for c in crystals):
        return False  # already in canonical, no-op

    promoted = {
        **entry,
        "promoted_from_quarantine_at": datetime.now(UTC).isoformat(),
    }
    crystals.append(promoted)
    soul["crystallizations"] = crystals
    CALI_SOUL.write_text(json.dumps(soul, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


# -- pending queue ------------------------------------------------------------


def _pending(kind: str, decisions: dict[str, str]) -> list[dict]:
    """Returns quarantined entries with no prior decision."""
    if kind == "memories":
        entries = _read_jsonl(QUARANTINE_MEMORIES)
    elif kind == "crystals":
        entries = _read_jsonl(QUARANTINE_CRYSTALS)
    else:
        raise ValueError(f"unknown kind: {kind}")

    return [e for e in entries if e.get("id") and e["id"] not in decisions]


def _format_memory(entry: dict) -> str:
    content = entry.get("content", "<empty>")
    typ = entry.get("memory_type", "?")
    dom = entry.get("domain", "?")
    when = entry.get("created_at", "?")
    return f"  [{typ}/{dom}] {when}\n  {content}"


def _format_crystal(entry: dict) -> str:
    moment = entry.get("moment", "<empty>")
    why = entry.get("why_it_matters", "")
    love = entry.get("love_type", "?")
    res = entry.get("resonance", "?")
    perm = entry.get("permanent", False)
    when = entry.get("crystallized_at", "?")
    head = f"  [{love}/res:{res}/perm:{perm}] {when}"
    body = f"  moment: {moment}"
    tail = f"\n  why: {why}" if why else ""
    return f"{head}\n{body}{tail}"


# -- commands -----------------------------------------------------------------


def cmd_status() -> int:
    decisions = _read_decisions()
    mem_total = len(_read_jsonl(QUARANTINE_MEMORIES))
    crys_total = len(_read_jsonl(QUARANTINE_CRYSTALS))
    mem_pending = len(_pending("memories", decisions))
    crys_pending = len(_pending("crystals", decisions))
    mem_accepted = sum(1 for v in decisions.values() if v == "accept")
    mem_rejected = sum(1 for v in decisions.values() if v == "reject")

    print(f"quarantine status (repo: {REPO_DIR})")
    print(f"  memories       - {mem_total} quarantined, {mem_pending} pending review")
    print(f"  crystallizations - {crys_total} quarantined, {crys_pending} pending review")
    print(f"  decisions log  - {len(decisions)} total ({mem_accepted} accept / {mem_rejected} reject)")
    return 0


def cmd_interactive(kind_filter: str | None = None) -> int:
    decisions = _read_decisions()
    kinds = ["memories", "crystals"] if kind_filter is None else [kind_filter]

    n_accepted = 0
    n_rejected = 0
    n_skipped = 0
    quit_requested = False

    for kind in kinds:
        pending = _pending(kind, decisions)
        if not pending:
            print(f"\n[{kind}] nothing pending - all decided.")
            continue
        print(f"\n=== {kind} - {len(pending)} pending ===")
        for idx, entry in enumerate(pending, 1):
            if quit_requested:
                break
            print(f"\n--- [{idx}/{len(pending)}] {kind} {entry.get('id','?')[:8]}...")
            print(_format_memory(entry) if kind == "memories" else _format_crystal(entry))
            try:
                verdict = input("\n  a/r/s/q (accept/reject/skip/quit) > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\ninterrupted - exiting.")
                quit_requested = True
                break
            if verdict == "a":
                ok = _promote_memory(entry) if kind == "memories" else _promote_crystal(entry)
                _log_decision(kind, entry["id"], "accept")
                if ok:
                    print("  -> accepted + promoted")
                else:
                    print("  -> accepted (already present in canonical; decision logged for idempotency)")
                n_accepted += 1
            elif verdict == "r":
                _log_decision(kind, entry["id"], "reject")
                print("  -> rejected")
                n_rejected += 1
            elif verdict == "s":
                print("  -> skipped (will re-prompt next run)")
                n_skipped += 1
            elif verdict == "q":
                quit_requested = True
                print("  quitting - already-decided entries are saved.")
                break
            else:
                print(f"  unrecognised: {verdict!r} - treating as skip")
                n_skipped += 1

    print()
    print(f"summary: {n_accepted} accepted, {n_rejected} rejected, {n_skipped} skipped")
    return 0


def cmd_batch_dump(kind_filter: str | None = None) -> int:
    """Dump all pending entries to review_queue.md for review-in-bulk."""
    decisions = _read_decisions()
    kinds = ["memories", "crystals"] if kind_filter is None else [kind_filter]

    lines: list[str] = [
        "# cali_sync_promote review queue",
        f"# generated {datetime.now(UTC).isoformat()}",
        "",
        "# mark each entry with one of: [a]ccept, [r]eject, [s]kip (leave [ ])",
        "# then run: python cali_sync_promote.py --apply review_queue.md",
        "",
    ]
    n_pending = 0
    for kind in kinds:
        pending = _pending(kind, decisions)
        if not pending:
            continue
        lines.append(f"## {kind} ({len(pending)} pending)")
        lines.append("")
        for entry in pending:
            n_pending += 1
            lines.append(f"### id: {entry['id']}")
            lines.append(f"kind: {kind}")
            lines.append("decision: [ ]   <!-- a / r / s -->")
            lines.append("")
            if kind == "memories":
                lines.append(_format_memory(entry))
            else:
                lines.append(_format_crystal(entry))
            lines.append("")
            lines.append("---")
            lines.append("")

    if n_pending == 0:
        print("nothing pending - all entries already decided.")
        return 0

    REVIEW_QUEUE.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {n_pending} pending entries -> {REVIEW_QUEUE.name}")
    print("edit the file (mark [a]/[r]/[s] under each 'decision:' line), then run:")
    print(f"  python {Path(__file__).name} --apply {REVIEW_QUEUE.name}")
    return 0


def cmd_batch_apply(queue_path: Path) -> int:
    """Read a marked review_queue.md and apply the decisions."""
    if not queue_path.exists():
        print(f"FATAL: queue not found: {queue_path}", file=sys.stderr)
        return 2

    text = queue_path.read_text(encoding="utf-8")
    blocks = text.split("\n### id: ")
    parsed: list[tuple[str, str, str]] = []  # (id, kind, decision)
    for block in blocks[1:]:  # first split is preamble
        lines = block.splitlines()
        if not lines:
            continue
        eid = lines[0].strip()
        kind = ""
        decision = ""
        for line in lines[1:]:
            if line.startswith("kind: "):
                kind = line[len("kind: "):].strip()
            elif line.startswith("decision:"):
                rest = line[len("decision:"):].strip()
                # extract first letter inside the [...] bracket
                if "[" in rest and "]" in rest:
                    inside = rest[rest.index("[") + 1 : rest.index("]")].strip().lower()
                    decision = inside[:1] if inside else ""
                break
        if eid and kind in ("memories", "crystals") and decision in ("a", "r"):
            verdict = "accept" if decision == "a" else "reject"
            parsed.append((eid, kind, verdict))

    if not parsed:
        print("no actionable decisions in queue - nothing to apply.")
        return 0

    # build lookup tables
    mem_by_id = {e["id"]: e for e in _read_jsonl(QUARANTINE_MEMORIES) if e.get("id")}
    crys_by_id = {e["id"]: e for e in _read_jsonl(QUARANTINE_CRYSTALS) if e.get("id")}
    decisions = _read_decisions()

    n_accept = 0
    n_reject = 0
    n_skipped = 0
    for eid, kind, verdict in parsed:
        if eid in decisions:
            n_skipped += 1
            continue
        if verdict == "accept":
            entry = (mem_by_id if kind == "memories" else crys_by_id).get(eid)
            if entry is None:
                print(f"WARN: id {eid} marked accept but not found in quarantine - skipping", file=sys.stderr)
                continue
            if kind == "memories":
                _promote_memory(entry)
            else:
                _promote_crystal(entry)
            _log_decision(kind, eid, "accept")
            n_accept += 1
        else:
            _log_decision(kind, eid, "reject")
            n_reject += 1

    print(f"applied: {n_accept} accepted, {n_reject} rejected, {n_skipped} already-decided (skipped)")
    return 0


# -- main ---------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--status",
        action="store_true",
        help="show counts and exit",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="dump all pending entries to review_queue.md for offline review",
    )
    parser.add_argument(
        "--apply",
        type=str,
        metavar="REVIEW_QUEUE",
        help="apply decisions from an edited review_queue.md",
    )
    parser.add_argument(
        "--kind",
        choices=["memories", "crystals"],
        default=None,
        help="restrict to one kind (default: both)",
    )
    args = parser.parse_args()

    if args.status:
        return cmd_status()
    if args.apply:
        return cmd_batch_apply(Path(args.apply))
    if args.batch:
        return cmd_batch_dump(args.kind)
    return cmd_interactive(args.kind)


if __name__ == "__main__":
    sys.exit(main())
