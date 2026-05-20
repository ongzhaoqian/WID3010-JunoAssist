from __future__ import annotations
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

        if any(word in t for word in ["music", "song", "songs", "sound", "relaxing", "calming"]):
            return Intent.PLAY_MUSIC

        if any(word in t for word in ["break", "tired", "stress", "stressed", "frustrated"]):
            return Intent.REQUEST_BREAK

        if any(phrase in t for phrase in ["what should i do", "how am i", "status"]):
            return Intent.ASK_STATUS

        return Intent.UNKNOWN

    def extract_timer_minutes(self, text: str, default: int = 25) -> int:
        duration = self.extract_timer_duration_seconds(text)
        if not duration:
            return default
        return max(1, min(duration // 60, 180))

    def extract_timer_duration_seconds(self, text: str, max_minutes: int = 180) -> int | None:
        """Extract a study timer duration from natural speech.

        Supports examples such as:
        - "25 minutes"
        - "1 minute 30 seconds"
        - "90 seconds"
        - "2:30"
        - "25" after JUNO has asked for the timer duration, interpreted as minutes.
        """
        t = text.lower().strip()
        if not t:
            return None

        clock_match = re.search(r"\b(\d{1,3})\s*[:.]\s*(\d{1,2})\b", t)
        if clock_match:
            minutes = int(clock_match.group(1))
            seconds = int(clock_match.group(2))
            return self._clamp_duration(minutes * 60 + seconds, max_minutes)

        minutes = 0
        seconds = 0
        min_match = re.search(r"(\d+)\s*(minutes?|mins?|m)\b", t)
        sec_match = re.search(r"(\d+)\s*(seconds?|secs?|s)\b", t)
        if min_match:
            minutes = int(min_match.group(1))
        if sec_match:
            seconds = int(sec_match.group(1))

        if min_match or sec_match:
            return self._clamp_duration(minutes * 60 + seconds, max_minutes)

        # When JUNO asks "How long...?", users often answer simply "25".
        # Treat a bare number as minutes for this prototype.
        bare_number = re.fullmatch(r"\s*(\d{1,3})\s*", t)
        if bare_number:
            return self._clamp_duration(int(bare_number.group(1)) * 60, max_minutes)

        return None

    @staticmethod
    def _clamp_duration(total_seconds: int, max_minutes: int) -> int | None:
        if total_seconds <= 0:
            return None
        max_seconds = max_minutes * 60
        return max(1, min(total_seconds, max_seconds))
