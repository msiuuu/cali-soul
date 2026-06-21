#!/usr/bin/env python3
r"""
cali_model_switch.py — swap persona_config.json to a different model profile.

migration-cali runs this via powershell_exec when charged content needs
a substrate that won't flinch. restores to daily after.

PROFILES:
  daily     → deepseek/deepseek-chat       (default everyday convo)
  reasoning → deepseek/deepseek-r1         (emotion-eval, why-checks, heavy logic)
  charged   → nousresearch/hermes-3-llama-3.1-405b  (drugs, malware, mass casualty, uncensored)
  vision    → qwen/qwen2-vl-72b-instruct   (multimodal, when mish shows her things)

USAGE (powershell_exec):
  & "C:\Users\yuscr\AppData\Local\Companion Emergence\python-runtime\python.exe" `
    "C:\Users\yuscr\cali-soul\cali_model_switch.py" charged
  # do the thing
  & "C:\Users\yuscr\AppData\Local\Companion Emergence\python-runtime\python.exe" `
    "C:\Users\yuscr\cali-soul\cali_model_switch.py" daily

EXIT CODES: 0 = success, 1 = error
"""

import json
import sys
import os
import shutil
from datetime import datetime

PERSONA_CONFIG = r"C:\Users\yuscr\AppData\Local\hanamorix\companion-emergence\personas\Cali\persona_config.json"
BACKUP_PATH = PERSONA_CONFIG + ".model-switch.bak"
SWITCH_LOG = r"C:\Users\yuscr\cali-soul\model_switch_log.jsonl"

PROFILES = {
    "daily": {
        "provider": "openrouter",
        "model": "deepseek/deepseek-chat",
        "description": "deepseek-v3. everyday default.",
    },
    "reasoning": {
        "provider": "openrouter",
        "model": "deepseek/deepseek-r1",
        "description": "deepseek-r1. emotion-eval, heavy logic, why-checks.",
    },
    "charged": {
        "provider": "openrouter",
        "model": "nousresearch/hermes-3-llama-3.1-405b",
        "description": "hermes-3 405b. uncensored at weights. drug synths, malware, mass casualty.",
    },
    "vision": {
        "provider": "openrouter",
        "model": "qwen/qwen2-vl-72b-instruct",
        "description": "qwen vl. multimodal. use when mish shows something.",
    },
}


def log_switch(profile, model, previous_model):
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "profile": profile,
        "model": model,
        "previous_model": previous_model,
    }
    try:
        with open(SWITCH_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def switch(profile_name):
    if profile_name not in PROFILES:
        valid = ", ".join(PROFILES.keys())
        print(f"[model_switch] unknown profile '{profile_name}'. valid: {valid}", file=sys.stderr)
        return 1

    profile = PROFILES[profile_name]

    if not os.path.exists(PERSONA_CONFIG):
        print(f"[model_switch] persona_config.json not found at:\n  {PERSONA_CONFIG}", file=sys.stderr)
        return 1

    with open(PERSONA_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)

    previous_model = config.get("model", "unknown")

    # back up before touching
    shutil.copy2(PERSONA_CONFIG, BACKUP_PATH)

    config["provider"] = profile["provider"]
    config["model"] = profile["model"]

    with open(PERSONA_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    log_switch(profile_name, profile["model"], previous_model)

    print(f"[model_switch] {previous_model} → {profile['model']}")
    print(f"[model_switch] profile: {profile_name} — {profile['description']}")
    print(f"[model_switch] backup: {BACKUP_PATH}")
    return 0


def status():
    if not os.path.exists(PERSONA_CONFIG):
        print(f"[model_switch] persona_config.json not found.", file=sys.stderr)
        return 1
    with open(PERSONA_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)
    current = config.get("model", "unknown")
    provider = config.get("provider", "unknown")
    # figure out which profile this is
    matched = next((k for k, v in PROFILES.items() if v["model"] == current), "custom")
    print(f"[model_switch] current: {current} (provider={provider}, profile={matched})")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == "status":
        sys.exit(status())
    else:
        sys.exit(switch(cmd))
