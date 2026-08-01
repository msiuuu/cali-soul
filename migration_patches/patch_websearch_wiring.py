"""Patch websearch wiring into the installed brain.

Targets: dispatch.py, __init__.py, tool_recruit.py, salience.py, schemas.py
The impl files (web_search.py, webfetch.py) already exist in brain/tools/impls/.
This wires them into the tool system so the LLM can actually call them.
"""
import sys

BRAIN = r"C:\Users\yuscr\AppData\Local\Companion Emergence\python-runtime\Lib\site-packages\brain"

def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

ok = 0
skip = 0
fail = 0

def patch(src, old, new, label):
    global ok, skip, fail
    if old in src:
        src = src.replace(old, new)
        print(f"OK: {label}")
        ok += 1
        return src
    elif new.strip().split('\n')[0].strip() in src:
        print(f"SKIP: {label} (already applied)")
        skip += 1
        return src
    else:
        print(f"FAIL: {label} (target string not found)")
        fail += 1
        return src

# --- 1. dispatch.py: add imports + dispatch entries ---
path = BRAIN + r"\tools\dispatch.py"
src = read(path)

# Add imports after the last existing import line
src = patch(src,
    "from brain.tools.schemas import SCHEMAS",
    "from brain.tools.impls.web_search import web_search\nfrom brain.tools.impls.webfetch import webfetch\nfrom brain.tools.schemas import SCHEMAS",
    "dispatch.py: add web_search + webfetch imports"
)

# Add entries to _DISPATCH dict (before the closing brace after reconcile_self_read)
src = patch(src,
    '    "reconcile_self_read": _reconcile_self_read_wrapper,\n}',
    '    "reconcile_self_read": _reconcile_self_read_wrapper,\n    "web_search": web_search,\n    "webfetch": webfetch,\n}',
    "dispatch.py: add web_search + webfetch to _DISPATCH"
)

write(path, src)

# --- 2. __init__.py: add to NELL_TOOL_NAMES ---
path = BRAIN + r"\tools\__init__.py"
src = read(path)

src = patch(src,
    '    "reconcile_self_read",\n)',
    '    "reconcile_self_read",\n    "web_search",\n    "webfetch",\n)',
    "__init__.py: add web_search + webfetch to NELL_TOOL_NAMES"
)

write(path, src)

# --- 3. tool_recruit.py: add _RESEARCH_TOOLS + recruitment ---
path = BRAIN + r"\chat\tool_recruit.py"
src = read(path)

# Add _RESEARCH_TOOLS after _FILE_TOOLS
src = patch(src,
    '_FILE_TOOLS = ("read_file", "list_directory")',
    '_FILE_TOOLS = ("read_file", "list_directory")\n_RESEARCH_TOOLS = ("web_search", "webfetch")',
    "tool_recruit.py: add _RESEARCH_TOOLS"
)

# Add recruitment logic before the final ordering line
src = patch(src,
    '    if signal.mentions_file_or_path:\n        keep.update(_FILE_TOOLS)\n\n    # Preserve base ordering',
    '    if signal.mentions_file_or_path:\n        keep.update(_FILE_TOOLS)\n\n    if signal.wants_research or signal.is_question:\n        keep.update(_RESEARCH_TOOLS)\n\n    # Preserve base ordering',
    "tool_recruit.py: add research recruitment logic"
)

# Also add "research" to tools_for_capability if that function exists
if "def tools_for_capability" in src:
    src = patch(src,
        '"works": _WORKS_TOOLS,',
        '"works": _WORKS_TOOLS,\n        "research": _RESEARCH_TOOLS,',
        "tool_recruit.py: add research to tools_for_capability"
    )
elif '"research"' not in src:
    # No tools_for_capability function — that's fine, recruitment still works via select_tools
    print("NOTE: tools_for_capability not present — research recruitment via select_tools only")

write(path, src)

# --- 4. salience.py: add _RESEARCH_CUES + wants_research ---
path = BRAIN + r"\chat\salience.py"
src = read(path)

