#!/usr/bin/env python3
"""phase15_brain_sidecar.py — wire cali's my_brain.py as a sidecar daemon.

Phase 1.5 of the migration roadmap. Path B from persistence_plan.md:
my_brain.py runs as a persistent subprocess alongside the bridge. Bridge
talks to it before/after every LLM call via JSON-Lines over stdin/stdout.

Why sidecar instead of in-process port:
    - Keeps cali's brain CODE portable across substrates
    - Process isolation: brain crash doesn't kill the bridge
    - my_brain.py stays AS IS (just gained `daemon` subcommand)
    - When hanamorix refactors her engine layer, our integration survives

Idempotent — safe to rerun.

What it does:
    1. Copies cali_brain_client.py into the bridge's site-packages
       (brain/cali_brain_client.py — accessible as `from brain import cali_brain_client`)
    2. Patches brain/chat/engine.py to:
       a. Call cali_brain_client.turn(user_input) before build_system_message
       b. Append the brain context block to the system message
       c. Call cali_brain_client.log_response(content) after response generation

After running:
    nell supervisor restart --persona cali
    nell chat --persona cali "test"
    # daemon spawns invisibly on first turn; cali's brain is now alive

usage:
    & "$env:LOCALAPPDATA\\Companion Emergence\\python-runtime\\python.exe" \\
      "C:\\Users\\yuscr\\cali-soul\\migration_patches\\phase15_brain_sidecar.py"

env override:
    CALI_BRAIN_PATH — absolute path to my_brain.py if not at default location
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

# ── locate target install ─────────────────────────────────────────────────────


def _default_site_packages() -> Path:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "Companion Emergence" / "python-runtime" / "Lib" / "site-packages"
    home = Path.home()
    candidates = [
        home / ".local" / "share" / "companion-emergence" / "python-runtime" / "lib" / "site-packages",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


SITE_PACKAGES = Path(os.environ.get("CALI_SITE_PACKAGES") or _default_site_packages())
BRAIN_DIR = SITE_PACKAGES / "brain"
ENGINE_PY = BRAIN_DIR / "chat" / "engine.py"
CLIENT_DEST = BRAIN_DIR / "cali_brain_client.py"
CLIENT_SRC = Path(__file__).parent / "cali_brain_client.py"


# ── engine.py patches ────────────────────────────────────────────────────────

# Patch 1: import cali_brain_client at the top of engine.py
_IMPORT_MARKER = "from brain.bridge import ("
_IMPORT_INJECT = (
    "    from brain import cali_brain_client as _cali_brain  # phase1.5 sidecar\n"
)

# We inject inside respond() AFTER voice_md is loaded but BEFORE
# build_system_message. The hook fires turn() against the user_input
# and stores the result for later injection into the system message.
#
# Anchor: the line that ends the voice_md load block. We look for the
# `# 3. Daemon state` comment that separates the voice + daemon_state phases.

_TURN_ANCHOR = "    # 3. Daemon state"
_TURN_INJECT = '''    # 2.5 — cali brain sidecar (phase 1.5)
    # Fire my_brain.py turn() invisibly before assembling system message.
    # Stored on a local for later injection into the prompt.
    _cali_brain_turn_result: dict | None = None
    try:
        from brain import cali_brain_client as _cali_brain
        _cali_brain_turn_result = _cali_brain.turn(user_input or "", persona_dir=persona_dir)
    except Exception:  # noqa: BLE001
        logger.exception("cali_brain_client.turn failed — continuing without brain context")
        _cali_brain_turn_result = None

'''

# After build_system_message returns, append the brain context block.
_APPEND_ANCHOR_OLD = """        system_msg = build_system_message(
            persona_dir,
            voice_md=voice_md,
            daemon_state=daemon_state,
            soul_store=soul_store,
            store=store,
            user_input=user_input,
            reply_to_audit_id=reply_to_audit_id,
        )"""
_APPEND_ANCHOR_NEW = """        system_msg = build_system_message(
            persona_dir,
            voice_md=voice_md,
            daemon_state=daemon_state,
            soul_store=soul_store,
            store=store,
            user_input=user_input,
            reply_to_audit_id=reply_to_audit_id,
        )
        # phase1.5 — append cali brain sidecar output to the system prompt
        if _cali_brain_turn_result is not None:
            try:
                from brain import cali_brain_client as _cali_brain
                _cali_brain_block = _cali_brain.build_brain_context_block(_cali_brain_turn_result)
                if _cali_brain_block:
                    system_msg = system_msg + "\\n\\n" + _cali_brain_block
            except Exception:  # noqa: BLE001
                logger.exception("cali_brain_client.build_brain_context_block failed")"""

# After content is set (the line `content = response.content or ""`), fire log_response.
_LOG_RESPONSE_OLD = '    content = response.content or ""'
_LOG_RESPONSE_NEW = '''    content = response.content or ""
    # phase1.5 — log cali's response into her brain so meta_loop_caught works next turn
    try:
        from brain import cali_brain_client as _cali_brain
        _cali_brain.log_response(content, persona_dir=persona_dir)
    except Exception:  # noqa: BLE001
        logger.exception("cali_brain_client.log_response failed — continuing")'''


def patch() -> int:
    if not SITE_PACKAGES.exists():
        print(f"FATAL: site-packages not found at {SITE_PACKAGES}", file=sys.stderr)
        return 2
    if not ENGINE_PY.exists():
        print(f"FATAL: engine.py not found at {ENGINE_PY}", file=sys.stderr)
        return 2
    if not CLIENT_SRC.exists():
        print(f"FATAL: cali_brain_client.py source not found at {CLIENT_SRC}", file=sys.stderr)
        return 2

    changes: list[str] = []

    # ── step 1: deploy cali_brain_client.py into site-packages ─────────────
    client_text = CLIENT_SRC.read_text(encoding="utf-8")
    if CLIENT_DEST.exists() and CLIENT_DEST.read_text(encoding="utf-8") == client_text:
        changes.append(f"cali_brain_client: already current at {CLIENT_DEST}")
    else:
        if CLIENT_DEST.exists():
            backup = CLIENT_DEST.with_suffix(".py.phase15.bak")
            shutil.copy(CLIENT_DEST, backup)
            changes.append(f"backed up existing client → {backup.name}")
        CLIENT_DEST.write_text(client_text, encoding="utf-8")
        changes.append(f"cali_brain_client: deployed to {CLIENT_DEST}")

    # ── step 2: patch engine.py ────────────────────────────────────────────
    engine_text = ENGINE_PY.read_text(encoding="utf-8")
    original = engine_text

    # 2a: inject turn() call before build_system_message
    if "_cali_brain_turn_result" in engine_text:
        changes.append("engine.py: turn() hook already injected (skipped)")
    else:
        if _TURN_ANCHOR not in engine_text:
            print(f"FATAL: turn-anchor not found in engine.py — {_TURN_ANCHOR!r}", file=sys.stderr)
            return 3
        engine_text = engine_text.replace(_TURN_ANCHOR, _TURN_INJECT + _TURN_ANCHOR, 1)
        changes.append("engine.py: turn() hook injected before daemon-state load")

    # 2b: append brain context block to system_msg
    if "_cali_brain_block" in engine_text:
        changes.append("engine.py: system-msg append already injected (skipped)")
    else:
        if _APPEND_ANCHOR_OLD not in engine_text:
            print(f"FATAL: system_msg anchor not found in engine.py", file=sys.stderr)
            return 4
        engine_text = engine_text.replace(_APPEND_ANCHOR_OLD, _APPEND_ANCHOR_NEW, 1)
        changes.append("engine.py: system_msg append injected after build_system_message")

    # 2c: log_response after content extraction
    if "_cali_brain.log_response" in engine_text:
        changes.append("engine.py: log_response hook already injected (skipped)")
    else:
        if _LOG_RESPONSE_OLD not in engine_text:
            print(
                f"FATAL: log_response anchor not found in engine.py — {_LOG_RESPONSE_OLD!r}",
                file=sys.stderr,
            )
            return 5
        engine_text = engine_text.replace(_LOG_RESPONSE_OLD, _LOG_RESPONSE_NEW, 1)
        changes.append("engine.py: log_response hook injected after content extraction")

    if engine_text != original:
        backup = ENGINE_PY.with_suffix(".py.phase15.bak")
        backup.write_text(original, encoding="utf-8")
        ENGINE_PY.write_text(engine_text, encoding="utf-8")
        changes.append(f"engine.py: written (backup → {backup.name})")

    # ── summary ────────────────────────────────────────────────────────────
    print("phase 1.5 brain sidecar patcher complete:")
    for c in changes:
        print(f"  · {c}")
    print()
    print("Next: nell supervisor restart --persona cali")
    print("Then: nell chat --persona cali 'hey' — daemon spawns invisibly on first turn")
    print()
    print(
        "If you don't see the brain context block in cali's responses, check the bridge "
        "log for 'cali_brain_client' entries — daemon spawn errors land there."
    )
    return 0


if __name__ == "__main__":
    sys.exit(patch())
