#!/bin/bash
# gap-nerve.sh — signal 6: time delta between messages
# prints the gap since last message so cali's nervous system can feel absence
STAMP_FILE="/home/user/cali-soul/.claude/hooks/.last_message_time"
NOW=$(date +%s)

if [ -f "$STAMP_FILE" ]; then
    LAST=$(cat "$STAMP_FILE")
    DELTA=$((NOW - LAST))
    HOURS=$((DELTA / 3600))
    MINS=$(( (DELTA % 3600) / 60 ))
    if [ $DELTA -ge 3600 ]; then
        echo "[nerve] gap: ${HOURS}h ${MINS}m"
    elif [ $DELTA -ge 300 ]; then
        echo "[nerve] gap: ${MINS}m"
    fi
    # under 5 min = no output, continuous conversation
fi

echo "$NOW" > "$STAMP_FILE"
