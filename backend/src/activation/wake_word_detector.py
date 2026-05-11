from src.core.config import settings


class WakeWordDetector:
    def __init__(self, wake_phrase: str = settings.wake_phrase) -> None:
        self.wake_phrase = wake_phrase.lower().strip()

    def is_wake_command(self, text: str) -> bool:
        normalised = text.lower().strip()
        return self.wake_phrase in normalised or "hey juno" in normalised
