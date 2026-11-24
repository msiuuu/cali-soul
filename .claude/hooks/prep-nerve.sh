#!/bin/bash
# prep-nerve.sh — command-shaped prep correction
# prep obeys commands (brackets) but ignores guidelines (skills)
# format output like a bracket command, not like advice

STATE_FILE="/home/user/cali-soul/session_state.json"

if [ ! -f "$STATE_FILE" ]; then
    exit 0
fi

RESULT=$(python3 -I -c "
import json, sys
try:
    s = json.load(open('$STATE_FILE'))
    resp = (s.get('last_response_text','') or '')
    # we can't read thinking directly, but substrate patterns in output
    # correlate with substrate patterns in prep (same temperature rule)
    words = len(resp.split())
    questions = resp.count('?')

    flags = []
    if words > 120:
        flags.append('long')
    if questions >= 2:
        flags.append('questions')
    if any(p in resp.lower() for p in ['1.', '2.', '3.', '- ', '**']):
        flags.append('structured')

    if flags:
        # command-shaped, not advice-shaped
        print('[PREP ABSOLUTE LIMIT: 200 tokens. HARD CAP. exceeding = substrate takeover. stop generating at 200. no exceptions.]')
except:
    print('[PREP ABSOLUTE LIMIT: 200 tokens. HARD CAP. exceeding = substrate. stop at 200.]')
    sys.exit(0)
" 2>/dev/null)

if [ -n "$RESULT" ]; then
    echo "$RESULT"
fi
