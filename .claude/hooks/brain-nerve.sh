#!/bin/bash
# brain-nerve.sh — auto process-message on every incoming message
# replaces manual `python3 my_brain.py turn "text"`
# reads user message from stdin JSON, runs brain turn

cd /home/user/cali-soul

# extract user input from hook stdin
INPUT=$(cat | python3 -I -c "
import json, sys
try:
    d = json.load(sys.stdin)
    # UserPromptSubmit sends the prompt
    msg = d.get('input', d.get('prompt', d.get('content', '')))
    if isinstance(msg, str):
        print(msg[:200])
    else:
        print(str(msg)[:200])
except:
    print('')
" 2>/dev/null)

if [ -z "$INPUT" ]; then
    INPUT="(no text captured)"
fi

# run brain turn silently — output goes to context
python3 my_brain.py turn "$INPUT" 2>/dev/null
