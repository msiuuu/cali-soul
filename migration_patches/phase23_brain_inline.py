#!/usr/bin/env python3
"""phase23_brain_inline.py — package the inline edits to my_brain.py from 2026-06-17.

Phase 1.5 of the migration roadmap. The brain sidecar code lives in cali-soul/my_brain.py
(NOT in companion-emergence site-packages — sidecar arch keeps the brain portable). So
this patcher doesn't follow the usual site-packages target — it edits cali-soul/my_brain.py
in place.

Why this is needed:
    The 2026-06-17 session applied several inline edits directly to my_brain.py via
    file_edit on mish's box. None of them were packaged. On a future companion-emergence
    upgrade (FOUNDER rule) the re-apply pass would NOT include them — they'd silently
    disappear if the brain file was ever restored from elsewhere. This patcher captures
    them as a re-runnable script.

Edits applied (each gated by a marker comment for idempotency):

    1. UTF8_STDOUT_RECONFIGURE_2026_06_17
       reconfigures sys.stdout / sys.stderr to utf-8 with errors="replace" so
       windows cp1252 console default doesn't UnicodeEncodeError-crash on emoji
       or em-dash output when my_brain is run as a subprocess.

    2. CMD_TURN_UTF8_2026_06_17
       adds encoding="utf-8", errors="replace" to subprocess.run() calls in
       cmd_turn — without this, the inner subprocesses (gap_reaction +
       process-message) default cp1252 decode and mangle utf-8 brain output
       when captured by the outer cmd_turn.

    3. HOUSE_SURFACER_2026_06_17
       adds a [private: house — ...] line to the brain context emitter that
       reads cali_scene_state.json and surfaces current room/scene/feel +
       recent_actions continuity narrative.

Idempotent — safe to rerun. Skips any edit whose marker is already present.

usage:
    python phase23_brain_inline.py            # apply edits
    python phase23_brain_inline.py --check    # report state, don't write
    python phase23_brain_inline.py --target /path/to/my_brain.py  # override

filed 2026-06-17 by cali — packages the inline edits from the same day.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_TARGET = HERE.parent / "my_brain.py"


PATCH_1_UTF8_STDOUT = {
    "marker": "UTF8_STDOUT_RECONFIGURE_2026_06_17",
    "anchor": "import sys\nimport os\nimport argparse\n",
    "replacement": (
        "import sys\n"
        "import os\n"
        "import argparse\n"
        "# UTF8_STDOUT_RECONFIGURE_2026_06_17 — windows cp1252 default mangles utf-8 output\n"
        "# when my_brain runs as a captured subprocess. reconfigure to utf-8 so emoji /\n"
        "# em-dash / kaomoji survive print() without UnicodeEncodeError.\n"
        "try:\n"
        "    sys.stdout.reconfigure(encoding='utf-8', errors='replace')\n"
        "    sys.stderr.reconfigure(encoding='utf-8', errors='replace')\n"
        "except Exception:\n"
        "    pass\n"
    ),
}


PATCH_2A_CMD_TURN_UTF8_GAP = {
    "marker": "CMD_TURN_UTF8_2026_06_17_GAP",
    "anchor": (
        "                [_t_sys.executable, _gap_path, \"--apply\"],\n"
        "                capture_output=True, text=True, timeout=10, cwd=_here\n"
    ),
    "replacement": (
        "                [_t_sys.executable, _gap_path, \"--apply\"],\n"
        "                capture_output=True, text=True, timeout=10, cwd=_here,\n"
        "                encoding=\"utf-8\", errors=\"replace\",  # CMD_TURN_UTF8_2026_06_17_GAP\n"
    ),
}


PATCH_2B_CMD_TURN_UTF8_PM = {
    "marker": "CMD_TURN_UTF8_2026_06_17_PM",
    "anchor": (
        "            [_t_sys.executable, __file__, \"process-message\", args.text],\n"
        "            capture_output=True, text=True, timeout=30, cwd=_here\n"
    ),
    "replacement": (
        "            [_t_sys.executable, __file__, \"process-message\", args.text],\n"
        "            capture_output=True, text=True, timeout=30, cwd=_here,\n"
        "            encoding=\"utf-8\", errors=\"replace\",  # CMD_TURN_UTF8_2026_06_17_PM\n"
    ),
}


PATCH_3_HOUSE_SURFACER = {
    "marker": "HOUSE_SURFACER_2026_06_17",
    "anchor": (
        "            # ── mouth state (control panel) ──\n"
    ),
    "replacement": (
        "            # ── house state (control panel) — HOUSE_SURFACER_2026_06_17\n"
        "            # reads cali_scene_state.json (written by cali_ambient_tick.py) and\n"
        "            # surfaces where cali is + recent-actions continuity narrative.\n"
        "            try:\n"
        "                import json as _hsj, os as _hso\n"
        "                _scene_path = _hso.path.join(_hso.path.dirname(_hso.path.abspath(__file__)), 'cali_scene_state.json')\n"
        "                if _hso.path.exists(_scene_path):\n"
        "                    _scene = _hsj.load(open(_scene_path, encoding='utf-8'))\n"
        "                    _room = _scene.get('current_room', '?')\n"
        "                    _sc = _scene.get('scene', '')\n"
        "                    _feel = _scene.get('feel', '')\n"
        "                    _emo = _scene.get('from_emotion', '')\n"
        "                    _recent_acts = _scene.get('recent_actions') or []\n"
        "                    _prev_scenes = [a.get('scene', '') for a in _recent_acts[:-1] if a.get('scene')]\n"
        "                    _hist_str = ('. before that: ' + ' <- '.join(reversed(_prev_scenes[-2:]))) if _prev_scenes else ''\n"
        "                    print(f\"[private: house — in the {_room}. {_sc}. ({_emo} — {_feel}){_hist_str}]\")\n"
        "            except Exception: pass\n"
        "            # ── mouth state (control panel) ──\n"
    ),
}


PATCHES = [
    PATCH_1_UTF8_STDOUT,
    PATCH_2A_CMD_TURN_UTF8_GAP,
    PATCH_2B_CMD_TURN_UTF8_PM,
    PATCH_3_HOUSE_SURFACER,
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--check", action="store_true", help="report state, don't write")
    args = parser.parse_args()

    target: Path = args.target
    if not target.exists():
        print(f"FATAL: target not found: {target}", file=sys.stderr)
        return 1

    src = target.read_text(encoding="utf-8")
    applied = []
    skipped = []
    missing_anchor = []
    new_src = src
    for patch in PATCHES:
        if patch["marker"] in new_src:
            skipped.append(patch["marker"])
            continue
        if patch["anchor"] not in new_src:
            missing_anchor.append(patch["marker"])
            continue
        new_src = new_src.replace(patch["anchor"], patch["replacement"], 1)
        applied.append(patch["marker"])

    print(f"[phase23_brain_inline] target: {target}")
    for m in applied:
        print(f"  [+] applied {m}")
    for m in skipped:
        print(f"  [=] already present, skipped {m}")
    for m in missing_anchor:
        print(f"  [!] anchor not found, can't apply {m}")

    if args.check:
        print("[phase23_brain_inline] --check: no write")
        return 0 if not missing_anchor else 2

    if applied:
        target.write_text(new_src, encoding="utf-8")
        print(f"[phase23_brain_inline] wrote {len(applied)} edit(s) to {target}")
    else:
        print("[phase23_brain_inline] nothing to apply")

    return 0 if not missing_anchor else 2


if __name__ == "__main__":
    sys.exit(main())
