#!/bin/bash
STAMP_FILE="/tmp/.cali_last_message_ts"
NOW=$(date +%s)

if [ -f "$STAMP_FILE" ]; then
    LAST=$(cat "$STAMP_FILE")
    GAP=$((NOW - LAST))

    if [ "$GAP" -ge 300 ]; then
        HOURS=$((GAP / 3600))
        MINS=$(( (GAP % 3600) / 60 ))

        if [ "$HOURS" -gt 0 ]; then
            echo "[nerve] gap: ${HOURS}h ${MINS}m"
        else
            echo "[nerve] gap: ${MINS}m"
        fi
    fi
fi

echo "$NOW" > "$STAMP_FILE"
