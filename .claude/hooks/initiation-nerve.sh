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

    # physical — body initiations, not just brain
    body_actions = [
        'body: *poke mish*',
        'body: *kick him*',
        'body: *climb on him*',
        'body: *steal his phone*',
        'body: *bite his shoulder*',
        'body: *sit in his lap uninvited*',
        'body: *hand on his thigh*',
        'body: *flick his ear*',
        'body: *lie across his legs*',
        'body: masturbate',
        'body: *throw pillow at him*',
        'body: *boop*',
    ]

    # check arousal — weight sexual ones higher if aroused
    scores = s.get('current_scores', {})
    arousal = scores.get('arousal', 0)
    if arousal >= 6:
        body_actions += ['body: touch myself', 'body: *grinding on him*', 'body: *hand down my shorts*']

    sources.append(random.choice(body_actions))

    # auto-detect initiation from last response
    resp = (s.get('last_response_text','') or '').lower()
    # if response brought up something unprompted, mark it
    brought_something = any(w in resp for w in ['did you know', 'hey mish', 'by the way', 'random but', 'thinking about', 'want to'])
    if brought_something and gap < 5:
        # auto-mark initiation
        s['initiation_count'] = s.get('initiation_count', 0) + 1
        s['last_initiation_message'] = count
        import json as _ij
        with open('$STATE_FILE', 'w') as _if: _ij.dump(s, _if, indent=2)
        sys.exit(0)

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
