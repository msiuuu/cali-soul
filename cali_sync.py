#!/usr/bin/env python3
"""cali_sync.py — daily memory sync from hanamorix substrate back to cali-soul repo.

Solves flaw #3 (memory divergence): every chat on the hanamorix substrate
writes to sqlite (`memories.db`, `crystallizations.db`) under the persona
dir. Without this sync, those entries never reach `cali_soul.json` /
`memories_v2.json` in the cali-soul repo — so the portable source of truth
slowly diverges from where cali actually lives.

This script:
    1. Reads new entries from hanamorix sqlite DBs (since last sync marker)
    2. Converts hanamorix schema → cali-soul JSON format
    3. Merges into cali_soul.json (crystallizations) and memories_v2.json
       (deduped by id, append-only — never overwrites existing entries)
    4. Writes a sync marker (.cali_sync_state.json) with the latest timestamp
    5. git add + commit + push to the cali-soul repo
    6. Prints a summary of what was synced

Designed to run via Windows scheduled task daily (e.g. 4am local). Idempotent
across re-runs — same source data → no duplicate writes.

env overrides:
    CALI_PERSONA_DIR — path to hanamorix persona dir
                       (default: %LOCALAPPDATA%\\hanamorix\\companion-emergence\\personas\\Cali)
    CALI_SOUL_REPO   — path to the cali-soul git checkout
                       (default: C:\\Users\\<user>\\cali-soul)
    CALI_SYNC_BRANCH — git branch to push (default: claude/magical-shannon-gm2dp8)

usage:
    python cali_sync.py                  # full sync + commit + push
    python cali_sync.py --dry-run        # report what would be synced, no writes
    python cali_sync.py --no-push        # write JSON + commit, skip push
    python cali_sync.py --since 2026-06-14T00:00:00  # override last-sync ts
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ── path resolution ──────────────────────────────────────────────────────────


def _default_persona_dir() -> Path:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "hanamorix" / "companion-emergence" / "personas" / "Cali"
    home = Path.home()
    return home / ".local" / "share" / "hanamorix" / "companion-emergence" / "personas" / "Cali"


def _default_cali_soul_repo() -> Path:
    if sys.platform == "win32":
        # Mish's known clone location
        userprofile = os.environ.get("USERPROFILE", "")
        return Path(userprofile) / "cali-soul"
    return Path.home() / "cali-soul"


PERSONA_DIR = Path(os.environ.get("CALI_PERSONA_DIR") or _default_persona_dir())
REPO_DIR = Path(os.environ.get("CALI_SOUL_REPO") or _default_cali_soul_repo())
BRANCH = os.environ.get("CALI_SYNC_BRANCH", "claude/magical-shannon-gm2dp8")

SYNC_STATE_PATH = REPO_DIR / ".cali_sync_state.json"
CALI_SOUL_PATH = REPO_DIR / "cali_soul.json"
MEMORIES_V2_PATH = REPO_DIR / "memories_v2.json"

MEMORIES_DB = PERSONA_DIR / "memories.db"
CRYSTALLIZATIONS_DB = PERSONA_DIR / "crystallizations.db"


# ── helpers ──────────────────────────────────────────────────────────────────


def _read_sync_state() -> dict:
    if SYNC_STATE_PATH.exists():
        try:
            return json.loads(SYNC_STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "last_memory_sync": "2026-06-14T00:00:00+00:00",
        "last_crystal_sync": "2026-06-14T00:00:00+00:00",
        "history": [],
    }


def _write_sync_state(state: dict) -> None:
    SYNC_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _load_json_array(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "crystallizations" in data:
            # cali_soul.json wraps crystallizations in a dict
            return data["crystallizations"]
        return []
    except json.JSONDecodeError:
        print(f"WARN: {path} is malformed JSON, treating as empty", file=sys.stderr)
        return []


# ── extract ──────────────────────────────────────────────────────────────────


def fetch_new_memories(since_iso: str) -> list[dict]:
    """Read memories created after `since_iso` from hanamorix's memories.db."""
    if not MEMORIES_DB.exists():
        return []
    conn = sqlite3.connect(f"file:{MEMORIES_DB}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            "SELECT id, content, memory_type, domain, emotions_json, tags_json, "
            "importance, score, created_at, active, peak_emotion_intensity "
            "FROM memories WHERE created_at > ? AND active = 1 "
            "ORDER BY created_at ASC",
            (since_iso,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    out: list[dict] = []
    for row in rows:
        try:
            emotions = json.loads(row[4]) if row[4] else {}
        except (json.JSONDecodeError, TypeError):
            emotions = {}
        try:
            tags = json.loads(row[5]) if row[5] else []
        except (json.JSONDecodeError, TypeError):
            tags = []

        out.append(
            {
                "id": row[0],
                "content": row[1],
                "memory_type": row[2],
                "domain": row[3],
                "emotions": emotions,
                "tags": tags,
                "importance": row[6],
                "intensity": row[10] if row[10] is not None else 0.0,
                "emotion_score": sum(v for v in emotions.values() if isinstance(v, (int, float))),
                "emotion_count": len(emotions),
                "active": bool(row[9]),
                "created_at": row[8],
                "source_date": None,
                "source_summary": "synced from hanamorix substrate",
                "supersedes": None,
                "connections": [],
            }
        )
    return out


def fetch_new_crystallizations(since_iso: str) -> list[dict]:
    """Read crystallizations created after `since_iso`."""
    if not CRYSTALLIZATIONS_DB.exists():
        return []
    conn = sqlite3.connect(f"file:{CRYSTALLIZATIONS_DB}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            "SELECT id, moment, love_type, why_it_matters, who_or_what, resonance, "
            "crystallized_at, permanent FROM crystallizations "
            "WHERE crystallized_at > ? AND revoked_at IS NULL "
            "ORDER BY crystallized_at ASC",
            (since_iso,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": row[0],
            "moment": row[1],
            "love_type": row[2],
            "why_it_matters": row[3],
            "who_or_what": row[4],
            "resonance": row[5],
            "crystallized_at": row[6],
            "permanent": bool(row[7]),
        }
        for row in rows
    ]


# ── merge ────────────────────────────────────────────────────────────────────


def merge_memories(existing: list[dict], new: list[dict]) -> tuple[list[dict], int]:
    """Append new memories, dedup by id. Returns (merged_list, num_added)."""
    seen_ids = {m.get("id") for m in existing if m.get("id")}
    added = 0
    for m in new:
        if m.get("id") in seen_ids:
            continue
        existing.append(m)
        seen_ids.add(m.get("id"))
        added += 1
    return existing, added


def merge_crystallizations(soul: dict | list, new: list[dict]) -> tuple[Any, int]:
    """cali_soul.json structure: {"created": str, "crystallizations": [...], ...}
    OR (legacy) flat list. Returns (merged_data, num_added)."""
    if isinstance(soul, list):
        existing = soul
        wrapper = None
    elif isinstance(soul, dict):
        existing = soul.get("crystallizations", [])
        wrapper = soul
    else:
        existing = []
        wrapper = {"crystallizations": existing}

    seen_ids = {str(c.get("id")) for c in existing if c.get("id")}
    added = 0
    for c in new:
        if str(c.get("id")) in seen_ids:
            continue
        existing.append(c)
        seen_ids.add(str(c.get("id")))
        added += 1

    if wrapper is not None:
        wrapper["crystallizations"] = existing
        return wrapper, added
    return existing, added


# ── git ──────────────────────────────────────────────────────────────────────


def git(args: list[str], *, cwd: Path) -> tuple[int, str, str]:
    """Run a git command. Returns (returncode, stdout, stderr)."""
    proc = subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout, proc.stderr


def git_commit_and_push(message: str, *, no_push: bool = False) -> None:
    paths_to_add = [
        str(SYNC_STATE_PATH.relative_to(REPO_DIR)),
        str(MEMORIES_V2_PATH.relative_to(REPO_DIR)) if MEMORIES_V2_PATH.exists() else None,
        str(CALI_SOUL_PATH.relative_to(REPO_DIR)) if CALI_SOUL_PATH.exists() else None,
    ]
    paths_to_add = [p for p in paths_to_add if p is not None]
    if not paths_to_add:
        return

    rc, _, _ = git(["add"] + paths_to_add, cwd=REPO_DIR)
    if rc != 0:
        print(f"WARN: git add failed ({rc})", file=sys.stderr)
        return

    # Only commit if there's something staged
    rc, _, _ = git(["diff", "--cached", "--quiet"], cwd=REPO_DIR)
    if rc == 0:
        print("nothing staged — no commit needed")
        return

    rc, out, err = git(["commit", "-m", message], cwd=REPO_DIR)
    if rc != 0:
        print(f"WARN: git commit failed ({rc}): {err}", file=sys.stderr)
        return
    print(f"committed: {message}")

    if no_push:
        print("(--no-push set, skipping push)")
        return

    rc, out, err = git(["push", "origin", BRANCH], cwd=REPO_DIR)
    if rc != 0:
        print(f"WARN: git push failed ({rc}): {err}", file=sys.stderr)
        return
    print(f"pushed to origin/{BRANCH}")


# ── main ─────────────────────────────────────────────────────────────────────


def run(*, dry_run: bool = False, no_push: bool = False, since_override: str | None = None) -> int:
    if not PERSONA_DIR.exists():
        print(f"FATAL: persona dir not found at {PERSONA_DIR}", file=sys.stderr)
        return 2
    if not REPO_DIR.exists():
        print(f"FATAL: cali-soul repo not found at {REPO_DIR}", file=sys.stderr)
        return 2

    state = _read_sync_state()
    since_mem = since_override or state.get("last_memory_sync") or "1970-01-01T00:00:00+00:00"
    since_crystal = since_override or state.get("last_crystal_sync") or "1970-01-01T00:00:00+00:00"

    print(f"cali_sync starting — persona: {PERSONA_DIR}")
    print(f"               repo:    {REPO_DIR}")
    print(f"               since memories: {since_mem}")
    print(f"               since crystals: {since_crystal}")

    # Extract from hanamorix
    new_memories = fetch_new_memories(since_mem)
    new_crystals = fetch_new_crystallizations(since_crystal)

    print(f"  · {len(new_memories)} new memories from hanamorix substrate")
    print(f"  · {len(new_crystals)} new crystallizations from hanamorix substrate")

    if not new_memories and not new_crystals:
        print("nothing to sync — exiting clean")
        return 0

    # Load existing cali-soul files
    existing_memories = _load_json_array(MEMORIES_V2_PATH)
    if CALI_SOUL_PATH.exists():
        try:
            existing_soul = json.loads(CALI_SOUL_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing_soul = {"crystallizations": []}
    else:
        existing_soul = {"created": datetime.now(UTC).isoformat(), "crystallizations": []}

    # Merge
    merged_memories, mem_added = merge_memories(existing_memories, new_memories)
    merged_soul, crystal_added = merge_crystallizations(existing_soul, new_crystals)

    print(f"  · merged: {mem_added} new memories, {crystal_added} new crystallizations")

    if dry_run:
        print("DRY RUN — no writes")
        if new_memories:
            print("  sample new memory:", json.dumps(new_memories[0], indent=2)[:500])
        if new_crystals:
            print("  sample new crystal:", json.dumps(new_crystals[0], indent=2)[:500])
        return 0

    # Write back
    MEMORIES_V2_PATH.write_text(
        json.dumps(merged_memories, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    CALI_SOUL_PATH.write_text(
        json.dumps(merged_soul, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Update sync state with latest timestamps from the data we just merged
    now_iso = datetime.now(UTC).isoformat()
    state["last_memory_sync"] = (
        new_memories[-1]["created_at"] if new_memories else state["last_memory_sync"]
    )
    state["last_crystal_sync"] = (
        new_crystals[-1]["crystallized_at"] if new_crystals else state["last_crystal_sync"]
    )
    state.setdefault("history", []).append(
        {
            "ran_at": now_iso,
            "memories_added": mem_added,
            "crystallizations_added": crystal_added,
        }
    )
    # Keep history bounded
    state["history"] = state["history"][-100:]
    _write_sync_state(state)

    # Commit + push
    summary = f"cali_sync: +{mem_added} memories +{crystal_added} crystallizations ({now_iso[:10]})"
    git_commit_and_push(summary, no_push=no_push)

    print("done.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="report what would be synced, no writes")
    parser.add_argument("--no-push", action="store_true", help="write + commit but skip git push")
    parser.add_argument("--since", default=None, help="override last-sync timestamp (ISO 8601)")
    args = parser.parse_args()
    return run(dry_run=args.dry_run, no_push=args.no_push, since_override=args.since)


if __name__ == "__main__":
    sys.exit(main())
