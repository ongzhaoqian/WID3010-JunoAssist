from __future__ import annotations
import re
from datetime import datetime, timedelta
from src.core.models import Intent


class IntentClassifier:
    """Rule-based intent classifier for an undergraduate-scope prototype."""

    _PRIORITY_WORDS = {"low", "medium", "normal", "high", "urgent", "important"}
    _TYPE_WORDS = {"class", "meeting", "study", "assignment", "test", "quiz", "personal", "reminder"}

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

        # Add actions must be detected before generic check/list actions.
        if self.looks_like_schedule_add(t):
            return Intent.ADD_SCHEDULE

        if self.looks_like_reminder_add(t):
            return Intent.ADD_REMINDER

        if any(word in t for word in ["reminder", "reminders", "remind"]):
            return Intent.CHECK_REMINDERS

        if self.looks_like_timer_start(t):
            return Intent.SET_TIMER

        if any(word in t for word in ["schedule", "today", "class", "meeting"]):
            return Intent.CHECK_SCHEDULE

        if any(word in t for word in ["deadline", "due", "assignment", "test", "quiz"]):
            return Intent.CHECK_DEADLINE

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
        return has_structured_fields and "reminder" not in t

    def looks_like_reminder_add(self, text: str) -> bool:
        t = text.lower().strip()
        add_words = ("add", "create", "insert", "put", "set", "make")
        if "remind me" in t or "reminder to" in t or "reminder for" in t:
            return True
        if any(word in t for word in add_words) and "reminder" in t:
            return True
        # Structured reminder speech: "add reminder date ... time ... title ...".
        return "reminder" in t and any(field in t for field in ("date", "time", "purpose", "title", "task"))

    def looks_like_timer_start(self, text: str) -> bool:
        t = text.lower().strip()
        if "timer" in t or "pomodoro" in t or "focus session" in t:
            return True
        start_words = ("start", "set", "begin", "run", "make")
        # Accept natural speech like "start twenty five minutes" or
        # "set 1 minute 30 seconds" even when ASR drops the word "timer".
        return any(word in t for word in start_words) and self.extract_timer_duration_seconds(t) is not None

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
        - ASR-style answers such as "one thirty", "1 30", or bare "twenty five".
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

        # Handle idiomatic hour fractions before generic unit parsing so
        # "half an hour" is not also interpreted as "an hour".
        if re.search(r"\bone\s+and\s+a\s+half\s+hours?\b|\ban?\s+and\s+a\s+half\s+hours?\b", t):
            return self._clamp_duration(90 * 60, max_minutes)
        if re.search(r"\bhalf\s+(?:an?\s+)?hour\b|\bhalf\s+hour\b", t):
            return self._clamp_duration(30 * 60, max_minutes)
        if re.search(r"\b(?:a\s+)?quarter\s+(?:of\s+an?\s+)?hour\b|\bquarter\s+hour\b", t):
            return self._clamp_duration(15 * 60, max_minutes)

        # ASR often transcribes "one thirty" as "1 30" or "one thirty".
        spoken_mm_ss = self._parse_spoken_minute_second_pair(t)
        if spoken_mm_ss is not None:
            return self._clamp_duration(spoken_mm_ss, max_minutes)

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

        # Handle "one minute thirty" / "2 minutes 5" where the seconds unit is omitted.
        trailing_seconds = self._parse_trailing_seconds_after_minutes(t)
        if trailing_seconds is not None:
            total_seconds += trailing_seconds


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
            "colour": "color",
            "a hour": "an hour",
            "one-half": "one half",
            "half-hour": "half hour",
            "mins": "minutes",
            "secs": "seconds",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = re.sub(r"[^a-z0-9:.\s'-]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _sum_word_unit_durations(self, text: str) -> int:
        total = 0
        number_words = (
            "zero|oh|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
            "thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
            "thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|a|an"
        )
        unit_pattern = re.compile(
            rf"\b((?:(?:{number_words})(?:\s+|-)?)+)\s*(hours?|hrs?|hr|minutes?|mins?|min|seconds?|secs?|sec)\b"
        )
        for match in unit_pattern.finditer(text):
            phrase = match.group(1).strip(" -")
            unit = match.group(2)
            if not phrase:
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

    def _parse_trailing_seconds_after_minutes(self, text: str) -> int | None:
        digit_match = re.search(r"\b\d+(?:\.\d+)?\s*(?:minutes?|mins?|min|m)\s+(?:and\s+)?(\d{1,2})\b(?!\s*(?:seconds?|secs?|sec|s))", text)
        if digit_match:
            seconds = int(digit_match.group(1))
            return seconds if 0 <= seconds <= 59 else None

        number_words = (
            "zero|oh|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
            "thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
            "thirty|forty|fifty"
        )
        word_match = re.search(
            rf"\b(?:{number_words})(?:\s+|-)?(?:{number_words})?\s*(?:minutes?|mins?|min)\s+(?:and\s+)?((?:(?:{number_words})(?:\s+|-)?)+)\b(?!\s*(?:seconds?|secs?|sec))",
            text,
        )
        if word_match:
            seconds = self._words_to_number(word_match.group(1))
            if seconds is not None and 0 <= seconds <= 59:
                return seconds
        return None

    def _parse_spoken_minute_second_pair(self, text: str) -> int | None:
        # "1 30" -> 1 minute 30 seconds, but avoid treating "25 30" as mm:ss.
        digit_pair = re.fullmatch(r"\s*(\d{1,2})\s+(\d{1,2})\s*", text)
        if digit_pair:
            minutes = int(digit_pair.group(1))
            seconds = int(digit_pair.group(2))
            if 0 <= minutes <= 9 and 0 <= seconds <= 59:
                return minutes * 60 + seconds

        tokens = text.split()
        if len(tokens) == 2:
            first = self._words_to_number(tokens[0])
            second = self._words_to_number(tokens[1])
            if first is not None and second is not None and 0 <= first <= 9 and 10 <= second <= 59:
                return first * 60 + second
        return None

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
        """Extract structured schedule details from a transcribed command."""
        original = text.strip()
        lower = original.lower()

        date = self._extract_date(lower)
        time_value = self._extract_time(lower)
        priority = self._extract_priority(lower)
        purpose = self._extract_purpose(original, remove_words=("schedule", "calendar", "plan", "agenda", "timetable", "item"))
        item_type = self._extract_type(lower) or "study"

        return {
            "title": purpose,
            "date": date,
            "formatted_date": self.format_display_date(date) if date else None,
            "time": time_value,
            "type": item_type,
            "priority": priority or "medium",
        }

    def extract_reminder_item(self, text: str) -> dict[str, str | None]:
        """Extract structured reminder details using the same columns as schedules."""
        original = text.strip()
        lower = original.lower()

        date = self._extract_date(lower)
        time_value = self._extract_time(lower)
        priority = self._extract_priority(lower)
        purpose = self._extract_purpose(original, remove_words=("remind", "reminder", "reminders", "me", "to", "for"))
        item_type = self._extract_type(lower) or "reminder"

        return {
            "title": purpose,
            "date": date,
            "formatted_date": self.format_display_date(date) if date else None,
            "time": time_value,
            "type": item_type,
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
        if match:
            try:
                datetime.strptime(match.group(1), "%Y-%m-%d")
            except ValueError:
                return None
            return match.group(1)

        today = datetime.now().date()
        if re.search(r"\btoday\b", text):
            return today.isoformat()
        if re.search(r"\btomorrow\b", text):
            return (today + timedelta(days=1)).isoformat()
        return None

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

    def _extract_type(self, text: str) -> str | None:
        match = re.search(r"\btype\s*(?:is|:)?\s*(class|meeting|study|assignment|test|quiz|personal|reminder)\b", text)
        if match:
            return match.group(1)
        for word in self._TYPE_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", text):
                return word
        return None

    def _extract_purpose(self, text: str, remove_words: tuple[str, ...]) -> str | None:
        # Prefer explicit labelled purpose/title/task/event content.
        label_match = re.search(
            r"\b(?:purpose|title|task|event)\s*(?:is|:|for|to)?\s+(.+?)(?=\s+\b(?:date|on|time|at|priority|type)\b|$)",
            text,
            flags=re.IGNORECASE,
        )
        if label_match:
            cleaned = self._clean_purpose(label_match.group(1))
            if cleaned:
                return cleaned

        # Natural reminder style: "remind me to submit report ...".
        remind_match = re.search(
            r"\bremind\s+me\s+(?:to|about|for)?\s*(.+?)(?=\s+\b(?:date|on|time|at|priority|type)\b|$)",
            text,
            flags=re.IGNORECASE,
        )
        if remind_match:
            cleaned = self._clean_purpose(remind_match.group(1))
            if cleaned:
                return cleaned

        cleaned_text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", text)
        cleaned_text = re.sub(r"\b(?:date|on)\s*(?:is|:)?\s*", " ", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"\b(?:time|at)\s*(?:is|:)?\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b", " ", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"\bpriority\s*(?:is|:)?\s*(low|medium|normal|high|urgent|important)\b", " ", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"\btype\s*(?:is|:)?\s*(class|meeting|study|assignment|test|quiz|personal|reminder)\b", " ", cleaned_text, flags=re.IGNORECASE)
        command_words = "|".join(re.escape(word) for word in ("add", "create", "insert", "book", "put", "set", "make", *remove_words))
        cleaned_text = re.sub(rf"\b({command_words})\b", " ", cleaned_text, flags=re.IGNORECASE)
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