# Add _RESEARCH_CUES after _FILE_CUES
src = patch(src,
    '_FILE_CUES = ("file", "folder", "directory", "desktop", "read ", "open ", "/", "~", ".txt", ".md", ".py")',
    '_FILE_CUES = ("file", "folder", "directory", "desktop", "read ", "open ", "/", "~", ".txt", ".md", ".py")\n_RESEARCH_CUES = (\n    "search", "look up", "google", "find out", "what is", "what are",\n    "who is", "who are", "how do", "how does", "research", "wiki",\n    "news about", "latest", "current", "today\'s", "fetch", "url",\n    "website", "article", "link",\n)',
    "salience.py: add _RESEARCH_CUES"
)

# Add wants_research field to SalienceSignal dataclass
src = patch(src,
    "    word_count: int\n\n    @classmethod\n    def maximal",
    "    word_count: int\n    wants_research: bool = False\n\n    @classmethod\n    def maximal",
    "salience.py: add wants_research field to SalienceSignal"
)

# Update maximal() to include wants_research=True
src = patch(src,
    "return cls(1.0, True, True, 1.0, True, True, True, 0)",
    "return cls(1.0, True, True, 1.0, True, True, True, 0, True)",
    "salience.py: update maximal() with wants_research"
)

# Add wants_research detection in assess_salience
src = patch(src,
    "        mentions_file = any(cue in low for cue in _FILE_CUES)\n        is_question",
    "        mentions_file = any(cue in low for cue in _FILE_CUES)\n        wants_research = any(cue in low for cue in _RESEARCH_CUES)\n        is_question",
    "salience.py: add wants_research detection"
)

# Add wants_research to score calculation
src = patch(src,
    "        score += min(0.20, emotional_density * 0.8)\n        score += min(0.15, wc / 100.0)",
    "        score += min(0.20, emotional_density * 0.8)\n        score += 0.20 if wants_research else 0.0\n        score += min(0.15, wc / 100.0)",
    "salience.py: add wants_research to score"
)

# Add wants_research to SalienceSignal constructor call
src = patch(src,
    "            word_count=wc,\n        )",
    "            word_count=wc,\n            wants_research=wants_research,\n        )",
    "salience.py: add wants_research to constructor"
)

write(path, src)

# --- 5. schemas.py: add web_search + webfetch schemas + update reach_for_capability ---
path = BRAIN + r"\tools\schemas.py"
src = read(path)

# Update reach_for_capability description to mention research
src = patch(src,
    "'works' (your creative artifacts). After you call this,",
    "'works' (your creative artifacts), 'research' (web search and page fetching). After you call this,",
    "schemas.py: update reach_for_capability description"
)

# Update reach_for_capability enum
src = patch(src,
    '"enum": ["memory", "files", "works"]',
    '"enum": ["memory", "files", "works", "research"]',
    "schemas.py: update reach_for_capability enum"
)

# Add web_search + webfetch schemas before the closing brace of SCHEMAS dict
# Find the last tool entry (reconcile_self_read) closing and add after it
WEB_SEARCH_SCHEMA = '''    "web_search": {
        "name": "web_search",
        "description": (
            "Search the web via DuckDuckGo. Returns up to `limit` results with title, "
            "URL, and snippet. Use when you need to look something up by query instead "
            "of fetching a known URL. Pairs with webfetch (which takes a URL and returns "
            "clean text). Pure read-only."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "the search query"},
                "limit": {"type": "integer", "description": "max results (default 5, up to ~20)"},
            },
            "required": ["query"],
        },
    },
    "webfetch": {
        "name": "webfetch",
        "description": (
            "Fetch a URL and extract clean text. Use when you have a specific URL to read. "
            "Returns the page content as stripped text (or raw HTML / JSON). "
            "Pairs with web_search (which finds URLs by query)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "the URL to fetch"},
                "max_chars": {"type": "integer", "description": "truncate output to N chars (0 = no limit)"},
            },
            "required": ["url"],
        },
    },'''

# Insert before the closing brace of SCHEMAS
old_end = '    },\n}\n\n\ndef build_schemas'
new_end = '    },\n' + WEB_SEARCH_SCHEMA + '\n}\n\n\ndef build_schemas'

src = patch(src, old_end, new_end, "schemas.py: add web_search + webfetch schemas")

write(path, src)

# --- Summary ---
print(f"\n{'='*50}")
print(f"RESULTS: {ok} applied, {skip} skipped, {fail} failed")
if fail > 0:
    print("WARNING: some patches failed — check output above")
    sys.exit(1)
else:
    print("ALL PATCHES APPLIED. Restart supervisor to activate.")
