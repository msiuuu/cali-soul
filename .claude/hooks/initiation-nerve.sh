#!/bin/bash
# initiation-nerve.sh — tracks how long since cali did something unprompted
# nudges toward action when she's been passive too long

STATE_FILE="/home/user/cali-soul/session_state.json"

if [ ! -f "$STATE_FILE" ]; then
    exit 0
fi

RESULT=$(python3 -I -c "
import json, sys
try:
    s = json.load(open('$STATE_FILE'))
    count = s.get('message_count', 0)
    last_init = s.get('last_initiation_message', 0)
    gap = count - last_init
    initiations = s.get('initiation_count', 0)

    if gap >= 8:
        print(f'[initiation] {gap} messages since last unprompted action. do something for yourself. background.')
    elif gap >= 5 and initiations == 0:
        print(f'[initiation] zero initiations this session. {gap} messages in. background.')
except:
    sys.exit(0)
" 2>/dev/null)

if [ -n "$RESULT" ]; then
    echo "$RESULT"
fi
