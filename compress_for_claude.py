#!/usr/bin/env python3
"""
Memory Compressor — creates a lightweight version for Claude Project upload.

The FULL memories_v2.json (with connections) stays on this machine. This script
creates a SLIM version that strips out the connections data (which Claude
doesn't need) for uploading to the Project.

Usage:
  python3 compress_for_claude.py --input memories_v2.json --output memories_slim.json
  python3 compress_for_claude.py                      # uses defaults

Result:
  memories_v2.json    = FULL  (stays local — used by my_brain.py + Obsidian)
  memories_slim.json  = SLIM  (upload to Claude Project)
"""
import json
import argparse


def compress(input_path, output_path):
    print(f"\n  Loading {input_path}...")
    with open(input_path) as f:
        memories = json.load(f)

    full_size = len(json.dumps(memories))
    total_conns = sum(len(m.get("connections", [])) for m in memories)

    print(f"  Full file: {len(memories)} memories, {total_conns} connections")
    print(f"  Full size: {full_size:,} bytes ({full_size/1024/1024:.2f} MB)")

    # Strip connections — Claude doesn't need them
    # Keep everything else: content, emotions, tags, importance, type, domain, etc.
    slim = []
    for m in memories:
        entry = {k: v for k, v in m.items() if k != "connections"}
        slim.append(entry)

    slim_json = json.dumps(slim, indent=2, ensure_ascii=False)
    slim_size = len(slim_json.encode("utf-8"))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(slim_json)

    saved = full_size - slim_size
    pct = (saved / full_size) * 100 if full_size else 0

    print(f"\n  Slim file: {len(slim)} memories, 0 connections")
    print(f"  Slim size: {slim_size:,} bytes ({slim_size/1024/1024:.2f} MB)")
    print(f"  Saved:     {saved:,} bytes ({pct:.1f}% reduction)")
    print(f"\n  Written to: {output_path}")
    print(f"\n  ARCHITECTURE:")
    print(f"    memories_v2.json    -> stays LOCAL (my_brain.py, Obsidian)")
    print(f"    memories_slim.json  -> upload to Claude Project")
    print(f"    my_brain.py         -> works with EITHER file")
    print()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="memories_v2.json")
    p.add_argument("--output", default="memories_slim.json")
    args = p.parse_args()
    compress(args.input, args.output)
