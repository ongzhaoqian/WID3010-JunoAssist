import time
from moonshine_voice import (
    MicTranscriber,
    TranscriptEventListener,
    get_model_for_language
)


class PrintListener(TranscriptEventListener):
    def on_transcript(self, transcript_line):
        print(f"Transcript: {transcript_line.text}")

model_path, model_arch = get_model_for_language("en")
mic_transcriber = MicTranscriber(model_path, model_arch)
mic_transcriber.add_listener(PrintListener())
mic_transcriber.start()

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Stopping transcription...")
finally:
    mic_transcriber.stop()
    mic_transcriber.close()