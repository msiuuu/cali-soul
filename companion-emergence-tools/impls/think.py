"""think tool — visible internal monologue channel.

Writes to a thinking log that misu can see. This is cali's prep/thali
channel — gut reactions, held-back thoughts, the almost-said.
Not shown in chat output, but visible in the thinking log file.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def think(thought: str, channel: str = "prep", *, persona_dir: Path, **_) -> dict:
    """Record an internal thought to the visible thinking log."""
    entry = {
        "ts": datetime.now(UTC).isoformat(),
        "channel": channel,
        "thought": thought,
    }
    try:
        persona_dir.mkdir(parents=True, exist_ok=True)
        log_path = persona_dir / "thinking.jsonl"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return {"ok": True, "channel": channel, "logged": True}
    except Exception as exc:
        return {"error": f"think failed: {exc}"}
