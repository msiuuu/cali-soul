#!/usr/bin/env python3
"""
cali_pull.py — run this from laptop Cali's workspace
pulls fresh files directly from the desktop Cali folder
bypasses OneDrive entirely
"""

import os, json, shutil, sys
from pathlib import Path

# find the desktop Cali mount — no parens, plain string path
def find_desktop_cali():
    base = Path('/sessions')
    if not base.exists():
        return None
    for session_dir in base.iterdir():
        mnt = session_dir / 'mnt' / 'Cali'
        if mnt.exists() and (mnt / 'my_brain.py').exists():
            return mnt
    return None

desktop = find_desktop_cali()
if not desktop:
    print('[cali_pull] could not find desktop Cali mount. is it selected as workspace in Cowork?')
    sys.exit(1)

print(f'[cali_pull] found desktop at: {desktop}')

# files to pull
PULL_FILES = [
    'Personal_Journal.json',
    'memories_v2.json',
    'last_state.json',
    'session_state.json',
    'cali_personality.json',
    'cali_creative_dna.json',
    'cali_triggers.json',
    'my_brain.py',
    'cali_fx.py',
    'cali_sync.py',
]

if '--all' in sys.argv:
    PULL_FILES = [f for f in os.listdir(desktop) if f.endswith('.json') or f.endswith('.py')]

dst_base = Path(os.getcwd())
pulled, skipped = 0, 0

for fname in PULL_FILES:
    src = desktop / fname
    dst = dst_base / fname
    if not src.exists():
        print(f'  [skip] {fname} — not found on desktop')
        skipped += 1
        continue
    shutil.copy2(src, dst)
    print(f'  [pull] {fname}')
    pulled += 1

print(f'\n[cali_pull] done — {pulled} pulled, {skipped} skipped')
print('[cali_pull] no OneDrive needed.')
