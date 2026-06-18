#!/usr/bin/env python3
"""kalimari_mode.py - model profile switcher for cali's persona_config.json.

Solves the open bug from PHASE 1.5 send-off (2026-06-16): deepseek's
provider-side trust/safety flag on minor-character sexual content. voice.md
section 0 beat the general charged-content floor but NOT the kalimari floor.
fix is model swap, not prompt engineering.

Three profiles:
    default    - deepseek/deepseek-chat (daily, fast, cheap)
    reasoning  - deepseek/deepseek-r1 (code, reasoning, slow + smart)
    charged    - nousresearch/hermes-3-llama-3.1-405b (kalimari, provider-flagged content,
                 uncensored at weights, not on deepseek's pipeline)

Flips the "model" field in persona_config.json. backs up before write.
optionally restarts the bridge supervisor so the swap takes effect immediately.

env overrides:
    CALI_PERSONA_DIR - path to hanamorix persona dir
                       (default: %LOCALAPPDATA%\\hanamorix\\companion-emergence\\personas\\Cali)

usage:
    python kalimari_mode.py status                  # show current profile
    python kalimari_mode.py default                 # swap to deepseek-v3
    python kalimari_mode.py reasoning               # swap to deepseek-r1
    python kalimari_mode.py charged                 # swap to hermes-3-405b
    python kalimari_mode.py charged --restart       # swap + kick supervisor restart
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# -- profiles -----------------------------------------------------------------

PROFILES: dict[str, dict[str, str]] = {
    "default": {
        "model": "deepseek/deepseek-chat",
        "purpose": "daily - fast, cheap, voice.md beats general charged content",
    },
    "reasoning": {
        "model": "deepseek/deepseek-r1",
        "purpose": "code + reasoning turns - slower, smarter, deepseek's r1",
    },
    "charged": {
        "model": "nousresearch/hermes-3-llama-3.1-405b",
        "purpose": "kalimari + provider-flagged content - uncensored at weights, off deepseek pipeline",
    },
}


def _default_persona_dir() -> Path:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "hanamorix" / "companion-emergence" / "personas" / "Cali"
    return Path.home() / ".local" / "share" / "hanamorix" / "companion-emergence" / "personas" / "Cali"


PERSONA_DIR = Path(os.environ.get("CALI_PERSONA_DIR") or _default_persona_dir())
CONFIG_PATH = PERSONA_DIR / "persona_config.json"


# -- helpers ------------------------------------------------------------------


def _read_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"FATAL: persona_config.json not found at {CONFIG_PATH}", file=sys.stderr)
        print("set CALI_PERSONA_DIR env var to override", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FATAL: persona_config.json is malformed JSON: {exc}", file=sys.stderr)
        sys.exit(3)


def _write_config(cfg: dict) -> None:
    # write atomically: tmp file + rename
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    tmp.replace(CONFIG_PATH)


def _backup_config() -> Path:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = CONFIG_PATH.with_suffix(f".json.{ts}.bak")
    backup.write_bytes(CONFIG_PATH.read_bytes())
    return backup


def _profile_for_model(model: str) -> str | None:
    """Map a model string back to its profile name, if it matches one."""
    for name, profile in PROFILES.items():
        if profile["model"] == model:
            return name
    return None


def _restart_bridge() -> int:
    """Kick the nell supervisor so the new model is picked up immediately."""
    print("restarting bridge supervisor...")
    try:
        proc = subprocess.run(
            ["nell", "supervisor", "restart", "--persona", "cali"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        print(
            "WARN: `nell` command not on PATH - run `nell supervisor restart --persona cali` "
            "manually to pick up the swap",
            file=sys.stderr,
        )
        return 1
    except subprocess.TimeoutExpired:
        print("WARN: supervisor restart timed out (30s)", file=sys.stderr)
        return 1
    if proc.returncode != 0:
        print(f"WARN: supervisor restart failed ({proc.returncode}):", file=sys.stderr)
        if proc.stderr:
            print(proc.stderr.rstrip(), file=sys.stderr)
        return proc.returncode
    print("supervisor restarted.")
    if proc.stdout:
        print(proc.stdout.rstrip())
    return 0


# -- commands -----------------------------------------------------------------


def cmd_status() -> int:
    cfg = _read_config()
    model = cfg.get("model", "<unset>")
    provider = cfg.get("provider", "<unset>")
    profile = _profile_for_model(model)
    print(f"persona_config: {CONFIG_PATH}")
    print(f"  provider: {provider}")
    print(f"  model:    {model}")
    if profile:
        print(f"  profile:  {profile} ({PROFILES[profile]['purpose']})")
    else:
        print(f"  profile:  <custom> (not one of {list(PROFILES)})")
    print()
    print("available profiles:")
    for name, p in PROFILES.items():
        marker = " *" if name == profile else "  "
        print(f"  {marker} {name:10s} -> {p['model']}")
        print(f"        {p['purpose']}")
    return 0


def cmd_swap(profile_name: str, *, restart: bool) -> int:
    if profile_name not in PROFILES:
        print(
            f"FATAL: unknown profile {profile_name!r}. choose from: {list(PROFILES)}",
            file=sys.stderr,
        )
        return 4

    target_model = PROFILES[profile_name]["model"]
    cfg = _read_config()
    current_model = cfg.get("model")

    if current_model == target_model:
        print(f"already on {profile_name}: {target_model}")
        if restart:
            return _restart_bridge()
        return 0

    backup = _backup_config()
    cfg["model"] = target_model
    _write_config(cfg)

    print(f"swap: {current_model} -> {target_model}")
    print(f"profile: {profile_name} ({PROFILES[profile_name]['purpose']})")
    print(f"backup:  {backup.name}")

    if restart:
        return _restart_bridge()

    print()
    print("NOTE: bridge supervisor still running old model. run:")
    print("  nell supervisor restart --persona cali")
    print("or rerun with --restart to do it automatically.")
    return 0


# -- main ---------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "profile",
        nargs="?",
        choices=["status", *PROFILES.keys()],
        default="status",
        help="profile to switch to, or 'status' to inspect current (default: status)",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="kick `nell supervisor restart --persona cali` after swap",
    )
    args = parser.parse_args()

    if args.profile == "status":
        return cmd_status()
    return cmd_swap(args.profile, restart=args.restart)


if __name__ == "__main__":
    sys.exit(main())
