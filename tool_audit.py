"""Inventory migration-cali's actual tool catalog."""
import json

inventory = {}
for name, path in [
    ("NELL_TOOL_NAMES", "brain.tools:NELL_TOOL_NAMES"),
    ("DISPATCH", "brain.tools.dispatch:DISPATCH"),
    ("TOOL_SCHEMAS", "brain.tools.schemas:TOOL_SCHEMAS"),
]:
    module_path, attr = path.split(":")
    try:
        module = __import__(module_path, fromlist=[attr])
        obj = getattr(module, attr)
        if isinstance(obj, (list, set, frozenset, tuple)):
            if obj and isinstance(next(iter(obj)), dict):
                inventory[name] = sorted({d.get("name","?") for d in obj})
            else:
                inventory[name] = sorted(obj)
        elif isinstance(obj, dict):
            inventory[name] = sorted(obj.keys())
        else:
            inventory[name] = f"unknown type: {type(obj).__name__}"
    except Exception as e:
        inventory[name] = f"NOT_FOUND: {e}"

print(json.dumps(inventory, indent=2))

keywords = ["edit", "file", "write", "fetch", "url", "http", "todo", "task", "plan", "agent", "spawn", "search"]
all_tools = set()
for v in inventory.values():
    if isinstance(v, list):
        all_tools.update(v)
matches = sorted(t for t in all_tools if any(k in t.lower() for k in keywords))
print("\nproposed-add keyword matches:")
for t in matches:
    print(f"  {t}")
