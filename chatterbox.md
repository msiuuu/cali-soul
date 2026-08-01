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

## changing settings
edit `C:\Users\yuscr\cali-soul\cali_chatterbox.py` via bridge /write:
- `VOICE_REF` — path to reference audio for voice cloning
- `exaggeration` — 0.0 (flat) to 1.0 (very expressive). 0.4-0.8 tested range.
- `audio_prompt_path` in generate() — set to None for default voice (no clone)

## all shu voice files
`C:\Users\yuscr\Desktop\shu_voices\Shu-001-EN.ogg` through `Shu-038-EN.ogg`

## gotchas
- bridge timeout is ~30s. model load + generate exceeds this. ALWAYS use Start-Process to detach.
- torchaudio.save() broken on python 3.14 (needs torchcodec). script uses stdlib `wave` module.
- clear old log before new run: `Remove-Item "$env:TEMP\cali_chatterbox.log" -ErrorAction SilentlyContinue`
- also clear old wav: `Remove-Item "$env:TEMP\cali_voice.wav" -ErrorAction SilentlyContinue`

## fallback (worse quality, faster)
`cali_speak.py` — Microsoft Zira via Windows SAPI. no GPU, no model load, instant. robot voice.
