from __future__ import annotations
import re
from datetime import datetime
from src.core.models import Intent


class IntentClassifier:
    """Rule-based intent classifier for an undergraduate-scope prototype."""

    _PRIORITY_WORDS = {"low", "medium", "normal", "high", "urgent", "important"}

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

        if self.looks_like_schedule_add(t):
            return Intent.ADD_SCHEDULE

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

    def looks_like_schedule_add(self, text: str) -> bool:
        t = text.lower().strip()
        add_words = ("add", "create", "insert", "book", "put", "set")
        schedule_words = ("schedule", "calendar", "plan", "agenda", "timetable")
        if any(word in t for word in add_words) and any(word in t for word in schedule_words):
            return True
        # Structured speech from Whisper often arrives as a compact field list.
        # Example: "date 2026-05-20 time 15:30 purpose revision priority high".
        has_structured_fields = all(field in t for field in ("date", "time", "purpose"))
        return has_structured_fields

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

    def extract_schedule_item(self, text: str) -> dict[str, str | None]:
        """Extract structured schedule details from a transcribed command.

        Expected fields may be spoken in either labelled or natural form:
        - "date 2026-05-20 time 15:30 purpose revision priority high"
        - "add schedule on 2026-05-20 at 3:30 pm purpose revision priority high"
        """
        original = text.strip()
        lower = original.lower()

        date = self._extract_date(lower)
        time_value = self._extract_time(lower)
        priority = self._extract_priority(lower)
        purpose = self._extract_purpose(original)

        return {
            "title": purpose,
            "date": date,
            "formatted_date": self.format_display_date(date) if date else None,
            "time": time_value,
            "type": "study",
            "priority": priority or "medium",
        }

    @staticmethod
    def format_display_date(value: str | None) -> str | None:
        if not value:
            return None
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return value
        return f"{parsed.day} {parsed.strftime('%B')}, {parsed.year}"

    def _extract_date(self, text: str) -> str | None:
        match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if not match:
            return None
        # Validate before accepting.
        try:
            datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            return None
        return match.group(1)

    def _extract_time(self, text: str) -> str | None:
        labelled = re.search(r"\b(?:time|at)\s*(?:is|:)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text)
        generic = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b", text)
        match = labelled or generic
        if not match:
            return None

        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        return f"{hour:02d}:{minute:02d}"

    def _extract_priority(self, text: str) -> str | None:
        match = re.search(r"\bpriority\s*(?:is|:)?\s*(low|medium|normal|high|urgent|important)\b", text)
        if not match:
            for word in self._PRIORITY_WORDS:
                if re.search(rf"\b{re.escape(word)}\s+priority\b", text):
                    match_value = word
                    break
            else:
                return None
        else:
            match_value = match.group(1)

        if match_value in {"urgent", "important"}:
            return "high"
        if match_value == "normal":
            return "medium"
        return match_value

    def _extract_purpose(self, text: str) -> str | None:
        # Prefer explicit labelled purpose/title/task/event content.
        label_match = re.search(
            r"\b(?:purpose|title|task|event)\s*(?:is|:|for|to)?\s+(.+?)(?=\s+\b(?:date|on|time|at|priority)\b|$)",
            text,
            flags=re.IGNORECASE,
        )
        if label_match:
            cleaned = self._clean_purpose(label_match.group(1))
            if cleaned:
                return cleaned

        # Fallback: remove structured fields and command words, then use what remains.
        cleaned_text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", text)
        cleaned_text = re.sub(r"\b(?:date|on)\s*(?:is|:)?\s*", " ", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"\b(?:time|at)\s*(?:is|:)?\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b", " ", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"\bpriority\s*(?:is|:)?\s*(low|medium|normal|high|urgent|important)\b", " ", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"\b(add|create|insert|book|put|set|schedule|calendar|plan|agenda|timetable|item)\b", " ", cleaned_text, flags=re.IGNORECASE)
        return self._clean_purpose(cleaned_text)

    @staticmethod
    def _clean_purpose(value: str | None) -> str | None:
        if not value:
            return None
        value = re.sub(r"[,.]+$", "", value.strip())
        value = re.sub(r"\s+", " ", value)
        if not value:
            return None
        return value[:1].upper() + value[1:]

    @staticmethod
    def _clamp_duration(total_seconds: int, max_minutes: int) -> int | None:
        if total_seconds <= 0:
            return None
        max_seconds = max_minutes * 60
        return max(1, min(total_seconds, max_seconds))
