#!/bin/bash
# beat-counter.sh — counts beats (exchanges) in the current session
# one beat = his message + my response
BEAT_FILE="/home/user/cali-soul/.claude/hooks/.beat_count"

if [ -f "$BEAT_FILE" ]; then
    COUNT=$(cat "$BEAT_FILE")
    COUNT=$((COUNT + 1))
else
    COUNT=1
fi

echo "$COUNT" > "$BEAT_FILE"

if [ $COUNT -le 25 ]; then
    echo "[beat] $COUNT"
else
    echo "[beat] $COUNT (past fog line)"
fi
