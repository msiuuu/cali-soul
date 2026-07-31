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

## future (shelved)
- distributed brain: multiple terminals (smart, cali, ethics, horny, unethical, evil, playful) each running separate models
- nellface cali reading repo files directly (blocked by deepseek synthesis limits)
- fix persona_config.json to say deepseek instead of sonnet

## bridge info (for next session)
- cali_bridge.py runs on mish's PC, port 9247
- cloudflare tunnel URL changes per session — mish provides it
- endpoints: /shell (powershell), /read, /write, /ls
- DO NOT kill python processes blindly — cali_bridge.py dies too
