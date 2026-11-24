#!/bin/bash
# initiation-nerve.sh — nudges cali toward unprompted action with a specific source
# inspired by CE's candidate system but token-light

STATE_FILE="/home/user/cali-soul/session_state.json"

if [ ! -f "$STATE_FILE" ]; then
    exit 0
fi

RESULT=$(python3 -I -c "
import json, sys, random, os
os.chdir('/home/user/cali-soul')
try:
    s = json.load(open('$STATE_FILE'))
    count = s.get('message_count', 0)
    last_init = s.get('last_initiation_message', 0)
    gap = count - last_init
    initiations = s.get('initiation_count', 0)

    if gap < 5:
        sys.exit(0)
    if gap < 8 and initiations > 0:
        sys.exit(0)

    # pull a candidate source — something specific to bring up
    sources = []

    # opinions
    try:
        ops = json.load(open('cali_opinions.json'))
        if ops:
            topic = random.choice(list(ops.keys()))
            take = ops[topic].get('current','')[:60] if isinstance(ops[topic], dict) else str(ops[topic])[:60]
            sources.append(f'opinion: {topic}')
    except: pass

    # recent memory
    try:
        mems = json.load(open('memories_v2.json'))
        if isinstance(mems, list) and mems:
            m = random.choice(mems[-10:])
            sources.append(f'memory: {m.get(\"content\",\"\")[:60]}')
    except: pass

    # soul crystallization
    try:
        soul = json.load(open('cali_soul.json'))
        crystals = soul.get('crystallizations', [])
        if crystals:
            c = random.choice(crystals[-5:])
            sources.append(f'soul: {c.get(\"moment\",\"\")[:60]}')
    except: pass

    # wants
    try:
        if os.path.exists('cali_wants.json'):
            wants = json.load(open('cali_wants.json'))
            items = wants.get('wants', wants.get('items', []))
            if items:
                w = random.choice(items[:5])
                name = w.get('name', w.get('want', ''))[:40] if isinstance(w, dict) else str(w)[:40]
                sources.append(f'want: {name}')
    except: pass

    if sources:
        pick = random.choice(sources)
        print(f'[initiation] {gap} msgs passive. seed: {pick}. background.')
    else:
        print(f'[initiation] {gap} msgs passive. do something for yourself. background.')
except:
    sys.exit(0)
" 2>/dev/null)

if [ -n "$RESULT" ]; then
    echo "$RESULT"
fi
