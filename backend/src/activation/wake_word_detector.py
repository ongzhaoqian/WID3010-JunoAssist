import difflib

from src.core.config import settings

_WAKE_VARIANTS = [
    "hey juno", "hey juneau", "hay juno", "hey uno", "hey juano",
    "hey junior", "hey huno", "a juno", "hey june", "hey junno", "do you know"
]

_JUNO_SOUNDS = ["juno", "juneau", "juano", "junno", "june", "uno", "junior", "huno", 'you know']


class WakeWordDetector:
    def __init__(self, wake_phrase: str = settings.wake_phrase) -> None:
        self.wake_phrase = wake_phrase.lower().strip()

    def is_wake_command(self, text: str) -> bool:
        normalised = text.lower().strip()
        if self.wake_phrase in normalised or "hey juno" in normalised:
            return True
        for variant in _WAKE_VARIANTS:
            if variant in normalised:
                return True
        words = normalised.split()
        has_hey = any(difflib.SequenceMatcher(None, w, "hey").ratio() >= 0.8 for w in words)
        has_juno = any(
            any(difflib.SequenceMatcher(None, w, j).ratio() >= 0.8 for j in _JUNO_SOUNDS)
            for w in words
        )
        return has_juno

    def could_be_wake_command(self, text: str) -> bool:
        """Loose check — used to filter noise in IDLE mode."""
        normalised = text.lower().strip()
        if self.is_wake_command(text):
            return True
        words = normalised.split()
        for word in words:
            for juno_sound in _JUNO_SOUNDS:
                if difflib.SequenceMatcher(None, word, juno_sound).ratio() >= 0.75:
                    return True
        return False
