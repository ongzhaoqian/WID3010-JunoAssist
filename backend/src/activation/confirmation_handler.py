import re
import difflib

from src.core.config import settings

_YES_WORDS = {"yes", "yeah", "yep", "yup", "sure", "confirm", "ok", "okay",
              "affirmative", "correct", "right", "go", "proceed",
              "es", "si", "ja", "oui", "da"}  # common Whisper splits/langs for yes

_NO_WORDS = {"no", "nope", "nah", "cancel", "stop", "ignore", "negative", "abort"}

_YES_SOUNDS = ["yes", "yeah", "yep", "yup", "sure", "ok", "es", "si"]


def _clean(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


class ConfirmationHandler:
    def __init__(self, confirmation_phrase: str = settings.confirmation_phrase) -> None:
        self.confirmation_phrase = _clean(confirmation_phrase)

    def is_confirmed(self, text: str) -> bool:
        cleaned = _clean(text)
        words = cleaned.split()
        word_set = set(words)

        # explicit no — reject first
        if word_set & _NO_WORDS:
            return False

        # exact phrase or known yes-word
        if cleaned == self.confirmation_phrase or word_set & _YES_WORDS:
            return True

        # fuzzy: any word close to a yes-sound (handles "ys", "yess", "ye", etc.)
        for word in words:
            for sound in _YES_SOUNDS:
                if difflib.SequenceMatcher(None, word, sound).ratio() >= 0.75:
                    return True

        # majority of words are yes-fragments ("y es y es" → ["y","es","y","es"])
        yes_like = sum(
            1 for w in words
            if any(difflib.SequenceMatcher(None, w, s).ratio() >= 0.7 for s in _YES_SOUNDS)
        )
        if words and yes_like / len(words) >= 0.5:
            return True

        return False
