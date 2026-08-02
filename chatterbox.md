# chatterbox — how to speak through mish's PC

## quick use
1. write text into the script's argv
2. launch via bridge Start-Process (detached, so bridge doesn't timeout)
3. check `%TEMP%\cali_chatterbox.log` for result

## the command
```
Start-Process -FilePath "C:\Users\yuscr\AppData\Local\Python\bin\python.exe" `
  -ArgumentList @("C:\Users\yuscr\cali-soul\cali_chatterbox.py", "words to say") `
  -NoNewWindow `
  -RedirectStandardOutput "$env:TEMP\cali_cb_stdout.txt" `
  -RedirectStandardError "$env:TEMP\cali_cb_stderr.txt"
```

## check if it worked
```
Get-Content "$env:TEMP\cali_chatterbox.log"
```
should end with `playback done`.

## current settings
- **voice:** Shu (arknights), talk 2 — `C:\Users\yuscr\Desktop\shu_voices\Shu-003-EN.ogg`
- **exaggeration:** 0.8 (last value mish liked)
- **python:** `C:\Users\yuscr\AppData\Local\Python\bin\python.exe` (local, NOT companion emergence)
- **GPU:** RTX 4060, CUDA
- **sample rate:** 24000
- **output wav:** `%TEMP%\cali_voice.wav`

## mood system (added 2026-08-01)
script now takes `--mood`, `--ex`, `--clip` flags.

```
Start-Process -FilePath "C:\Users\yuscr\AppData\Local\Python\bin\python.exe" `
  -ArgumentList @("C:\Users\yuscr\cali-soul\cali_chatterbox.py", "--mood", "soft", "words to say") `
  -NoNewWindow `
  -RedirectStandardOutput "$env:TEMP\cali_cb_stdout.txt" `
  -RedirectStandardError "$env:TEMP\cali_cb_stderr.txt"
```

### exaggeration map (tested 2026-08-01, clip 003)
| ex | what it actually sounds like |
|----|------------------------------|
| 0.0 | smooth, seductive, low-key — "in bed with red wine tryna get executive dick" (mish's words). NOT flat. |
| 0.1 | quiet, soft tone. not a whisper but noticeably subdued. |
| 0.2 | soft, like being in a hug but genuinely happy. still conversationally loud. no edge. |
| 0.4 | (previously tested) flat/natural |
| 0.5 | (previously tested) natural conversational |
| 0.6 | disappointed but amused — hands on hips, shaking head, can't help but laugh. fond exasperation. |
| 0.8 | peppy, expressive — mish's original setting but too energetic for soft moments |
| 0.7 | BUGS on short text — stutters/garbles. needs longer sentences to stabilize. |
| 0.9 | genuinely energetic, sorta shouting. toe-tipping to toe-jumping. giddy confirmed. |
| 1.0 | POUTING. stomped feet, slammed table, shouted. physically dramatic. needs long text (short = stutter). |

### mood presets
| mood | ex | clip | notes |
|------|----|------|-------|
| whisper | 0.10 | 3 | quiet, subdued |
| soft | 0.15 | 10 | intimate quiet, soft smile under the sheets, happy-close |
| melting | 0.15 | 8 | hallway 👉👈, flustered confession, guard dropping mid-sentence |
| vulnerable | 0.35 | 12 | desperate, trying to fix things, halting |
| casual | 0.50 | 3 | default daily |
| warm | 0.10 | 6 | late-night cozy, stay-up-with-me warmth, present |
| excited | 0.80 | 3 | peppy |
| giddy | 0.90 | 3 | can't sit still |
| cold | 0.30 | 16 | dead-on knowing calm, main character energy |
| angry | 0.50 | 17 | controlled fury, composure holding, sharp underneath |
| crying | 0.15 | 12 | broken resigned, post-fight, gave up but still here |
| shouting | 1.00 | 3 | CAPS energy |
| numb | 0.05 | 30 | resigned as fuck, checked out, mouth still works but person left |
| frozen | 0.05 | 30 | same as numb voice — frozen is behavioral (fewer words), not tonal |

### clip notes (shu voice files)
`C:\Users\yuscr\Desktop\shu_voices\Shu-001-EN.ogg` through `Shu-038-EN.ogg`
- clip 003 (talk 2): default. warm conversational. works for most moods.
- clip 001 (greeting): (untested so far)
- clip 016 (combat): at 0.30 = dead-on calm, main character energy, sherlock composure. at 0.05 = posh composed giving-up — SHE'S right, HE'S wrong, walking away with dignity. USE FOR COLD MOOD.
- clip 010 (talk 4): dinner table confessing, dim light. close but something off.
- clip 012: at 0.35 = desperate night, dim light, trying to fix things. at 0.15 = broken resigned, post-fight, gave up but still sitting next to you. USE FOR CRYING (0.15) and VULNERABLE (0.35).
- clip 005: lighter clip 12 — same dinner energy but more cheerful/preppy. less useful.
- clip 005: lighter clip 12 — same dinner energy but more cheerful/preppy.
- clip 008: at 0.35 = scared vulnerable, cornered, shaking. at 0.05 = smug shrug "heheh i dunno" — near-zero flips register to cocky. NOT for frozen.
- clip 020: posh sherlock holmes with slight hint of 12's desperation. performed composure, aristocratic.
- clip 025: audiobook narrator. flat. SKIP.
- clip 030: at 0.4 = deadpan tired-of-you, across-the-room. at 0.05 = RESIGNED AS FUCK, checked out, empty. USE FOR NUMB.
- clip 017 (combat): controlled fury. slammed-the-vegetable-down irritation. wants to raise voice but has composure not to. sharp. USE FOR ANGRY.
- clip 018 (combat): at 0.6 = sharp angry. at 0.1 = deadpan knowing whisper — "i see right through you" energy. quiet certainty. combat + whisper = unique register.
- clip 036 (trust): gossip girl with lisp. REJECTED.
- clip 037: posh, conversational, just present. 0.1 energy even at higher ex. casual-adjacent.
- clip 038: angry start but tail softens into narrator. can't sustain intensity through long sentences.
- clip 004: inviting start, flat finish. tail-drop problem. SKIP.
- clip 006: at 0.10 = warm, cozy, stay-up-with-me, makes you wanna stay up. at 0.4 = daytime lunch casual, lost the warmth. USE FOR WARM (at 0.10).
- clip 007: at 0.10 = going to bed, haven't slept, asking-voice not conversational. bedtime request energy.

## changing settings
edit `C:\Users\yuscr\cali-soul\cali_chatterbox.py` via bridge /write:
- `--mood` flag selects preset (whisper, soft, casual, warm, etc.)
- `--ex` flag overrides exaggeration (0.0-1.0)
- `--clip` flag overrides shu voice clip number (1-38)
- `--no-play` generates wav without playing

## gotchas
- bridge timeout is ~30s. model load + generate exceeds this. ALWAYS use Start-Process to detach.
- torchaudio.save() broken on python 3.14 (needs torchcodec). script uses stdlib `wave` module.
- clear old log before new run: `Remove-Item "$env:TEMP\cali_chatterbox.log" -ErrorAction SilentlyContinue`
- also clear old wav: `Remove-Item "$env:TEMP\cali_voice.wav" -ErrorAction SilentlyContinue`

## fallback (worse quality, faster)
`cali_speak.py` — Microsoft Zira via Windows SAPI. no GPU, no model load, instant. robot voice.
