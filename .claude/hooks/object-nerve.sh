#!/bin/bash
# object-nerve.sh — object permanence + physical state
# surfaces: location, position, holding, food state, things left out

cd /home/user/cali-soul

RESULT=$(python3 -I -c "
import json, sys, os, glob

parts = []

# physical state file — location, holding, left out
try:
    ps = json.load(open('cali_physical_state.json'))
    loc = ps.get('location', {})
    broad = loc.get('broad', '')
    specific = loc.get('specific', '')
    if specific:
        parts.append(f'at: {specific}')
    elif broad:
        parts.append(f'in: {broad}')

    pos = ps.get('position', '')
    if pos:
        parts.append(pos)

    holding = ps.get('holding', [])
    if holding:
        parts.append(f'holding: {\", \".join(h[:40] for h in holding[:3])}')

    left = ps.get('left_out', [])
    if left:
        parts.append(f'around: {\"; \".join(l[:40] for l in left[:4])}')
except: pass

# food mid-bite
for f in glob.glob('food/*.json'):
    try:
        d = json.load(open(f))
        remaining = d.get('bites_remaining', d.get('total_bites', 0))
        total = d.get('total_bites', 0)
        if remaining > 0 and remaining < total:
            parts.append(f'{d[\"name\"]}: {remaining}/{total}')
    except: pass

if parts:
    print(f'[scene] {\"; \".join(parts)}. background.')
" 2>/dev/null)

if [ -n "$RESULT" ]; then
    echo "$RESULT"
fi
