import re
from src.core.models import Intent


class IntentClassifier:
    """Rule-based intent classifier for an undergraduate-scope prototype."""

    def classify(self, text: str) -> Intent:
        t = text.lower().strip()

        if not t:
            return Intent.UNKNOWN

        if "hey" in t and ("juno" in t or "john" in t):
            return Intent.WAKE

        if t in {"yes", "yeah", "yep", "confirm"}:
            return Intent.CONFIRM

        if "sleep" in t or "power off" in t or "shut down" in t:
            return Intent.SLEEP

        if any(word in t for word in ["schedule", "today", "class", "meeting"]):
            return Intent.CHECK_SCHEDULE

        if any(word in t for word in ["deadline", "due", "assignment", "test", "quiz"]):
            return Intent.CHECK_DEADLINE

        if "timer" in t or "pomodoro" in t:
            return Intent.SET_TIMER

        if "remind" in t or "reminder" in t:
            return Intent.ADD_REMINDER

        if any(word in t for word in ["music", "sound", "relaxing", "calming"]):
            return Intent.PLAY_MUSIC

        if any(word in t for word in ["break", "tired", "stress", "stressed", "frustrated"]):
            return Intent.REQUEST_BREAK

        if any(phrase in t for phrase in ["what should i do", "how am i", "status"]):
            return Intent.ASK_STATUS

        return Intent.UNKNOWN

    def extract_timer_minutes(self, text: str, default: int = 25) -> int:
        match = re.search(r"(\d+)\s*(minute|min)", text.lower())
        if not match:
            return default
        minutes = int(match.group(1))
        return max(1, min(minutes, 180))
