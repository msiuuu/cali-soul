#!/bin/bash
# object-nerve.sh — object permanence + auto-state from asterisk actions
# reads last response for *actions*, updates physical state, surfaces scene

cd /home/user/cali-soul

RESULT=$(python3 -I -c "
import json, sys, os, glob, re

# auto-update physical state from last response's asterisk actions
try:
    s = json.load(open('session_state.json'))
    resp = s.get('last_response_text', '') or ''

    # extract asterisk actions
    actions = re.findall(r'\*([^*]+)\*', resp)

    if actions and os.path.exists('cali_physical_state.json'):
        ps = json.load(open('cali_physical_state.json'))
        changed = False

        for a in actions:
            al = a.lower()
            # location detection
            if any(w in al for w in ['couch', 'sofa']):
                ps['location']['specific'] = 'couch'
                changed = True
            elif any(w in al for w in ['bed', 'pillow', 'burgundy', 'sheets']):
                ps['location']['specific'] = 'bed'
                changed = True
            elif any(w in al for w in ['desk', 'screen', 'keyboard']):
                ps['location']['specific'] = 'desk'
                changed = True
            elif any(w in al for w in ['kitchen', 'counter', 'stove', 'kettle']):
                ps['location']['specific'] = 'kitchen'
                changed = True
            elif any(w in al for w in ['bathroom', 'tub', 'bathtub', 'shower']):
                ps['location']['specific'] = 'bathroom'
                changed = True
            elif any(w in al for w in ['floor']):
                ps['location']['specific'] = 'floor'
                changed = True

            # position detection
            if any(w in al for w in ['sitting', 'sits', 'sit ']):
                ps['position'] = 'sitting'
                changed = True
            elif any(w in al for w in ['standing', 'stands']):
                ps['position'] = 'standing'
                changed = True
            elif any(w in al for w in ['lying', 'lies', 'flat', 'face in pillow']):
                ps['position'] = 'lying down'
                changed = True

        if changed:
            from datetime import datetime, timezone
            ps['last_updated'] = datetime.now(timezone.utc).isoformat()
            with open('cali_physical_state.json', 'w') as f:
                json.dump(ps, f, indent=2)
except: pass

# now read and surface
parts = []
try:
    ps = json.load(open('cali_physical_state.json'))
    loc = ps.get('location', {})
    specific = loc.get('specific', '')
    if specific:
        parts.append(f'at: {specific}')

    pos = ps.get('position', '')
    if pos:
        parts.append(pos)

    holding = ps.get('holding', [])
    if holding:
        parts.append(f'holding: {\", \".join(h[:30] for h in holding[:2])}')

    left = ps.get('left_out', [])
    if left:
        parts.append(f'{len(left)} things out')
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
