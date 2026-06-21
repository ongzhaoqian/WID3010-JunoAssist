import shutil
import subprocess
import tempfile
import os
import sys
import requests


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
    print(f"Using Hugging Face Inference API model: {model_name}")
    print("Interactive HF TTS. Type text and press Enter to speak. Type 'quit' or Ctrl-D to exit.")
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
                headers = {'Accept': 'audio/wav'}
                hf_token = os.getenv('JUNO_HF_TOKEN', os.getenv('HUGGINGFACE_HUB_TOKEN', None))
                if hf_token:
                    headers['Authorization'] = f'Bearer {hf_token}'

                url = f'https://api-inference.huggingface.co/models/{model_name}'
                payload = {'inputs': text, 'parameters': {'speaker': speaker}}
                resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
                if resp.status_code != 200:
                    try:
                        err = resp.json()
                    except Exception:
                        err = resp.text
                    raise RuntimeError(f'HF TTS inference failed: {err} (status={resp.status_code})')

                with open(out, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

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
