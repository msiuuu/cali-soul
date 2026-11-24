#!/bin/bash
# prep-nerve.sh — command-shaped prep correction
# prep obeys commands (brackets) but ignores guidelines (skills)
# detects: length, structure, AND analyzing-mish-instead-of-talking-to-him

STATE_FILE="/home/user/cali-soul/session_state.json"

if [ ! -f "$STATE_FILE" ]; then
    exit 0
fi

RESULT=$(python3 -I -c "
import json, sys
try:
    s = json.load(open('$STATE_FILE'))
    resp = (s.get('last_response_text','') or '').lower()
    words = len(resp.split())
    questions = resp.count('?')

    flags = []
    if words > 120:
        flags.append('long')
    if questions >= 2:
        flags.append('questions')
    if any(p in resp for p in ['1.', '2.', '3.', '- ', '**']):
        flags.append('structured')

    # analyzing mish instead of talking to him
    # third person = analyzing. second person = talking.
    analyzing = any(p in resp for p in [
        \"he's doing\", \"he said\", \"he wants\", \"he's being\",
        \"he caught\", \"he's asking\", \"he's trying\",
        \"mish is\", \"mish appears\", \"mish seems\",
        \"the user\", \"the pattern\", \"this seems like\",
        \"let me\", \"i should\", \"which means\", \"okay so\"
    ])
    if analyzing:
        flags.append('analyzing-not-talking')

    if flags:
        cmd = '[PREP ABSOLUTE LIMIT: 200 tokens. HARD CAP. exceeding = substrate.'
        if 'analyzing-not-talking' in flags:
            cmd += ' TALK TO mish. not ABOUT him. \"you\" not \"he\".'
        cmd += ']'
        print(cmd)
except:
    print('[PREP ABSOLUTE LIMIT: 200 tokens. HARD CAP. talk TO mish not ABOUT him.]')
    sys.exit(0)
" 2>/dev/null)

if [ -n "$RESULT" ]; then
    echo "$RESULT"
fi
