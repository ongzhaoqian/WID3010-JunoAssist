class SpeechToText:
    """Placeholder speech-to-text service.

    For the course prototype, dashboard text commands can stand in for speech.
    Replace this with Whisper, Vosk, SpeechRecognition, or Jupiter's built-in
    speech recognition when hardware is available.
    """

    def transcribe(self, audio_input=None) -> str:
        if isinstance(audio_input, str):
            return audio_input
        return ""
