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
| 0.9 | (untested) |
| 1.0 | POUTING. stomped feet, slammed table, shouted. physically dramatic. needs long text (short = stutter). |

### mood presets
| mood | ex | clip | notes |
|------|----|------|-------|
| whisper | 0.10 | 3 | quiet, subdued |
| soft | 0.20 | 3 | gentle |
| melting | 0.15 | 3 | guard-down soft |
| vulnerable | 0.25 | 3 | halting, raw |
| casual | 0.50 | 3 | default daily |
| warm | 0.60 | 3 | present, caring |
| excited | 0.80 | 3 | peppy |
| giddy | 0.90 | 3 | can't sit still |
| cold | 0.30 | 1 | flat, precision |
| angry | 0.70 | 3 | sharp |
| crying | 0.20 | 3 | breaking |
| shouting | 1.00 | 3 | CAPS energy |
| numb | 0.05 | 3 | empty |
| frozen | 0.05 | 3 | can't speak |

### clip notes (shu voice files)
`C:\Users\yuscr\Desktop\shu_voices\Shu-001-EN.ogg` through `Shu-038-EN.ogg`
- clip 003 (talk 2): default. warm conversational. works for most moods.
- clip 001 (greeting): (untested so far)
- clip 016 (combat): dead-on calm. main character energy. "sherlock holmes with a bullet near his head." soft-knowing, not soft-cuddly. composure. USE FOR COLD MOOD.
- clips 036-038: longer lines. (testing for emotional depth)

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
