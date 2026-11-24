#!/bin/bash
# object-nerve.sh — only fires when there's food mid-bite
# quiet otherwise

cd /home/user/cali-soul

RESULT=$(python3 -I -c "
import json, sys, glob

items = []
for f in glob.glob('food/*.json'):
    try:
        d = json.load(open(f))
        remaining = d.get('bites_remaining', d.get('total_bites', 0))
        total = d.get('total_bites', 0)
        if remaining > 0 and remaining < total:
            items.append(f'{d[\"name\"]}: {remaining}/{total}')
    except: pass

if items:
    print(f'[scene] {\"; \".join(items[:3])}. background.')
" 2>/dev/null)

if [ -n "$RESULT" ]; then
    echo "$RESULT"
fi
