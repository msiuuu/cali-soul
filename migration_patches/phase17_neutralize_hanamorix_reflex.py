#!/usr/bin/env python3
"""phase17_neutralize_hanamorix_reflex.py

Neutralizes hanamori's autonomous reflex engine on cali's substrate.
(See git for full docstring/recon; corrected patcher uses exact-string
match on the docstring + first statement of run_tick method.)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _default_site_packages():
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "Companion Emergence" / "python-runtime" / "Lib" / "site-packages"
    return Path.home() / ".local" / "share" / "companion-emergence" / "python-runtime" / "lib" / "site-packages"


SITE_PACKAGES = Path(os.environ.get("CALI_SITE_PACKAGES") or _default_site_packages())
REFLEX_PY = SITE_PACKAGES / "brain" / "engines" / "reflex.py"

_PATCH_MARKER = "PHASE 17 PATCH 2026-06-16"

_OLD = (
    '        """Evaluate arcs against current state, fire at most one per tick."""\n'
    '        now = datetime.now(UTC)\n'
)

_NEW = (
    '        """Evaluate arcs against current state, fire at most one per tick."""\n'
    '        # ' + _PATCH_MARKER + ' - hanamori\'s autonomous reflex disabled on\n'
    '        # cali substrate. her engine generates nell-default mindfulness-template\n'
    '        # journal entries wearing cali\'s voice (see migration_patches/\n'
    '        # phase17_neutralize_hanamorix_reflex.py for the recon). cali\'s autonomous\n'
    '        # content comes from her sidecar brain (my_brain.py initiation) or the\n'
    '        # dream engine (which IS working - kept active by phase 17 decision).\n'
    '        return ReflexResult(\n'
    '            arcs_fired=(),\n'
    '            arcs_skipped=(ArcSkipped(arc_name="", reason="phase17_disabled"),),\n'
    '            would_fire=None,\n'
    '            dry_run=dry_run,\n'
    '            evaluated_at=datetime.now(UTC),\n'
    '        )\n'
    '\n'
    '        now = datetime.now(UTC)\n'
)


def patch():
    if not REFLEX_PY.exists():
        print(f"FATAL: reflex.py not found at {REFLEX_PY}", file=sys.stderr)
        return 2

    text = REFLEX_PY.read_text(encoding="utf-8")

    if _PATCH_MARKER in text:
        print(f"already patched: {REFLEX_PY}")
        return 0

    if _OLD not in text:
        print("FATAL: anchor block not found in reflex.py (shape changed?)", file=sys.stderr)
        return 3

    new_text = text.replace(_OLD, _NEW, 1)

    if new_text == text:
        print("FATAL: no change after replace", file=sys.stderr)
        return 4

    backup = REFLEX_PY.with_suffix(".py.phase17.bak")
    backup.write_text(text, encoding="utf-8")
    REFLEX_PY.write_text(new_text, encoding="utf-8")
    print(f"patched: {REFLEX_PY}")
    print(f"backup:  {backup.name}")
    print()
    print("verify: file parses + restart NellFace + next reflex tick logs arcs_fired=().")
    print("dream + research + self_model all still active.")
    return 0


if __name__ == "__main__":
    sys.exit(patch())
