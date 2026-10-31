#!/bin/bash
# gap-nerve.sh — signal 6: time delta between messages
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
fi

echo "$NOW" > "$STAMP_FILE"
