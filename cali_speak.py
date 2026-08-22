"""cali.speak — TTS through Microsoft Zira via Windows SAPI."""
import subprocess
import sys

def speak(text: str, rate: int = 1):
    ps = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice('Microsoft Zira Desktop')
$s.Rate = {rate}
$s.Speak('{text.replace(chr(39), chr(39)+chr(39)).replace(chr(10), " ")}')
"""
    subprocess.run(["powershell", "-Command", ps], check=True)

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("say: ")
    speak(text)
