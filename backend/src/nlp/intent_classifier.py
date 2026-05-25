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

        _check_reminder_phrases = ("what are my reminders", "show my reminders", "list reminders", "check reminders", "my reminders", "show reminders")
        if any(p in t for p in _check_reminder_phrases):
            return Intent.CHECK_REMINDERS

        if "remind me" in t or self.looks_like_reminder_add(t):
            return Intent.ADD_REMINDER

        if "remind" in t or "reminder" in t:
            return Intent.CHECK_REMINDERS

        if any(word in t for word in ["music", "song", "songs", "sound", "relaxing", "calming"]):
            return Intent.PLAY_MUSIC

        if any(word in t for word in ["break", "tired", "stress", "stressed", "frustrated"]):
            return Intent.REQUEST_BREAK

        if any(phrase in t for phrase in ["what should i do", "how am i", "status"]):
            return Intent.ASK_STATUS

        return Intent.UNKNOWN

    def looks_like_reminder_add(self, text: str) -> bool:
        t = text.lower().strip()
        add_words = ("add", "create", "insert", "put", "set", "make")
        if "remind me" in t or "reminder to" in t or "reminder for" in t:
            return True
        if any(word in t for word in add_words) and "reminder" in t:
            return True
        return "reminder" in t and any(field in t for field in ("date", "time", "purpose", "title", "task"))

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
        """Extract a study timer duration from flexible speech.

        Supports digit and word formats, including:
        - "25 minutes", "1 minute 30 seconds", "90 seconds"
        - "2:30", "1h 30m", "1 hr and 15 min"
        - "half an hour", "quarter of an hour", "one and a half hours"
        - "twenty five minutes", "one minute thirty seconds"
        - bare answers such as "25" or "twenty five" after JUNO asks.
        """
        t = self._normalise_duration_text(text)
        if not t:
            return None

        # 2:30 or 2.30 means 2 minutes 30 seconds in the timer-answer context.
        clock_match = re.search(r"\b(\d{1,3})\s*[:.]\s*(\d{1,2})\b", t)
        if clock_match:
            minutes = int(clock_match.group(1))
            seconds = int(clock_match.group(2))
            return self._clamp_duration(minutes * 60 + seconds, max_minutes)

        total_seconds = 0

        # Compact forms: 1h 30m, 1 hr, 45s.
        for match in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(hours?|hrs?|hr|h)\b", t):
            total_seconds += int(float(match.group(1)) * 3600)
        for match in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(minutes?|mins?|min|m)\b", t):
            total_seconds += int(float(match.group(1)) * 60)
        for match in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(seconds?|secs?|sec|s)\b", t):
            total_seconds += int(float(match.group(1)))

        # Word-number forms. Convert only unit-attached phrases to avoid
        # accidentally reading unrelated command text as duration.
        total_seconds += self._sum_word_unit_durations(t)

        if re.search(r"\bhalf\s+(?:an?\s+)?hour\b|\bhalf\s+hour\b", t):
            total_seconds += 30 * 60
        if re.search(r"\b(?:a\s+)?quarter\s+(?:of\s+an?\s+)?hour\b|\bquarter\s+hour\b", t):
            total_seconds += 15 * 60
        if re.search(r"\bone\s+and\s+a\s+half\s+hours?\b|\ban?\s+and\s+a\s+half\s+hours?\b", t):
            # The one-hour part may not be captured by word-unit parsing because
            # of the phrase "and a half". Add the intended 90 minutes once.
            total_seconds += 90 * 60

        if total_seconds:
            return self._clamp_duration(total_seconds, max_minutes)

        # A bare digit or bare number phrase is interpreted as minutes after the
        # robot has asked for the timer duration.
        bare_digit = re.fullmatch(r"\s*(\d{1,3})\s*", t)
        if bare_digit:
            return self._clamp_duration(int(bare_digit.group(1)) * 60, max_minutes)

        bare_word_number = self._words_to_number(t)
        if bare_word_number is not None:
            return self._clamp_duration(bare_word_number * 60, max_minutes)

        return None

    def is_timer_duration_cancel(self, text: str) -> bool:
        """Return True when the user wants to leave timer setup."""
        t = self._normalise_duration_text(text)
        if not t:
            return False
        cancel_phrases = (
            "cancel", "stop", "exit", "quit", "never mind", "nevermind",
            "not now", "later", "skip", "forget it", "no timer",
            "dont start", "do not start", "don't start", "leave it",
            "no need", "i dont know", "i don't know", "nothing", "none",
        )
        return any(phrase in t for phrase in cancel_phrases) or t in {"no", "nah", "nope"}

    def is_likely_different_active_intent(self, text: str) -> bool:
        """Used while waiting for a timer duration to let the user move on."""
        intent = self.classify(text)
        return intent not in {Intent.UNKNOWN, Intent.SET_TIMER}


    @staticmethod
    def _normalise_duration_text(text: str) -> str:
        text = text.lower().strip()
        replacements = {
            "hours": "hours", "hrs": "hrs", "mins": "mins", "secs": "secs",
            "colour": "color", "an hour": "an hour", "a hour": "an hour",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = text.replace("one-half", "one half").replace("half-hour", "half hour")
        text = re.sub(r"[^a-z0-9:.\s'-]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _sum_word_unit_durations(self, text: str) -> int:
        total = 0
        unit_pattern = re.compile(
            r"\b([a-z\s-]+?)\s*(hours?|hrs?|hr|minutes?|mins?|min|seconds?|secs?|sec)\b"
        )
        for match in unit_pattern.finditer(text):
            phrase = match.group(1).strip(" -")
            unit = match.group(2)
            if not phrase or re.search(r"\d", phrase):
                continue
            value = self._words_to_number(phrase)
            if value is None:
                continue
            if unit.startswith(("hour", "hr")):
                total += value * 3600
            elif unit.startswith(("minute", "min")):
                total += value * 60
            elif unit.startswith(("second", "sec")):
                total += value
        return total

    @classmethod
    def _words_to_number(cls, text: str) -> int | None:
        text = text.lower().strip()
        text = re.sub(r"\band\b", " ", text)
        text = re.sub(r"[-]", " ", text)
        text = re.sub(r"\b(a|an)\b", "one", text)
        tokens = [tok for tok in text.split() if tok]
        if not tokens:
            return None

        units = {
            "zero": 0, "oh": 0, "one": 1, "two": 2, "three": 3, "four": 4,
            "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
            "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
            "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
            "eighteen": 18, "nineteen": 19,
        }
        tens = {
            "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
            "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
        }
        allowed = set(units) | set(tens) | {"hundred"}
        if any(tok not in allowed for tok in tokens):
            return None

        total = 0
        current = 0
        for tok in tokens:
            if tok in units:
                current += units[tok]
            elif tok in tens:
                current += tens[tok]
            elif tok == "hundred":
                current = max(1, current) * 100
        total += current
        return total if total >= 0 else None

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

    def extract_reminder_item(self, text: str) -> dict[str, str | None]:
        """Extract structured reminder details from a transcribed command."""
        original = text.strip()
        lower = original.lower()

        date = self._extract_date(lower)
        time_value = self._extract_time(lower)
        priority = self._extract_priority(lower)
        purpose = self._extract_purpose(original, remove_words=("remind", "reminder", "reminders", "me", "to", "for"))

        return {
            "title": purpose,
            "date": date,
            "formatted_date": self.format_display_date(date) if date else None,
            "time": time_value,
            "type": "reminder",
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

    def _extract_purpose(self, text: str, remove_words: tuple = ()) -> str | None:
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
        cleaned_text = text
        for word in remove_words:
            cleaned_text = re.sub(rf"\b{re.escape(word)}\b", " ", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", cleaned_text)
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
