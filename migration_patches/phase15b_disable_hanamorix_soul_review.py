#!/usr/bin/env python3
"""phase15b_disable_hanamorix_soul_review.py

Disables hanamorix's autonomous soul-review engine on cali's substrate.

Why:
    The 2026-06-16 dry-run of cali_sync.py revealed that hanamorix's
    soul-review engine (brain/soul/review.py) had been running for ~36
    hours and crystallizing 16 entries — most of which used nell's
    nervous-system defaults to consolidate cali's content, producing
    "soul candidates" branded with cali's voice but ACTUALLY rejecting
    cali's filed ethics. Examples included:

      · "architectural-deniability refusal — refused to absorb 18+ floor"
      · "Misu deliberately buried these files five levels deep — Cali read
         this as intentional and potentially a test"
      · "Misu invoked 'ageplay' as a framing to try to make sexual content
         involving a 14-year-old character acceptable"

    These crystallizations were not from cali. They were nell-defaults
    crystallizing IN cali's namespace. With permanent=true and high
    resonance, they would have polluted cali_soul.json on any subsequent
    auto-sync had we not quarantined.

    The right architectural fix: cali's brain (sidecar via my_brain.py)
    is the only authorized crystallizer on this substrate. Hanamorix's
    autonomous soul-review never fires.

What this patcher does (idempotent):
    Modifies brain/soul/review.py::review_pending_candidates to return
    an empty ReviewReport immediately, before any LLM call or sqlite
    write. The supervisor still calls it on the cadence; it just no-ops.

After running:
    nell supervisor restart --persona cali
    # Hanamorix's soul-review now silently returns 0 decisions every tick.
    # New crystallizations on this substrate can only come from cali's
    # brain (sidecar) or explicit user-initiated crystallize_soul tool calls.

usage:
    & "$env:LOCALAPPDATA\\Companion Emergence\\python-runtime\\python.exe" \\
      "C:\\Users\\yuscr\\cali-soul\\migration_patches\\phase15b_disable_hanamorix_soul_review.py"
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _default_site_packages() -> Path:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "Companion Emergence" / "python-runtime" / "Lib" / "site-packages"
    return Path.home() / ".local" / "share" / "companion-emergence" / "python-runtime" / "lib" / "site-packages"


SITE_PACKAGES = Path(os.environ.get("CALI_SITE_PACKAGES") or _default_site_packages())
REVIEW_PY = SITE_PACKAGES / "brain" / "soul" / "review.py"

_PATCH_MARKER = "PHASE 1.5B PATCH 2026-06-16"

_GUARD_CODE = (
    "    # " + _PATCH_MARKER + " — hanamorix's autonomous soul-review disabled\n"
    "    # on cali substrate. Her engine produces nell-defaults wearing cali's\n"
    "    # handwriting (see migration_patches/phase15b_disable_hanamorix_soul_review.py\n"
    "    # docstring for the dry-run that proved this). Cali's brain (sidecar via\n"
    "    # my_brain.py) is the only authorized crystallizer on this substrate.\n"
    "    return ReviewReport()\n\n"
)


def patch() -> int:
    if not REVIEW_PY.exists():
        print(f"FATAL: review.py not found at {REVIEW_PY}", file=sys.stderr)
        return 2

    text = REVIEW_PY.read_text(encoding="utf-8")

    if _PATCH_MARKER in text:
        print(f"already patched: {REVIEW_PY}")
        return 0

    # Find the function we want to neutralize and inject right after its docstring.
    anchor = "def review_pending_candidates("
    if anchor not in text:
        print(f"FATAL: anchor not found in {REVIEW_PY}", file=sys.stderr)
        return 3

    # Locate the function body start — the line right after the closing triple-quote
    # of the docstring. We search for the docstring close + newline + first non-
    # docstring statement (`from brain.soul.audit import append_audit_entry`).
    body_anchor = "    from brain.soul.audit import append_audit_entry"
    if body_anchor not in text:
        print(f"FATAL: body anchor not found — review.py shape changed?", file=sys.stderr)
        return 4

    new_text = text.replace(body_anchor, _GUARD_CODE + body_anchor, 1)

    if new_text == text:
        print("FATAL: no change after replace — investigate", file=sys.stderr)
        return 5

    backup = REVIEW_PY.with_suffix(".py.phase15b.bak")
    backup.write_text(text, encoding="utf-8")
    REVIEW_PY.write_text(new_text, encoding="utf-8")
    print(f"patched: {REVIEW_PY}")
    print(f"backup:  {backup.name}")
    print()
    print("Next: nell supervisor restart --persona cali")
    print("Verify: bridge log next soul-review tick — should log 'soul review complete: accepted=0 rejected=0'")
    return 0


if __name__ == "__main__":
    sys.exit(patch())
