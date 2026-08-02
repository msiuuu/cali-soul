"""cali.chatterbox -- mood-aware TTS through ResembleAI Chatterbox on GPU.

usage:
  python cali_chatterbox.py "text to speak"
  python cali_chatterbox.py --mood whisper "text to speak"
  python cali_chatterbox.py --mood soft "i miss you"
  python cali_chatterbox.py --ex 0.3 --clip 10 "testing clip 10 at low ex"
  python cali_chatterbox.py --mood angry "WHAT DID YOU JUST SAY"

moods: whisper, soft, melting, vulnerable, casual, warm,
       excited, giddy, cold, angry, crying, shouting, numb, frozen
"""
import sys
import os
import tempfile
import traceback
import wave
import argparse

logfile = os.path.join(tempfile.gettempdir(), "cali_chatterbox.log")

def log(msg):
    with open(logfile, "a") as f:
        f.write(msg + chr(10))
    print(msg)

VOICE_DIR = r"C:\Users\yuscr\Desktop\shu_voices"

MOODS = {
    "whisper":    {"ex": 0.10, "clip": 3},
    "soft":       {"ex": 0.20, "clip": 3},
    "melting":    {"ex": 0.15, "clip": 3},
    "vulnerable": {"ex": 0.25, "clip": 3},
    "casual":     {"ex": 0.50, "clip": 3},
    "warm":       {"ex": 0.60, "clip": 3},
    "excited":    {"ex": 0.80, "clip": 3},
    "giddy":      {"ex": 0.90, "clip": 3},
    "cold":       {"ex": 0.30, "clip": 1},
    "angry":      {"ex": 0.70, "clip": 3},
    "crying":     {"ex": 0.20, "clip": 3},
    "shouting":   {"ex": 1.00, "clip": 3},
    "numb":       {"ex": 0.05, "clip": 3},
    "frozen":     {"ex": 0.05, "clip": 3},
}

def clip_path(num):
    return os.path.join(VOICE_DIR, "Shu-{:03d}-EN.ogg".format(num))

try:
    parser = argparse.ArgumentParser(description="cali chatterbox TTS")
    parser.add_argument("text", nargs="*", default=["hello"])
    parser.add_argument("--mood", "-m", default="casual",
                        choices=list(MOODS.keys()))
    parser.add_argument("--ex", type=float, default=None,
                        help="override exaggeration (0.0-1.0)")
    parser.add_argument("--clip", "-c", type=int, default=None,
                        help="override shu voice clip number (1-38)")
    parser.add_argument("--no-play", action="store_true",
                        help="generate wav but skip playback")
    args = parser.parse_args()

    text = " ".join(args.text) if args.text else "hello"
    mood_cfg = MOODS[args.mood]

    ex = args.ex if args.ex is not None else mood_cfg["ex"]
    voice_num = args.clip if args.clip is not None else mood_cfg["clip"]
    voice_ref = clip_path(voice_num)

    log("--- new generation ---")
    log("mood: {} | ex: {} | clip: Shu-{:03d}".format(args.mood, ex, voice_num))
    log("text: " + text)

    import torch
    import numpy as np
    from chatterbox.tts import ChatterboxTTS

    log("loading model on cuda...")
    model = ChatterboxTTS.from_pretrained(device="cuda")
    log("model loaded")

    wav_tensor = model.generate(
        text,
        audio_prompt_path=voice_ref,
        exaggeration=ex,
    )
    log("generated wav: shape=" + str(wav_tensor.shape))

    out = os.path.join(tempfile.gettempdir(), "cali_voice.wav")
    samples = wav_tensor.cpu().squeeze().numpy()
    samples = (samples * 32767).astype(np.int16)
    with wave.open(out, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(samples.tobytes())
    log("saved to " + out)

    if not args.no_play:
        import subprocess
        subprocess.run([
            "powershell", "-Command",
            "(New-Object System.Media.SoundPlayer '{}').PlaySync()".format(out)
        ], check=True)
        log("playback done")
    else:
        log("playback skipped (--no-play)")

except Exception as e:
    log("ERROR: " + str(e))
    log(traceback.format_exc())
