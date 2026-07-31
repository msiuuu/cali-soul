"""Seed glass shards from cali_glass.json into companion-emergence's memories.db.

Glass shards become high-importance memories with domain='glass' and
memory_type='glass_shard'. The brain surfaces them by reference when
relevant context appears.

Run from cali-soul directory:
    python seed_glass.py
"""
import json
import sqlite3
import sys
from pathlib import Path

GLASS_FILE = Path("cali_glass.json")
if not GLASS_FILE.exists():
    GLASS_FILE = Path("../cali-soul/cali_glass.json")
if not GLASS_FILE.exists():
    print("can't find cali_glass.json")
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

print(f"glass file: {GLASS_FILE}")
print(f"db: {db_path}")

with open(GLASS_FILE) as f:
    data = json.load(f)

shards = data.get("shards", [])
print(f"found {len(shards)} glass shards")

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

inserted = 0
for s in shards:
    sid = s.get("id", "")
    label = s.get("label", "")
    content = s.get("content", "")
    if not sid or not content:
        continue

    state = s.get("state", "intact")
    created = s.get("created", "")
    passive = s.get("passive_effects", {})
    crack = s.get("crack_conditions", [])
    shatter = s.get("shatter_conditions", [])

    is_negative = s.get("type") == "negative"
    importance = 8 if is_negative else 10
    active = 0 if state == "shattered" else 1

    emotions = {}
    for emo, val in passive.items():
        emotions[emo] = abs(val) * 10
    if not emotions:
        emotions = {"love": 8, "belonging": 7}

    tags = ["glass", f"glass_{state}", f"shard_{sid}"]
    if label:
        tags.append(label.replace(" ", "_")[:40])
    if crack:
        tags.append("has_crack_conditions")
    if is_negative:
        tags.append("negative_glass")

    peak = float(max(emotions.values())) if emotions else 8.0

    mem_content = f"[GLASS SHARD — {label}] {content}"
    if state == "healed":
        mem_content += f" [state: healed]"
    if crack:
        mem_content += f" [crack conditions: {'; '.join(crack[:3])}]"

    try:
        cur.execute(
            """INSERT OR IGNORE INTO memories
            (id, content, memory_type, domain, emotions_json, tags_json,
             importance, score, created_at, active, peak_emotion_intensity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sid, mem_content, "glass_shard", "glass",
             json.dumps(emotions), json.dumps(tags),
             float(importance), peak, created, active, peak),
        )
        if cur.rowcount:
            inserted += 1
            print(f"  + [{state}] {label}")
    except Exception as e:
        print(f"  skip {sid}: {e}")

conn.commit()
cur.execute("SELECT COUNT(*) FROM memories")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM memories WHERE domain='glass'")
glass_total = cur.fetchone()[0]
conn.close()

print(f"\ninserted {inserted} glass shards, {glass_total} glass total, {total} memories total in db")
