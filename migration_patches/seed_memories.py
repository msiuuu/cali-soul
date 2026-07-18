"""Seed memories from memories_v2.json into companion-emergence's memories.db.

Run from cali-soul directory:
    python seed_memories.py
"""
import json
import sqlite3
import sys
from pathlib import Path

MEM_FILE = Path("memories_v2.json")
if not MEM_FILE.exists():
    MEM_FILE = Path("../cali-soul/memories_v2.json")
if not MEM_FILE.exists():
    print("can't find memories_v2.json")
    sys.exit(1)

DB_CANDIDATES = [
    Path.home() / "companion-emergence" / "personas" / "cali" / "memories.db",
    Path.home() / "Documents" / "companion-emergence" / "personas" / "cali" / "memories.db",
    Path(__file__).parent.parent.parent / "companion-emergence" / "personas" / "cali" / "memories.db",
    Path.home() / "AppData" / "Local" / "Companion Emergence" / "python-runtime" / "personas" / "cali" / "memories.db",
]

db_path = None
for p in DB_CANDIDATES:
    if p.exists():
        db_path = p
        break

if not db_path:
    print("can't find memories.db. candidates tried:")
    for p in DB_CANDIDATES:
        print(f"  {p}")
    manual = input("paste the full path to memories.db: ").strip().strip('"')
    db_path = Path(manual)
    if not db_path.exists():
        print(f"nope, {db_path} doesn't exist either")
        sys.exit(1)

print(f"memories file: {MEM_FILE}")
print(f"db: {db_path}")

with open(MEM_FILE) as f:
    data = json.load(f)

mems = data if isinstance(data, list) else data.get("memories", data.get("entries", []))
print(f"found {len(mems)} memories")

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

inserted = 0
for m in mems:
    mid = m.get("id", "")
    content = m.get("content", "")
    if not mid or not content:
        continue

    mtype = m.get("memory_type", "event")
    domain = m.get("domain", "relationship")
    emotions = m.get("emotions", {})
    tags = m.get("tags", [])
    importance = m.get("importance", 5)
    score = m.get("emotion_score", m.get("intensity", 0))
    created = m.get("created_at", "")
    active = 1 if m.get("active", True) else 0
    peak = float(max(emotions.values())) if emotions else 0.0

    try:
        cur.execute(
            """INSERT OR IGNORE INTO memories
            (id, content, memory_type, domain, emotions_json, tags_json,
             importance, score, created_at, active, peak_emotion_intensity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (mid, content, mtype, domain,
             json.dumps(emotions), json.dumps(tags),
             float(importance), float(score), created, active, peak),
        )
        if cur.rowcount:
            inserted += 1
            print(f"  + [{domain}] {content[:60]}...")
    except Exception as e:
        print(f"  skip {mid[:12]}: {e}")

conn.commit()
cur.execute("SELECT COUNT(*) FROM memories")
total = cur.fetchone()[0]
conn.close()

print(f"\ninserted {inserted} new, {total} total in db")
