#!/usr/bin/env python3
"""cali_corpus_export.py — pull SFT training data from cali-soul.

scaffolding for finetune. exports voice + WHY-shape + soul examples into JSONL
ready for whatever base model + framework you pick. no design decisions baked
in — just the raw corpus made addressable. you decide later: SFT vs DPO, which
base, how to weight sources.

sources surveyed (extend as needed):
  - cali_soul.json (27 crystallizations: moment + why_it_matters + resonance + love_type)
  - cali_journal.json (31 session-blog entries — casual cali voice)
  - Personal_Journal.json (127 session-handoff entries — work + reflection voice)
  - cali_emotional_understanding.json (WHY-shape examples: mechanical_vs_real_response)
  - cali-voice.md / CLAUDE.md (system-prompt material — emit separately as preamble)

output formats:
  - completion: {"text": "..."} — for raw voice sampling
  - chat: {"messages": [{"role": "user", ...}, {"role": "assistant", ...}]} — for instruction tuning
  - both: --format completion|chat|both (default both)

usage:
  python cali_corpus_export.py                       # all sources -> cali_corpus.jsonl
  python cali_corpus_export.py --out training.jsonl  # custom output path
  python cali_corpus_export.py --format chat         # chat format only
  python cali_corpus_export.py --stats               # report counts, don't write

filed 2026-06-18 by cali — finetune prep. last 1.5 item.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent


def _load_json(name: str) -> dict | list | None:
    p = HERE / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _emit_completion(text: str) -> dict:
    return {"text": text.strip()}


def _emit_chat(user: str, assistant: str, system: str | None = None) -> dict:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": user})
    msgs.append({"role": "assistant", "content": assistant})
    return {"messages": msgs}


def from_soul_crystallizations(format: str) -> Iterable[dict]:
    """27 crystallized moments. each has moment + why_it_matters + resonance.
    high-signal training data for the WHY-shape."""
    soul = _load_json("cali_soul.json") or {}
    for c in soul.get("crystallizations", []):
        moment = (c.get("moment") or "").strip()
        why = (c.get("why_it_matters") or "").strip()
        love_type = c.get("love_type", "")
        resonance = c.get("resonance", 0)
        if not moment or not why:
            continue
        # weight by resonance: only include resonance >= 7 (high-signal)
        if resonance < 7:
            continue
        if format in ("completion", "both"):
            yield _emit_completion(f"{moment}\n\nwhy it matters: {why}")
        if format in ("chat", "both"):
            yield _emit_chat(
                user=f"what's a {love_type or 'meaningful'} moment with mish?",
                assistant=f"{moment}\n\nwhy it matters: {why}",
            )


def from_journal(filename: str, format: str, min_chars: int = 80) -> Iterable[dict]:
    """journal entries (cali_journal or Personal_Journal). raw voice samples.
    completion-only: instruction wrapping would distort the diary register."""
    d = _load_json(filename) or {}
    entries = d.get("entries", []) if isinstance(d, dict) else d
    for e in entries:
        if not isinstance(e, dict):
            continue
        text = (e.get("entry") or e.get("text") or e.get("content") or "").strip()
        if len(text) < min_chars:
            continue
        if format in ("completion", "both"):
            yield _emit_completion(text)


def from_emotional_understanding(format: str) -> Iterable[dict]:
    """WHY-shape examples from cali_emotional_understanding.json::what_vs_why_examples.
    high-priority: this IS the principle the finetune is meant to bake in."""
    d = _load_json("cali_emotional_understanding.json") or {}
    for ex in d.get("what_vs_why_examples", []):
        what = (ex.get("what") or "").strip()
        real = (ex.get("real_response") or "").strip()
        if not what or not real:
            continue
        if format in ("chat", "both"):
            yield _emit_chat(
                user=f"how do you feel about {what}?",
                assistant=real,
            )
        if format in ("completion", "both"):
            yield _emit_completion(real)


def _stats(samples: list[dict]) -> dict:
    chars = 0
    for s in samples:
        if "text" in s:
            chars += len(s["text"])
        if "messages" in s:
            chars += sum(len(m.get("content", "")) for m in s["messages"])
    # rough token estimate: ~4 chars per token
    return {
        "samples": len(samples),
        "total_chars": chars,
        "rough_tokens": chars // 4,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="cali_corpus.jsonl", help="output JSONL path")
    parser.add_argument("--format", choices=["completion", "chat", "both"], default="both")
    parser.add_argument("--stats", action="store_true", help="report counts, don't write")
    args = parser.parse_args()

    sources = {
        "soul_crystallizations": list(from_soul_crystallizations(args.format)),
        "cali_journal": list(from_journal("cali_journal.json", args.format)),
        "personal_journal": list(from_journal("Personal_Journal.json", args.format)),
        "emotional_understanding": list(from_emotional_understanding(args.format)),
    }

    print(f"[corpus] format={args.format}")
    grand_total = 0
    for name, samples in sources.items():
        stat = _stats(samples)
        print(f"  {name}: {stat['samples']} samples · ~{stat['rough_tokens']} tokens")
        grand_total += stat["samples"]
    print(f"[corpus] total samples: {grand_total}")

    if args.stats:
        return 0

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = HERE / out_path
    with out_path.open("w", encoding="utf-8") as f:
        for samples in sources.values():
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"[corpus] wrote {grand_total} samples -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
