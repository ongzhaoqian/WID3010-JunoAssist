import shutil
import subprocess
import tempfile
import os
import sys
from TTS.api import TTS


def find_audio_player():
    for player in ("aplay", "paplay", "ffplay", "afplay"):
        if shutil.which(player):
            return player
    return None


def play_wav(path):
    player = find_audio_player()
    if not player:
        print("No audio player found. WAV saved at", path)
        return
    if player == "ffplay":
        cmd = ["ffplay", "-nodisp", "-autoexit", path]
    else:
        cmd = [player, path]
    print("Playing with", player)
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p.wait()


def main():
    model_name = os.getenv("JUNO_TTS_COQUI_MODEL", "tts_models/en/vctk/vits")
    default_speaker = os.getenv("JUNO_TTS_COQUI_SPEAKER", "p226")
    print(f"Loading Coqui TTS model: {model_name} (this may take a moment)")
    tts = TTS(model_name)

    print("Interactive Coqui TTS. Type text and press Enter to speak. Type 'quit' or Ctrl-D to exit.")
    print(f"Default speaker: {default_speaker}")

    try:
        while True:
            try:
                text = input("TTS> ").strip()
            except EOFError:
                print()
                break
            if not text:
                continue
            if text.lower() in ("quit", "exit"):
                break

            # Allow specifying a different speaker inline using the syntax: @speaker TEXT
            speaker = default_speaker
            if text.startswith("@"):
                parts = text.split(" ", 1)
                if len(parts) == 2:
                    speaker = parts[0][1:]
                    text = parts[1]

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                out = f.name
            try:
                tts.tts_to_file(text=text, file_path=out, speaker=speaker)
                play_wav(out)
            except Exception as e:
                print("TTS error:", e, file=sys.stderr)
            finally:
                try:
                    os.unlink(out)
                except Exception:
                    pass
    finally:
        print("Exiting interactive TTS.")


if __name__ == "__main__":
    main()
