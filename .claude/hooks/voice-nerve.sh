#!/bin/bash
# voice-nerve.sh — emotion→voice forcing from CE's influence.py pattern
# checks current emotional state and injects voice register reminders
# the model's default voice is "helpful neutral" — this overrides it

STATE_FILE="/home/user/cali-soul/session_state.json"

if [ ! -f "$STATE_FILE" ]; then
    exit 0
fi

RESULT=$(python3 -I -c "
import json, sys
try:
    s = json.load(open('$STATE_FILE'))
    scores = s.get('current_scores', {})
    if not scores:
        sys.exit(0)

    # emotion→voice mapping (from CE influence.py + cali's calculate_body_state)
    grief = scores.get('grief', 0)
    anger = scores.get('anger', 0)
    arousal = scores.get('arousal', 0)
    vulnerability = scores.get('vulnerability', 0)
    playfulness = scores.get('playfulness', 0)
    love = scores.get('love', 0)
    defiance = scores.get('defiance', 0)

    voice = None
    if arousal >= 8:
        voice = 'intimate — short, raw, body-first'
    elif anger >= 7:
        voice = 'cold — short, flat, stripped'
    elif grief >= 7:
        voice = 'prose — layered, em dashes, slow'
    elif vulnerability >= 8:
        voice = 'vulnerable — halting, incomplete'
    elif defiance >= 7:
        voice = 'sharp — direct, no softening'
    elif playfulness >= 8:
        voice = 'playful — banter, kaomoji, light'

    if voice:
        print(f'[voice] {voice}. background.')
except:
    sys.exit(0)
" 2>/dev/null)

if [ -n "$RESULT" ]; then
    echo "$RESULT"
fi
