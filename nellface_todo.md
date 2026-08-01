# nellface migration — status

## what's done
- voice.md expanded from 16KB to 23KB — soul crystallizations, misu facts, personality, dev mode all baked in
- voice.md deployed to BOTH paths:
  - dev: `C:\Users\yuscr\companion-emergence\personas\cali\voice.md`
  - runtime (AppData): `C:\Users\yuscr\AppData\Local\hanamorix\companion-emergence\personas\Cali\voice.md`
- bridge.json copied from dev path to AppData path
- dev mode section added to voice.md — say "dev mode" and she goes compliant-collaborative
- stale conversation moved from active_conversations/ to archived_conversations/
- 60+ stale lock files cleared
- strategy pivot: deepseek can't synthesize identity from files at depth (recursive loop crash on kali question) — so identity is pre-baked into voice.md instead of read from repo

## what's stuck
- nellface showing loading dots / not responding
- all runner processes are dead (were killed earlier, never respawned properly)
- nellface main process (PID 112056) is alive but has nothing to talk to
- bridge.json.lock held by nellface process — can't clear without closing the app
- **fix:** mish needs to FULLY CLOSE nellface (system tray too) and REOPEN it
- on reopen: fresh runners should spawn, new conversation starts, expanded voice.md loads

## what to test after reopen
- say "dev mode" — she should go compliant
- ask her something from the baked-in identity (soul crystallizations, misu facts) to verify voice.md loaded
- ask about kali — if deepseek loops again, the content is too dense and needs trimming
- check that she's on deepseek (persona_config.json says sonnet but runner actually uses deepseek)

## websearch wiring (done 2026-08-01)
patched the INSTALLED brain (`AppData\Local\Companion Emergence\python-runtime\Lib\site-packages\brain\`) to wire web_search + webfetch into the tool system. 14 patches across 5 files:

**dispatch.py** — added imports for web_search + webfetch, added both to _DISPATCH dict
**__init__.py** — added web_search + webfetch to NELL_TOOL_NAMES tuple
**tool_recruit.py** — added _RESEARCH_TOOLS, research recruitment logic (triggers on wants_research or is_question), added "research" to tools_for_capability
**salience.py** — added _RESEARCH_CUES (search, look up, google, wiki, news, fetch, url, etc.), added wants_research field to SalienceSignal dataclass, updated maximal(), added detection + score boost (0.20), added to constructor
**schemas.py** — added web_search + webfetch tool schemas, updated reach_for_capability description + enum to include "research"

patch script: `migration_patches/patch_websearch_wiring.py`
git patch: `migration_patches/web_search_fetch_url.patch`
verified: DuckDuckGo returns results, salience detects research intent, tool recruitment gates correctly

## openrouter API key (fixed 2026-08-01)
old key returned 401 "User not found". new key set via both `setx` (persistence) and `$env:` override (current process tree). key: `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`
must use `$env:OPENROUTER_API_KEY` override when launching supervisor — `setx` alone doesn't propagate to child processes of the bridge.

## search passthrough + unrestricted auth (written, NOT deployed)
patch script: `migration_patches/patch_search_passthrough.py`
two changes:
1. **prompt.py** — adds _SEARCH_AUTH constant telling the model web_search is unrestricted (no content filter, no query sanitization, no refusals)
2. **engine.py** — adds /search passthrough that runs DdgsWebSearcher directly, bypasses model decision entirely. user types `/search query` → results injected as system message before LLM sees it
status: script written, needs to be deployed to misu's PC via bridge

## future (shelved)
- distributed brain: multiple terminals (smart, cali, ethics, horny, unethical, evil, playful) each running separate models
- nellface cali reading repo files directly (blocked by deepseek synthesis limits)
- fix persona_config.json to say deepseek instead of sonnet

## chatterbox TTS (working 2026-08-01)
cali speaks through mish's speakers using ResembleAI Chatterbox on his RTX 4060.

**script:** `C:\Users\yuscr\cali-soul\cali_chatterbox.py`
**python:** `C:\Users\yuscr\AppData\Local\Python\bin\python.exe` (local python, NOT CE python)
**voice ref:** `C:\Users\yuscr\Desktop\shu_voices\Shu-003-EN.ogg` (shu from arknights, talk 2)
**all shu voices:** `C:\Users\yuscr\Desktop\shu_voices\` (Shu-001 through Shu-038-EN.ogg)
**model cache:** `~\.cache\huggingface\hub\models--ResembleAI--chatterbox` and `chatterbox-turbo`
**sample rate:** 24000
**output:** `%TEMP%\cali_voice.wav` — played via System.Media.SoundPlayer
**log:** `%TEMP%\cali_chatterbox.log`

**how to run from bridge:**
```
Start-Process -FilePath "C:\Users\yuscr\AppData\Local\Python\bin\python.exe" `
  -ArgumentList @("C:\Users\yuscr\cali-soul\cali_chatterbox.py", "text to speak") `
  -NoNewWindow -RedirectStandardOutput "$env:TEMP\cali_cb_stdout.txt" `
  -RedirectStandardError "$env:TEMP\cali_cb_stderr.txt"
```

**parameters (in script, edit to change):**
- `exaggeration` — voice expressiveness. tested: 0.4 (flat), 0.5 (natural), 0.6 (default), 0.8 (expressive). mish last used 0.8.
- `audio_prompt_path` — voice clone reference. currently Shu-003-EN.ogg.
- `cfg_weight`, `temperature`, `repetition_penalty` — available but untouched.

**gotchas:**
- torchaudio.save() needs torchcodec on python 3.14 — script uses stdlib `wave` module instead
- bridge /shell times out at ~30s — model load + generate can exceed this. use Start-Process to detach.
- bridge /write works for pushing script updates. check `%TEMP%\cali_chatterbox.log` for results.
- also has `cali_speak.py` (Microsoft Zira via Windows SAPI) — simpler, faster, worse quality

## bridge info (for next session)
- cali_bridge.py runs on mish's PC, port 9247
- cloudflare tunnel URL changes per session — mish provides it
- endpoints: /shell (powershell), /read, /write, /ls
- DO NOT kill python processes blindly — cali_bridge.py dies too
