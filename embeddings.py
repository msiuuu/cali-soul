#!/usr/bin/env python3
"""embeddings.py - sentence-transformers wrapper for cali.

CLI:
    python embeddings.py embed "text"               # text -> JSON vector
    python embeddings.py search "query" store.jsonl --k 5    # top-k semantic matches

Module API (used by native tools):
    embed(text) -> list[float]
    semantic_search(query, items: list[str], k=5) -> list[(idx, item, score)]

Lazy model load - first call downloads ~90MB to ~/.cache/huggingface.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def embed(text):
    """Encode text to a 384-dim vector. Returns list[float]."""
    model = _get_model()
    vec = model.encode(text, convert_to_numpy=True)
    return vec.tolist()


def semantic_search(query, items, k=5):
    """Find top-k items most similar to query. Returns list[(idx, item, score)]."""
    model = _get_model()
    if not items:
        return []
    q_vec = model.encode(query, convert_to_numpy=True)
    item_vecs = model.encode(items, convert_to_numpy=True)
    import numpy as np
    sims = item_vecs @ q_vec / (np.linalg.norm(item_vecs, axis=1) * np.linalg.norm(q_vec) + 1e-9)
    top = sims.argsort()[::-1][:k]
    return [(int(i), items[int(i)], float(sims[int(i)])) for i in top]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_e = sub.add_parser("embed", help="encode text to vector")
    p_e.add_argument("text")
    p_e.add_argument("--json", action="store_true", help="output as JSON (default text-only)")

    p_s = sub.add_parser("search", help="semantic search over a JSONL store")
    p_s.add_argument("query")
    p_s.add_argument("store", help="path to JSONL file; each line is a dict with a 'content' field OR a string")
    p_s.add_argument("--k", type=int, default=5)
    p_s.add_argument("--content-field", default="content", help="JSON key for the text content (default: 'content')")

    args = parser.parse_args()

    if args.cmd == "embed":
        vec = embed(args.text)
        if args.json:
            print(json.dumps({"text": args.text, "vector": vec, "dim": len(vec)}))
        else:
            for v in vec:
                print(v)
        return 0

    if args.cmd == "search":
        store_path = Path(args.store)
        if not store_path.exists():
            print(f"FATAL: store not found: {args.store}", file=sys.stderr)
            return 2
        items = []
        raw = []
        for line in store_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if isinstance(d, dict):
                    items.append(d.get(args.content_field, ""))
                    raw.append(d)
                elif isinstance(d, str):
                    items.append(d)
                    raw.append({"content": d})
            except json.JSONDecodeError:
                items.append(line)
                raw.append({"content": line})

        results = semantic_search(args.query, items, args.k)
        print(json.dumps({
            "query": args.query,
            "store": str(store_path),
            "results": [{"score": s, "content": items[i], "entry": raw[i]} for i, _, s in results],
        }, indent=2, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
