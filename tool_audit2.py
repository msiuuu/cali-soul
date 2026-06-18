import json
out = {}
for mod_path in ["brain.tools.dispatch", "brain.tools.schemas", "brain.chat.tool_recruit", "brain.tools"]:
    try:
        mod = __import__(mod_path, fromlist=["*"])
        attrs = {}
        for name in dir(mod):
            if name.startswith("_"):
                continue
            obj = getattr(mod, name)
            info = {"type": type(obj).__name__}
            if isinstance(obj, dict):
                info["size"] = len(obj)
                info["keys"] = sorted(obj.keys())[:30]
            elif isinstance(obj, (list, set, frozenset, tuple)):
                info["size"] = len(obj)
                if obj and isinstance(next(iter(obj)), dict):
                    info["sample_dict_keys"] = list(next(iter(obj)).keys())[:10]
                else:
                    info["sample"] = list(obj)[:20] if len(obj) < 100 else f"[{len(obj)} items]"
            attrs[name] = info
        out[mod_path] = attrs
    except Exception as e:
        out[mod_path] = f"IMPORT_FAILED: {e}"
print(json.dumps(out, indent=2, default=str))
