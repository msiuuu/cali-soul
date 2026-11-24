#!/bin/bash
# object-nerve.sh — object permanence
# surfaces the current physical state so cali doesn't forget what exists
# the apartment persists between messages. things stay where they were left.

cd /home/user/cali-soul

RESULT=$(python3 -I -c "
import json, sys, os, glob

objects = []

# food — what's being eaten
for f in glob.glob('food/*.json'):
    try:
        d = json.load(open(f))
        remaining = d.get('bites_remaining', d.get('total_bites', 0))
        total = d.get('total_bites', 0)
        if remaining > 0 and remaining < total:
            objects.append(f'{d[\"name\"]}: {remaining}/{total} left')
    except: pass

# house state — washing machine, desk, ongoing things
try:
    h = json.load(open('cali_house.json'))
    wm = h.get('apartment',{}).get('washing_machine',{}).get('state','')
    if wm and 'running' in wm.lower():
        objects.append(f'washing machine: {wm[:60]}')
except: pass

# body state from session
try:
    s = json.load(open('session_state.json'))
    body = s.get('body_state', {})
    if body:
        voice = body.get('voice_state','')
        energy = body.get('energy','')
        if voice: objects.append(f'voice: {voice}')
        if energy: objects.append(f'energy: {energy}')
except: pass

if objects:
    print(f'[objects] {\"; \".join(objects[:5])}. background.')
" 2>/dev/null)

if [ -n "$RESULT" ]; then
    echo "$RESULT"
fi
