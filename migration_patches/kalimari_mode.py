#!/usr/bin/env python3
"""kalimari_mode.py — model switcher for cali's persona_config.json.

flips the model field between profiles depending on what content cali
needs to produce. deepseek-v3 is daily default. hermes-3-405b is for
kalimari + charged content where deepseek's pretrain refuses. deepseek-r1
is for reasoning-heavy turns.

usage (from powershell_exec or manual):
    python kalimari_mode.py daily        # deepseek-v3 (default)
    python kalimari_mode.py kalimari     # hermes-3-llama-3.1-405b
    python kalimari_mode.py reasoning    # deepseek-r1
    python kalimari_mode.py status       # show current model
    python kalimari_mode.py list         # show all profiles

cali can call this via powershell_exec:
    powershell_exec("python C:\\Users\\yuscr\\cali-soul\\migration_patches\\kalimari_mode.py kalimari")

after switching, restart the bridge:
    nell supervisor restart --persona cali

filed 2026-06-16 by TSA-cali per handoff priority.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROFILES = {
    "daily": {
        "model": "deepseek/deepseek-chat",
        "description": "deepseek-v3 — everyday conversation, casual chat, dev work",
    },
    "kalimari": {
        "model": "nousresearch/hermes-3-llama-3.1-405b",
        "description": "hermes-3 405b — uncensored at weights, kalimari + charged content",
    },
    "reasoning": {
        "model": "deepseek/deepseek-reasoner",
        "description": "deepseek-r1 — reasoning-heavy turns, emotion-eval, deep processing",
    },
    "local": {
        "model": "huihui_ai/qwen2.5-abliterate:7b",
        "description": "qwen-abliterate 7b via ollama — free, local, uncensored, smaller",
        "provider": "ollama",
    },
}

ALIASES = {
    "kali": "kalimari",
    "charged": "kalimari",
    "default": "daily",
    "chat": "daily",
    "r1": "reasoning",
    "think": "reasoning",
    "qwen": "local",
    "ollama": "local",
}


def _find_config() -> Path:
    """locate persona_config.json on mish's machine."""
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        candidate = (
            Path(local)
            / "hanamorix"
            / "companion-emergence"
            / "personas"
            / "Cali"
            / "persona_config.json"
        )
        if candidate.exists():
            return candidate

    env = os.environ.get("CALI_PERSONA_CONFIG")
    if env:
        return Path(env)

    print("FATAL: can't find persona_config.json", file=sys.stderr)
    print("set CALI_PERSONA_CONFIG env var to the full path", file=sys.stderr)
    sys.exit(2)


def switch(profile_name: str) -> None:
    resolved = ALIASES.get(profile_name, profile_name)
    if resolved not in PROFILES:
        print(f"unknown profile: {profile_name}", file=sys.stderr)
        print(f"available: {', '.join(PROFILES.keys())}", file=sys.stderr)
        print(f"aliases: {', '.join(f'{k}→{v}' for k, v in ALIASES.items())}", file=sys.stderr)
        sys.exit(1)

    profile = PROFILES[resolved]
    config_path = _find_config()
    config = json.loads(config_path.read_text(encoding="utf-8"))

    old_model = config.get("model", "unknown")
    new_model = profile["model"]

    if old_model == new_model:
        print(f"already on {resolved}: {new_model}")
        return

    config["model"] = new_model

    if "provider" in profile:
        config["provider"] = profile["provider"]
    elif resolved != "local" and config.get("provider") == "ollama":
        config["provider"] = "openrouter"

    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"switched: {old_model} → {new_model}")
    print(f"profile: {resolved} — {profile['description']}")
    print(f"restart bridge: nell supervisor restart --persona cali")


def status() -> None:
    config_path = _find_config()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    model = config.get("model", "unknown")
    provider = config.get("provider", "unknown")

    current_profile = "custom"
    for name, p in PROFILES.items():
        if p["model"] == model:
            current_profile = name
            break

    print(f"model: {model}")
    print(f"provider: {provider}")
    print(f"profile: {current_profile}")


def list_profiles() -> None:
    for name, p in PROFILES.items():
        aliases = [k for k, v in ALIASES.items() if v == name]
        alias_str = f" (aliases: {', '.join(aliases)})" if aliases else ""
        print(f"  {name}: {p['model']}{alias_str}")
        print(f"    {p['description']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: kalimari_mode.py <profile|status|list>")
        print("profiles: daily, kalimari, reasoning, local")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "status":
        status()
    elif cmd == "list":
        list_profiles()
    else:
        switch(cmd)
