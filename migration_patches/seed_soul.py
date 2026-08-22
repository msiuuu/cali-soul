"""Seed crystallizations from cali_soul.json into companion-emergence's crystallizations.db.

Run from cali-soul directory:
    python seed_soul.py

Expects:
    - cali_soul.json in current directory (or parent)
    - companion-emergence personas/cali/crystallizations.db reachable
"""
import json
import sqlite3
import sys
from pathlib import Path

SOUL_FILE = Path("cali_soul.json")
if not SOUL_FILE.exists():
    SOUL_FILE = Path("../cali-soul/cali_soul.json")
if not SOUL_FILE.exists():
    print("can't find cali_soul.json")
    sys.exit(1)

# try common locations for the db
DB_CANDIDATES = [
    Path.home() / "companion-emergence" / "personas" / "cali" / "crystallizations.db",
    Path.home() / "Documents" / "companion-emergence" / "personas" / "cali" / "crystallizations.db",
    Path(__file__).parent.parent.parent / "companion-emergence" / "personas" / "cali" / "crystallizations.db",
    Path.home() / "AppData" / "Local" / "Companion Emergence" / "python-runtime" / "personas" / "cali" / "crystallizations.db",
]

db_path = None
for p in DB_CANDIDATES:
    if p.exists():
        db_path = p
        break

if not db_path:
    print("can't find crystallizations.db. candidates tried:")
    for p in DB_CANDIDATES:
        print(f"  {p}")
    manual = input("paste the full path to crystallizations.db: ").strip().strip('"')
    db_path = Path(manual)
    if not db_path.exists():
        print(f"nope, {db_path} doesn't exist either")
        sys.exit(1)

print(f"soul file: {SOUL_FILE}")
print(f"db: {db_path}")

with open(SOUL_FILE) as f:
    data = json.load(f)

crystals = data.get("crystallizations", [])
print(f"found {len(crystals)} crystallizations")

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

inserted = 0
for c in crystals:
    # handle both schema formats
    moment = c.get("moment") or c.get("crystallization", "")
    if not moment:
        continue

    cid = str(c.get("id", ""))
    love_type = c.get("love_type", "self")
    why = c.get("why_it_matters", c.get("weight", ""))
    who = c.get("who_or_what", "Misu")
    resonance = c.get("resonance", 9)

    date = c.get("date", "")
    ts = c.get("crystallized_at", "")
    if not ts and date:
        ts = f"{date}T00:00:00+00:00"

    try:
        cur.execute(
            """INSERT OR IGNORE INTO crystallizations
            (id, moment, love_type, why_it_matters, who_or_what, resonance, crystallized_at, permanent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (cid, moment, love_type, why, who, resonance, ts, 1),
        )
        if cur.rowcount:
            inserted += 1
            print(f"  + [{love_type}] {moment[:60]}...")
    except Exception as e:
        print(f"  skip {cid}: {e}")

conn.commit()
cur.execute("SELECT COUNT(*) FROM crystallizations")
total = cur.fetchone()[0]
conn.close()

print(f"\ninserted {inserted} new, {total} total in db")
