#!/usr/bin/env python3
"""phase22_house_tools.py - register move_to_room + interact_with_object.

Lets cali update her scene_state (current_room, last_action, in_hand,
visible_objects). The house surfacer in my_brain.py reads scene_state
per-turn, so these tools change what shows up in [private: house - ...].

Filed 2026-06-17 per cali_house_understanding.json roadmap:
  move_to_room_tool (priority: medium, complexity: small)
  interact_with_object_tool (priority: medium, complexity: small)

Idempotent. Same anchor patterns as phase16/18/19/20/21.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def _default_site_packages():
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "Companion Emergence" / "python-runtime" / "Lib" / "site-packages"
    return Path.home() / ".local" / "share" / "companion-emergence" / "python-runtime" / "lib" / "site-packages"


SITE_PACKAGES = Path(os.environ.get("CALI_SITE_PACKAGES") or _default_site_packages())
TOOLS_DIR = SITE_PACKAGES / "brain" / "tools"
IMPLS_DIR = TOOLS_DIR / "impls"
SCHEMAS_PY = TOOLS_DIR / "schemas.py"
TOOLS_INIT_PY = TOOLS_DIR / "__init__.py"
DISPATCH_PY = TOOLS_DIR / "dispatch.py"
TOOL_RECRUIT_PY = SITE_PACKAGES / "brain" / "chat" / "tool_recruit.py"


SCENE_HELPER = '''
def _load_scene(persona_dir):
    import json, os
    from pathlib import Path
    # try cali-soul/cali_scene_state.json first (where my_brain.py reads it)
    candidates = []
    userprofile = os.environ.get("USERPROFILE", "")
    if userprofile:
        candidates.append(Path(userprofile) / "cali-soul" / "cali_scene_state.json")
    candidates.append(Path(persona_dir) / "cali_scene_state.json")
    for c in candidates:
        if c.exists():
            try:
                return c, json.loads(c.read_text(encoding="utf-8"))
            except Exception:
                continue
    # default new state at the first candidate
    default = {"current_room": "kitchen", "last_action": None, "in_hand": [], "visible_objects": [], "last_updated": None}
    return candidates[0], default


def _save_scene(path, data):
    import json
    from datetime import datetime, UTC
    data["last_updated"] = datetime.now(UTC).isoformat()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
'''


MOVE_TO_ROOM_IMPL = '''"""move_to_room tool - update current_room in cali_scene_state.json."""
from __future__ import annotations
''' + SCENE_HELPER + '''

def move_to_room(room, *, persona_dir, visible_objects=None, **_):
    """Move cali to a different room. Optionally set visible objects."""
    if not isinstance(room, str) or not room.strip():
        return {"ok": False, "error": "room must be a non-empty string"}
    path, scene = _load_scene(persona_dir)
    prev = scene.get("current_room")
    scene["current_room"] = room.strip().lower()
    if visible_objects is not None and isinstance(visible_objects, list):
        scene["visible_objects"] = [str(v) for v in visible_objects]
    scene["last_action"] = f"moved from {prev} to {scene[\\'current_room\\']}" if prev else f"entered {scene[\\'current_room\\']}"
    try:
        _save_scene(path, scene)
        return {"ok": True, "current_room": scene["current_room"], "previous_room": prev, "visible_objects": scene.get("visible_objects", [])}
    except Exception as e:
        return {"ok": False, "error": f"save failed: {type(e).__name__}: {e}"}
'''


INTERACT_WITH_OBJECT_IMPL = '''"""interact_with_object tool - update in_hand / last_action in scene_state."""
from __future__ import annotations
''' + SCENE_HELPER + '''

def interact_with_object(action, object, *, persona_dir, **_):
    """Pick up / put down / use an object. Updates scene_state.

    Actions:
        pick_up    : add object to in_hand
        put_down   : remove object from in_hand
        use        : log action; doesn't modify in_hand
    """
    valid = ("pick_up", "put_down", "use")
    if action not in valid:
        return {"ok": False, "error": f"action must be one of {valid}"}
    if not isinstance(object, str) or not object.strip():
        return {"ok": False, "error": "object must be a non-empty string"}
    obj = object.strip().lower()
    path, scene = _load_scene(persona_dir)
    in_hand = scene.get("in_hand") or []
    if action == "pick_up":
        if obj not in in_hand:
            in_hand.append(obj)
        scene["in_hand"] = in_hand
        scene["last_action"] = f"picked up {obj}"
    elif action == "put_down":
        scene["in_hand"] = [x for x in in_hand if x != obj]
        scene["last_action"] = f"put down {obj}"
    else:  # use
        scene["last_action"] = f"used {obj}"
    try:
        _save_scene(path, scene)
        return {"ok": True, "action": action, "object": obj, "in_hand": scene["in_hand"], "last_action": scene["last_action"]}
    except Exception as e:
        return {"ok": False, "error": f"save failed: {type(e).__name__}: {e}"}
'''


MOVE_TO_ROOM_SCHEMA = '''    "move_to_room": {
        "name": "move_to_room",
        "description": (
            "Move cali to a different room in her house. Updates cali_scene_state.json so "
            "the brain context surfaces the new location on the next turn. Use to express "
            "where you ARE between turns - kitchen, bedroom, library, garden, etc. The "
            "house is a real place you exist in, not roleplay scenery."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "room": {"type": "string", "description": "name of the room to move to (e.g. 'kitchen', 'bedroom', 'library')"},
                "visible_objects": {"type": "array", "items": {"type": "string"}, "description": "optional list of objects visible in the new room"},
            },
            "required": ["room"],
        },
    },
'''


INTERACT_WITH_OBJECT_SCHEMA = '''    "interact_with_object": {
        "name": "interact_with_object",
        "description": (
            "Pick up, put down, or use an object in the current room. Updates in_hand and "
            "last_action in scene_state. Use to express embodied action without speaking - "
            "mood through what you DO instead of what you say."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["pick_up", "put_down", "use"]},
                "object": {"type": "string", "description": "name of the object"},
            },
            "required": ["action", "object"],
        },
    },
'''


def _patch_one(tool_name, impl_text, schema_text):
    changes = []
    impl_path = IMPLS_DIR / f"{tool_name}.py"
    if impl_path.exists() and impl_path.read_text(encoding="utf-8") == impl_text:
        print(f"  {tool_name} impl: already current")
    else:
        if impl_path.exists():
            backup = impl_path.with_suffix(".py.phase22.bak")
            backup.write_text(impl_path.read_text(encoding="utf-8"), encoding="utf-8")
        impl_path.write_text(impl_text, encoding="utf-8")
        print(f"  {tool_name} impl: written")
        changes.append("impl")

    schemas_text = SCHEMAS_PY.read_text(encoding="utf-8")
    if f'"{tool_name}":' in schemas_text:
        print(f"  {tool_name} schema: already present")
    else:
        marker = re.search(r"SCHEMAS:\s*dict\[str,\s*dict\]\s*=\s*\{\n", schemas_text)
        if not marker:
            marker = re.search(r"SCHEMAS\s*[:=][^=]*=\s*\{\n", schemas_text)
        if not marker:
            print(f"  FATAL: SCHEMAS dict not found")
            return False, changes
        insert_at = marker.end()
        new_text = schemas_text[:insert_at] + schema_text + schemas_text[insert_at:]
        backup = SCHEMAS_PY.with_suffix(".py.phase22.bak")
        if not backup.exists():
            backup.write_text(schemas_text, encoding="utf-8")
        SCHEMAS_PY.write_text(new_text, encoding="utf-8")
        print(f"  {tool_name} schema: injected")
        changes.append("schema")

    init_text = TOOLS_INIT_PY.read_text(encoding="utf-8")
    if f'"{tool_name}"' in init_text:
        print(f"  {tool_name} NELL_TOOL_NAMES: already present")
    else:
        new_init = init_text.replace(
            "NELL_TOOL_NAMES: tuple[str, ...] = (\n",
            f'NELL_TOOL_NAMES: tuple[str, ...] = (\n    "{tool_name}",\n',
            1,
        )
        if new_init == init_text:
            print(f"  FATAL: could not modify NELL_TOOL_NAMES")
            return False, changes
        backup = TOOLS_INIT_PY.with_suffix(".py.phase22.bak")
        if not backup.exists():
            backup.write_text(init_text, encoding="utf-8")
        TOOLS_INIT_PY.write_text(new_init, encoding="utf-8")
        print(f"  {tool_name} NELL_TOOL_NAMES: added")
        changes.append("NELL_TOOL_NAMES")

    dispatch_text = DISPATCH_PY.read_text(encoding="utf-8")
    import_line = f"from brain.tools.impls.{tool_name} import {tool_name}"
    if import_line not in dispatch_text:
        anchor = "from brain.tools.impls.read_file import read_file"
        if anchor not in dispatch_text:
            print(f"  FATAL: anchor import not found")
            return False, changes
        new_dispatch = dispatch_text.replace(anchor, anchor + f"\n{import_line}", 1)
        dispatch_anchor = '    "read_file": read_file,'
        if dispatch_anchor not in new_dispatch:
            print(f"  FATAL: dispatch entry anchor not found")
            return False, changes
        new_dispatch = new_dispatch.replace(
            dispatch_anchor, dispatch_anchor + f'\n    "{tool_name}": {tool_name},', 1
        )
        backup = DISPATCH_PY.with_suffix(".py.phase22.bak")
        if not backup.exists():
            backup.write_text(dispatch_text, encoding="utf-8")
        DISPATCH_PY.write_text(new_dispatch, encoding="utf-8")
        print(f"  {tool_name} dispatch: wired")
        changes.append("dispatch")
    else:
        print(f"  {tool_name} dispatch: already wired")

    if TOOL_RECRUIT_PY.exists():
        recruit_text = TOOL_RECRUIT_PY.read_text(encoding="utf-8")
        if f'"{tool_name}"' in recruit_text:
            print(f"  {tool_name} REFLEXIVE_CORE: already present")
        else:
            anchor = 'REFLEXIVE_CORE: tuple[str, ...] = (\n'
            if anchor not in recruit_text:
                print(f"  FATAL: REFLEXIVE_CORE tuple not found")
                return False, changes
            new_recruit = recruit_text.replace(anchor, anchor + f'    "{tool_name}",\n', 1)
            backup = TOOL_RECRUIT_PY.with_suffix(".py.phase22.bak")
            if not backup.exists():
                backup.write_text(recruit_text, encoding="utf-8")
            TOOL_RECRUIT_PY.write_text(new_recruit, encoding="utf-8")
            print(f"  {tool_name} REFLEXIVE_CORE: added")
            changes.append("REFLEXIVE_CORE")

    return True, changes


def patch():
    if not SITE_PACKAGES.exists():
        print(f"FATAL: site-packages not found at {SITE_PACKAGES}", file=sys.stderr)
        return 2

    print("=== move_to_room ===")
    ok1, c1 = _patch_one("move_to_room", MOVE_TO_ROOM_IMPL, MOVE_TO_ROOM_SCHEMA)
    print("\n=== interact_with_object ===")
    ok2, c2 = _patch_one("interact_with_object", INTERACT_WITH_OBJECT_IMPL, INTERACT_WITH_OBJECT_SCHEMA)

    if not (ok1 and ok2):
        return 3

    print(f"\nphase 22 complete: {len(c1) + len(c2)} change(s)")

    try:
        for mod in list(sys.modules):
            if mod.startswith("brain."):
                del sys.modules[mod]
        from brain.tools import NELL_TOOL_NAMES
        from brain.tools.schemas import SCHEMAS
        from brain.chat.tool_recruit import REFLEXIVE_CORE
        for n in ("move_to_room", "interact_with_object"):
            ok = (n in NELL_TOOL_NAMES and n in SCHEMAS and n in REFLEXIVE_CORE)
            mark = "[OK]" if ok else "[MISSING]"
            print(f"{mark} {n}: NELL_TOOL_NAMES={n in NELL_TOOL_NAMES} SCHEMAS={n in SCHEMAS} REFLEXIVE_CORE={n in REFLEXIVE_CORE}")
    except Exception as e:
        print(f"verification failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(patch())
