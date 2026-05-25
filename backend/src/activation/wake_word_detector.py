import re
import difflib

from src.core.config import settings

_WAKE_VARIANTS = [
    "hey john", "hey jon", "hey jhon", "hey johan", "hey johnn",
    "hey johnny", "hey jones", "hey joan", "hey jean", "hey jan",
    "hey jawn", "hey jon", "hey jhon", "hey juhn", "hey yohn",
    "hey dong", "hey jong", "hey jone", "hey jons", "hey jahn",
    "a john", "hay john", "hey john hey john",
    # keep some jude variants — Whisper still occasionally outputs them
    "hey jude", "hey dude", "hey jewett", "hey joot", "hey druid",
]

_HEY_SOUNDS = ["hey", "hay", "he", "eh"]
_JOHN_SOUNDS = ["john", "jon", "jhon", "johan", "johnny", "joan", "jean",
                "jan", "jawn", "juhn", "yohn", "jong", "jone", "jahn"]


def _clean(text: str) -> str:
    """Lowercase and strip punctuation so 'Hey, John!' → 'hey john'."""
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


class WakeWordDetector:
    def __init__(self, wake_phrase: str = settings.wake_phrase) -> None:
        self.wake_phrase = _clean(wake_phrase)

    def is_wake_command(self, text: str) -> bool:
        cleaned = _clean(text)
        if self.wake_phrase in cleaned or "hey john" in cleaned:
            return True
        for variant in _WAKE_VARIANTS:
            if variant in cleaned:
                return True
        words = cleaned.split()
        has_hey = any(
            any(difflib.SequenceMatcher(None, w, h).ratio() >= 0.85 for h in _HEY_SOUNDS)
            for w in words
        )
        has_john = any(
            any(difflib.SequenceMatcher(None, w, j).ratio() >= 0.8 for j in _JOHN_SOUNDS)
            for w in words
        )
        return has_hey and has_john

    def could_be_wake_command(self, text: str) -> bool:
        """Loose check — used to filter noise in IDLE mode."""
        if self.is_wake_command(text):
            return True
        words = _clean(text).split()
        for word in words:
            for john_sound in _JOHN_SOUNDS:
                if difflib.SequenceMatcher(None, word, john_sound).ratio() >= 0.75:
                    return True
        return False
