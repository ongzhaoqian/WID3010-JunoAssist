from __future__ import annotations
import difflib
import re
from datetime import datetime, timedelta
from src.core.models import Intent


class IntentClassifier:
    """Rule-based intent classifier for an undergraduate-scope prototype."""

    _MONTHS = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
        "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
    }
    _WEEKDAYS = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    _PRIORITY_WORDS = {"low", "medium", "normal", "high", "urgent", "important"}

    def classify(self, text: str) -> Intent:
        t = text.lower().strip()

        if not t:
            return Intent.UNKNOWN

        if self.is_stop_command(t):
            return Intent.STOP

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

        _TIMER_EXACT = {"timer", "pomodoro", "timmer", "tym", "tymer", "timed"}
        # "time" alone (Whisper mishearing "timer") is a timer trigger, but NOT
        # when used as a schedule/reminder field label followed by a clock value.
        _time_as_field = bool(re.search(r"\btime\s+\d{1,2}[:.]\d{2}\b", t))
        _has_timer_word = (
            any(w in t for w in ("timer", "pomodoro"))
            or any(w in t.split() for w in _TIMER_EXACT)
            or ("time" in t.split() and not _time_as_field)
        )
        if _has_timer_word:
            return Intent.SET_TIMER

        _check_reminder_phrases = ("what are my reminders", "show my reminders", "list reminders", "check reminders", "my reminders", "show reminders")
        if any(p in t for p in _check_reminder_phrases):
            return Intent.CHECK_REMINDERS

        if self._looks_like_remind_me(t) or self.looks_like_reminder_add(t):
            return Intent.ADD_REMINDER

        if self._has_remind_word(t):
            return Intent.CHECK_REMINDERS

        if any(word in t for word in ["music", "song", "songs", "sound", "relaxing", "calming"]):
            return Intent.PLAY_MUSIC

        if any(word in t for word in ["lo-fi", "lofi", "upbeat", "instrumental", "cool down", "cooldown"]):
            return Intent.PLAY_MUSIC

        if any(word in t for word in ["break", "tired", "stress", "stressed", "frustrated"]):
            return Intent.REQUEST_BREAK

        if any(phrase in t for phrase in ["what should i do", "how am i", "status"]):
            return Intent.ASK_STATUS

        return Intent.UNKNOWN

    _GENRE_KEYWORDS: list[str] = [
        "calm", "calming", "relax", "relaxing", "peaceful", "soothing", "anxiety", "stress relief",
        "happy", "upbeat", "energetic", "positive", "cheerful", "motivating",
        "focus", "study", "concentration", "lofi", "lo-fi", "instrumental", "deep work",
        "sad", "gentle", "soft", "chill", "mellow",
        "cool down", "cooldown", "reset",
    ]

    def extract_genre(self, text: str) -> str | None:
        t = text.lower().strip()
        for genre in self._GENRE_KEYWORDS:
            if genre in t:
                return genre
        return None

    def is_stop_command(self, text: str) -> bool:
        """Detect immediate interruption commands for TTS and music.

        This intentionally stays narrow so ordinary phrases like "stop by the
        office" are not treated as robot-control commands.
        """
        t = text.lower().strip()
        t = re.sub(r"[^a-z0-9\s']", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        exact_commands = {
            "stop", "please stop", "stop please", "silent", "silence",
            "be quiet", "quiet", "shush", "shut up", "pause", "pause it",
        }
        if t in exact_commands:
            return True
        stop_patterns = (
            r"^stop\s+(speaking|talking|the speech|speech|tts|voice|music|song|songs|audio|it)\b",
            r"^pause\s+(music|song|songs|audio|it)\b",
            r"^turn\s+off\s+(music|song|songs|audio|voice|speech)\b",
            r"^mute\s+(juno|john|music|audio|speech|voice)?$",
        )
        return any(re.search(pattern, t) for pattern in stop_patterns)

    def looks_like_reminder_add(self, text: str) -> bool:
        t = text.lower().strip()
        add_words = ("add", "create", "insert", "put", "set", "make")
        if self._looks_like_remind_me(t) or "reminder to" in t or "reminder for" in t:
            return True
        if any(word in t for word in add_words) and "reminder" in t:
            return True
        return "reminder" in t and any(field in t for field in ("date", "time", "purpose", "title", "task"))

    @staticmethod
    def _looks_like_remind_me(text: str) -> bool:
        """Fuzzy match for 'remind me' — accepts Whisper pronoun mishearings.

        Whisper Tiny frequently transcribes 'remind me' as 'remind us',
        'remind my', 'reminded me', etc. This checks both an explicit pronoun
        list and a SequenceMatcher ratio so novel variants are caught too.
        """
        _FIRST_PERSON = {"me", "my", "us", "i", "we", "myself", "our"}
        if re.search(r"\bremind\s+(?:me|my|us|i|we|myself|our)\b", text):
            return True
        words = text.split()
        for idx, word in enumerate(words):
            clean = re.sub(r"[^a-z]", "", word)
            if not clean:
                continue
            if difflib.SequenceMatcher(None, clean, "remind").ratio() >= 0.80:
                next_word = re.sub(r"[^a-z]", "", words[idx + 1]) if idx + 1 < len(words) else ""
                if next_word in _FIRST_PERSON or difflib.SequenceMatcher(None, next_word, "me").ratio() >= 0.65:
                    return True
        return False

    @staticmethod
    def _has_remind_word(text: str) -> bool:
        """Fuzzy detect any 'remind'/'reminder' word for CHECK_REMINDERS fallback."""
        for word in text.split():
            clean = re.sub(r"[^a-z]", "", word)
            if not clean:
                continue
            if clean in ("remind", "reminder", "reminders"):
                return True
            if len(clean) >= 5 and difflib.SequenceMatcher(None, clean, "remind").ratio() >= 0.80:
                return True
        return False

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

        This parser is intentionally tolerant because Whisper Tiny may return
        numbers as digits, words, short units, or filler-heavy phrases. Supported
        examples include:

        - "25 minutes", "for twenty five minutes", "one minute thirty seconds"
        - "1 minute 30", "two minutes five", "5 and 30"
        - "90 seconds", "1h 30m", "2:30"
        - "half an hour", "quarter of an hour", "one and a half hours"
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

        # Compact single-letter forms with no space, such as "1h 30m" or "45s".
        # Spaced/full-unit forms are handled by _sum_word_unit_durations below.
        for match in re.finditer(r"(?<![a-z0-9])(\d+(?:\.\d+)?)(h)\b", t):
            total_seconds += int(float(match.group(1)) * 3600)
        for match in re.finditer(r"(?<![a-z0-9])(\d+(?:\.\d+)?)(m)\b", t):
            total_seconds += int(float(match.group(1)) * 60)
        for match in re.finditer(r"(?<![a-z0-9])(\d+(?:\.\d+)?)(s)\b", t):
            total_seconds += int(float(match.group(1)))

        # Unit-attached digit/word forms with filler tolerance. The previous implementation
        # failed on phrases such as "for five minutes" because it tried to
        # parse the whole prefix "for five" as a number.
        total_seconds += self._sum_word_unit_durations(t)

        # Minute-plus-bare-second patterns commonly produced by speech input:
        # "1 minute 30", "one minute thirty", "two minutes and five".
        minute_trailer = self._extract_minute_then_bare_seconds(t)
        if minute_trailer is not None:
            total_seconds += minute_trailer

        # Bare "5 and 30" / "five and thirty" after the timer prompt.
        split_pair = self._extract_minute_second_pair_without_units(t)
        if split_pair is not None:
            total_seconds += split_pair

        if re.search(r"\bhalf\s+(?:an?\s+)?hour\b|\bhalf\s+hour\b", t):
            total_seconds += 30 * 60
        if re.search(r"\b(?:a\s+)?quarter\s+(?:of\s+an?\s+)?hour\b|\bquarter\s+hour\b", t):
            total_seconds += 15 * 60
        if re.search(r"\bone\s+and\s+a\s+half\s+hours?\b|\ban?\s+and\s+a\s+half\s+hours?\b", t):
            total_seconds += 90 * 60
        if re.search(r"\bhalf\s+(?:a\s+)?minute\b|\bhalf\s+min\b", t):
            total_seconds += 30

        if total_seconds:
            return self._clamp_duration(total_seconds, max_minutes)

        # A bare digit or bare number phrase is interpreted as minutes after the
        # robot has asked for the timer duration.
        bare_digit = re.fullmatch(r"\s*(\d{1,3})\s*", t)
        if bare_digit:
            return self._clamp_duration(int(bare_digit.group(1)) * 60, max_minutes)

        bare_word_number = self._words_to_number(self._extract_trailing_number_phrase(t) or t)
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
            "one-half": "one half",
            "half-hour": "half hour",
            "mins.": "mins",
            "secs.": "secs",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        # Common lightweight ASR variants seen in duration answers. Keep this
        # conservative so ordinary text is not over-corrected.
        text = re.sub(r"\bo\b", "zero", text)
        text = re.sub(r"\boh\b", "zero", text)
        text = re.sub(r"\ba hour\b", "an hour", text)
        text = re.sub(r"[^a-z0-9:.\s'-]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _sum_word_unit_durations(self, text: str) -> int:
        total = 0
        unit_pattern = re.compile(
            r"\b(hours?|hrs?|hr|h|minutes?|mins?|min|m|seconds?|secs?|sec|s)\b"
        )
        for match in unit_pattern.finditer(text):
            unit = match.group(1)
            prefix = text[: match.start()].strip()
            # Do not let the article in "quarter of an hour" become one hour;
            # that fraction is handled explicitly below.
            if re.search(r"\bquarter\s+of\s+an?\s*$", prefix):
                continue
            phrase = self._extract_trailing_number_phrase(prefix)
            if not phrase:
                continue
            value = self._number_phrase_to_value(phrase)
            if value is None:
                continue
            if unit.startswith(("hour", "hr")) or unit == "h":
                total += int(value * 3600)
            elif unit.startswith(("minute", "min")) or unit == "m":
                total += int(value * 60)
            elif unit.startswith(("second", "sec")) or unit == "s":
                total += int(value)
        return total

    def extract_spoken_number(self, text: str) -> int | None:
        """Extract a small integer from a noisy speech answer.

        Used by the legacy two-step timer flow where JUNO may ask for only the
        minute or second amount. It accepts both digits and word numbers inside
        short phrases such as "five minutes", "make it thirty", or
        "zero seconds".
        """
        t = self._normalise_duration_text(text)
        digit_match = re.search(r"\b(\d{1,3})\b", t)
        if digit_match:
            return int(digit_match.group(1))

        # Explicit zero forms for the seconds step.
        if re.search(r"\b(no|none|nothing|zero|nil)\b(?:\s+(?:extra\s+)?seconds?)?\b", t):
            return 0

        phrase = self._extract_trailing_number_phrase(t)
        value = self._number_phrase_to_value(phrase) if phrase else None
        return int(value) if value is not None else None

    def _extract_minute_then_bare_seconds(self, text: str) -> int | None:
        minute_unit = re.search(r"\b(minutes?|mins?|min)\b", text)
        if not minute_unit:
            return None

        before = text[: minute_unit.start()]
        after = text[minute_unit.end():]
        minutes_phrase = self._extract_trailing_number_phrase(before)
        minutes_value = self._number_phrase_to_value(minutes_phrase) if minutes_phrase else None
        if minutes_value is None:
            return None

        # If the seconds part already has an explicit seconds unit, it is handled
        # by _sum_word_unit_durations and should not be counted twice.
        if re.search(r"\b(seconds?|secs?|sec)\b", after):
            return None

        after = re.sub(r"^\s*(and|plus|with|then|,|-)\s+", "", after.strip())
        seconds_phrase = self._extract_leading_number_phrase(after)
        seconds_value = self._number_phrase_to_value(seconds_phrase) if seconds_phrase else 0
        # The minute part is already captured by _sum_word_unit_durations / digit
        # unit parsing, so only return the extra bare seconds here.
        return int(seconds_value or 0)

    def _extract_minute_second_pair_without_units(self, text: str) -> int | None:
        has_connector = bool(re.search(r"\b(and|plus|then|with)\b", text))
        compact = re.sub(r"\b(and|plus|then|with)\b", " ", text)
        compact = re.sub(r"\s+", " ", compact).strip()
        tokens = compact.split()
        if len(tokens) < 2 or len(tokens) > 8:
            return None

        # Numeric pair: "5 30". Limit the second part to 0..59 so "20 25"
        # is not accidentally interpreted unless it looks like a timer pair.
        digit_pair = re.fullmatch(r"(\d{1,3})\s+(\d{1,2})", compact)
        if digit_pair:
            minutes = int(digit_pair.group(1))
            seconds = int(digit_pair.group(2))
            if 0 <= seconds < 60:
                return minutes * 60 + seconds
            return None

        if not has_connector:
            return None

        # Word pair: try every split and keep a valid minutes/seconds split.
        for split_at in range(1, len(tokens)):
            left = " ".join(tokens[:split_at])
            right = " ".join(tokens[split_at:])
            minutes = self._number_phrase_to_value(left)
            seconds = self._number_phrase_to_value(right)
            if minutes is not None and seconds is not None and 0 <= seconds < 60:
                return int(minutes * 60 + seconds)
        return None

    @classmethod
    def _number_phrase_to_value(cls, phrase: str | None) -> float | None:
        if not phrase:
            return None
        phrase = phrase.strip()
        digit = re.fullmatch(r"\d+(?:\.\d+)?", phrase)
        if digit:
            return float(phrase)
        if phrase in {"half", "a half", "one half"}:
            return 0.5
        value = cls._words_to_number(phrase)
        return float(value) if value is not None else None

    @classmethod
    def _number_tokens(cls) -> set[str]:
        return {
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
            "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
            "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
            "sixty", "seventy", "eighty", "ninety", "hundred", "a", "an", "half",
        }

    @classmethod
    def _extract_trailing_number_phrase(cls, text: str) -> str | None:
        tokens = re.findall(r"\d+(?:\.\d+)?|[a-z]+", text.lower())
        if not tokens:
            return None
        keep: list[str] = []
        allowed = cls._number_tokens() | {"and"}
        for token in reversed(tokens):
            if token in allowed or re.fullmatch(r"\d+(?:\.\d+)?", token):
                keep.append(token)
                continue
            if keep:
                break
        if not keep:
            return None
        phrase = " ".join(reversed(keep)).strip()
        phrase = re.sub(r"^(and\s+)+", "", phrase).strip()
        return phrase or None

    @classmethod
    def _extract_leading_number_phrase(cls, text: str) -> str | None:
        tokens = re.findall(r"\d+(?:\.\d+)?|[a-z]+", text.lower())
        if not tokens:
            return None
        keep: list[str] = []
        allowed = cls._number_tokens() | {"and"}
        for token in tokens:
            if token in allowed or re.fullmatch(r"\d+(?:\.\d+)?", token):
                keep.append(token)
                continue
            break
        phrase = " ".join(keep).strip()
        phrase = re.sub(r"^(and\s+)+", "", phrase).strip()
        return phrase or None

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
        """Extract dates from typed or spoken Malaysian/UK-friendly formats.

        Supported examples:
        - 2026-05-25
        - 25/05/2026, 25-05-26, 25.05.2026
        - 25 May, 25 May 2026, May 25, May twenty fifth
        - twenty fifth of May
        - today, tomorrow, day after tomorrow, next Monday
        """
        raw = text.lower().strip()
        normalised = self._normalise_datetime_text(raw)
        today = datetime.now().date()

        relative_map = {
            "today": 0,
            "tonight": 0,
            "tomorrow": 1,
            "tmr": 1,
            "day after tomorrow": 2,
            "the day after tomorrow": 2,
        }
        for phrase, offset in relative_map.items():
            if re.search(rf"\b{re.escape(phrase)}\b", normalised):
                return (today + timedelta(days=offset)).strftime("%Y-%m-%d")

        weekday_match = re.search(
            r"\b(?:(next|this)\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            normalised,
        )
        if weekday_match:
            modifier = weekday_match.group(1)
            target = self._WEEKDAYS[weekday_match.group(2)]
            delta = (target - today.weekday()) % 7
            if modifier == "next" or delta == 0:
                delta = delta or 7
            return (today + timedelta(days=delta)).strftime("%Y-%m-%d")

        # ISO date first.
        match = re.search(r"\b(\d{4}-\d{1,2}-\d{1,2})\b", normalised)
        if match:
            return self._coerce_date_parts(match.group(1), "%Y-%m-%d")

        # UK/Malaysia-style numeric dates: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY.
        match = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?\b", normalised)
        if match:
            day = int(match.group(1))
            month = int(match.group(2))
            year = self._normalise_year(match.group(3)) if match.group(3) else today.year
            parsed = self._safe_date(year, month, day)
            if parsed:
                return parsed.strftime("%Y-%m-%d")

        # 25 May 2026 / 25th of May / twenty fifth of May.
        day_first_pattern = re.compile(
            r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?"
            r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
            r"aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
            r"(?:\s*,?\s*(\d{2,4}))?\b"
        )
        match = day_first_pattern.search(normalised)
        if match:
            day = int(match.group(1))
            month = self._MONTHS[match.group(2)]
            year = self._normalise_year(match.group(3)) if match.group(3) else today.year
            parsed = self._safe_date(year, month, day)
            if parsed:
                return parsed.strftime("%Y-%m-%d")

        # May 25 2026 / May twenty fifth.
        month_first_pattern = re.compile(
            r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
            r"aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
            r"\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{2,4}))?\b"
        )
        match = month_first_pattern.search(normalised)
        if match:
            month = self._MONTHS[match.group(1)]
            day = int(match.group(2))
            year = self._normalise_year(match.group(3)) if match.group(3) else today.year
            parsed = self._safe_date(year, month, day)
            if parsed:
                return parsed.strftime("%Y-%m-%d")

        return None

    def _extract_time(self, text: str) -> str | None:
        """Extract clock time from typed or spoken forms.

        Supported examples:
        - 15:30, 1530, 3pm, 3:30 pm
        - nine p m, nine thirty, twenty one thirty
        - half past nine, quarter past five, quarter to six
        - noon, midday, midnight, morning, afternoon, evening
        """
        normalised = self._normalise_datetime_text(text.lower().strip())

        if re.search(r"\b(noon|midday)\b", normalised):
            return "12:00"
        if re.search(r"\bmidnight\b", normalised):
            return "00:00"

        # Natural approximations for cases where speech gets the exact time poorly.
        approximate_times = {
            "morning": "09:00",
            "afternoon": "14:00",
            "evening": "19:00",
            "night": "20:00",
            "tonight": "20:00",
        }
        for phrase, value in approximate_times.items():
            if re.search(rf"\b{phrase}\b", normalised) and not re.search(r"\d", normalised):
                return value

        # half past nine, quarter past five, quarter to six.
        relative_match = re.search(r"\b(half|quarter)\s+(past|to)\s+(\d{1,2}|[a-z\s-]{3,30}?)\s*(am|pm)?\b", normalised)
        if relative_match:
            kind, direction, hour_text, meridiem = relative_match.groups()
            hour = int(hour_text) if hour_text.strip().isdigit() else self._words_to_number(hour_text.strip())
            if hour is None:
                return None
            minute = 30 if kind == "half" else 15
            if direction == "to":
                hour -= 1
                minute = 45
            return self._format_time(hour, minute, meridiem)

        # 15:30, 3.30 pm, at 9:05, time is 21:00.
        labelled = re.search(r"\b(?:time|at|by|before|around|about)\s*(?:is|:)?\s*(\d{1,2})(?::|\.)(\d{2})\s*(am|pm)?\b", normalised)
        generic = re.search(r"\b(\d{1,2})(?::|\.)(\d{2})\s*(am|pm)?\b", normalised)
        match = labelled or generic
        if match:
            return self._format_time(int(match.group(1)), int(match.group(2)), match.group(3))

        # 1530 / 2130, normally after labelled markers or four compact digits.
        compact = re.search(r"\b(?:time|at|by|before|around|about)\s*(?:is|:)?\s*(\d{3,4})\s*(am|pm)?\b", normalised)
        if compact:
            digits = compact.group(1)
            if len(digits) == 3:
                hour, minute = int(digits[0]), int(digits[1:])
            else:
                hour, minute = int(digits[:2]), int(digits[2:])
            formatted = self._format_time(hour, minute, compact.group(2))
            if formatted:
                return formatted

        # 9 pm / nine pm / at nine / nine thirty / twenty one thirty.
        words_or_number = re.search(
            r"\b(?:time|at|by|before|around|about)?\s*"
            r"(\d{1,2}|[a-z\s-]{3,40}?)"
            r"(?:\s+(\d{1,2}|[a-z\s-]{3,30}))?\s*(am|pm)?\b",
            normalised,
        )
        candidates = self._time_candidates_from_text(normalised)
        if candidates:
            return candidates[0]

        # Fall back to rough time-of-day if mentioned alongside a date command.
        for phrase, value in approximate_times.items():
            if re.search(rf"\b{phrase}\b", normalised):
                return value

        return None

    @classmethod
    def _normalise_datetime_text(cls, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"\b([ap])\s*\.?\s*m\.?\b", r"\1m", text)
        text = text.replace("o'clock", " ").replace("oclock", " ")
        text = text.replace("half-past", "half past").replace("quarter-past", "quarter past")
        text = text.replace("quarter-to", "quarter to")
        text = re.sub(r"[,]+", " ", text)
        text = re.sub(r"\s+", " ", text)

        ordinal_phrases = {
            "thirty first": 31, "thirtieth": 30, "twenty ninth": 29,
            "twenty eighth": 28, "twenty seventh": 27, "twenty sixth": 26,
            "twenty fifth": 25, "twenty fourth": 24, "twenty third": 23,
            "twenty second": 22, "twenty first": 21, "twentieth": 20,
            "nineteenth": 19, "eighteenth": 18, "seventeenth": 17,
            "sixteenth": 16, "fifteenth": 15, "fourteenth": 14,
            "thirteenth": 13, "twelfth": 12, "eleventh": 11, "tenth": 10,
            "ninth": 9, "eighth": 8, "seventh": 7, "sixth": 6,
            "fifth": 5, "fourth": 4, "third": 3, "second": 2, "first": 1,
        }
        for phrase, value in sorted(ordinal_phrases.items(), key=lambda item: len(item[0]), reverse=True):
            text = re.sub(rf"\b{re.escape(phrase)}\b", str(value), text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _normalise_year(value: str | None) -> int:
        if not value:
            return datetime.now().year
        year = int(value)
        if year < 100:
            return 2000 + year if year < 70 else 1900 + year
        return year

    @staticmethod
    def _safe_date(year: int, month: int, day: int):
        try:
            return datetime(year, month, day).date()
        except ValueError:
            return None

    def _coerce_date_parts(self, value: str, fmt: str) -> str | None:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            # Allow non-zero-padded ISO values like 2026-5-25.
            if fmt == "%Y-%m-%d":
                parts = value.split("-")
                if len(parts) == 3:
                    parsed = self._safe_date(int(parts[0]), int(parts[1]), int(parts[2]))
                    return parsed.strftime("%Y-%m-%d") if parsed else None
            return None

    def _time_candidates_from_text(self, text: str) -> list[str]:
        candidates: list[str] = []
        implied_meridiem = None
        if re.search(r"\b(afternoon|evening|night|tonight)\b", text):
            implied_meridiem = "pm"
        elif re.search(r"\bmorning\b", text):
            implied_meridiem = "am"

        # Context-labelled phrases: "at nine thirty", "time nine pm".
        context_pattern = re.compile(
            r"\b(?:time|at|by|before|around|about)\s+(?:is\s+)?"
            r"([a-z0-9\s-]{1,45}?)(?=\s+\b(?:date|on|purpose|title|task|event|priority|for|to)\b|$)"
        )
        for match in context_pattern.finditer(text):
            parsed = self._parse_time_phrase(match.group(1), implied_meridiem=implied_meridiem)
            if parsed and parsed not in candidates:
                candidates.append(parsed)

        # Phrases with explicit meridiem can stand without context.
        meridiem_pattern = re.compile(r"\b([a-z0-9\s-]{1,35}?)\s+(am|pm)\b")
        for match in meridiem_pattern.finditer(text):
            parsed = self._parse_time_phrase(match.group(1) + " " + match.group(2))
            if parsed and parsed not in candidates:
                candidates.append(parsed)

        return candidates

    def _parse_time_phrase(self, phrase: str, implied_meridiem: str | None = None) -> str | None:
        phrase = phrase.lower().strip()
        phrase = re.sub(r"\b(?:in the|this|tomorrow|today|tonight|morning|afternoon|evening|night)\b", " ", phrase)
        phrase = re.sub(r"\b(?:sharp|exactly|please)\b", " ", phrase)
        phrase = re.sub(r"\s+", " ", phrase).strip()
        if not phrase:
            return None

        meridiem_match = re.search(r"\b(am|pm)\b", phrase)
        meridiem = meridiem_match.group(1) if meridiem_match else implied_meridiem
        phrase = re.sub(r"\b(am|pm)\b", " ", phrase)
        phrase = re.sub(r"\s+", " ", phrase).strip()

        # Direct number phrases, e.g. 9, 930, 21 30.
        if re.fullmatch(r"\d{1,2}", phrase):
            return self._format_time(int(phrase), 0, meridiem)
        if re.fullmatch(r"\d{3,4}", phrase):
            hour = int(phrase[:-2])
            minute = int(phrase[-2:])
            return self._format_time(hour, minute, meridiem)
        digits = re.findall(r"\d{1,2}", phrase)
        if digits:
            hour = int(digits[0])
            minute = int(digits[1]) if len(digits) >= 2 else 0
            return self._format_time(hour, minute, meridiem)

        tokens = [tok for tok in re.split(r"\s+", phrase) if tok]
        if not tokens:
            return None

        # One number-word phrase: "nine".
        full_value = self._words_to_number(" ".join(tokens))
        if full_value is not None and 0 <= full_value <= 23:
            return self._format_time(full_value, 0, meridiem)

        # Two-part number-word phrase: "nine thirty", "twenty one thirty".
        for split in range(1, len(tokens)):
            hour = self._words_to_number(" ".join(tokens[:split]))
            minute = self._words_to_number(" ".join(tokens[split:]))
            if hour is None or minute is None:
                continue
            formatted = self._format_time(hour, minute, meridiem)
            if formatted:
                return formatted
        return None

    @staticmethod
    def _format_time(hour: int, minute: int, meridiem: str | None = None) -> str | None:
        if meridiem:
            meridiem = meridiem.lower()
            if hour == 12 and meridiem == "am":
                hour = 0
            elif meridiem == "pm" and hour < 12:
                hour += 12
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
        cleaned_text = self._remove_datetime_phrases(cleaned_text)
        cleaned_text = re.sub(r"\bpriority\s*(?:is|:)?\s*(low|medium|normal|high|urgent|important)\b", " ", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"\b(add|create|insert|book|put|set|schedule|calendar|plan|agenda|timetable|item)\b", " ", cleaned_text, flags=re.IGNORECASE)
        return self._clean_purpose(cleaned_text)


    def _remove_datetime_phrases(self, text: str) -> str:
        month_names = "jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
        patterns = [
            r"\b\d{4}-\d{1,2}-\d{1,2}\b",
            r"\b\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?\b",
            rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:{month_names})(?:\s+\d{{2,4}})?\b",
            rf"\b(?:{month_names})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s+\d{{2,4}})?\b",
            r"\b(today|tomorrow|tonight|tmr|day after tomorrow|the day after tomorrow|next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|this\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
            r"\b(?:date|on)\s*(?:is|:)?\s*",
            r"\b(?:time|at|by|before|around|about)\s*(?:is|:)?\s*\d{1,2}(?::|\.)?\d{0,2}\s*(?:a\s*m|p\s*m|am|pm)?\b",
            r"\b(?:time|at|by|before|around|about)\s+(?:is\s+)?(?:half|quarter)\s+(?:past|to)\s+[a-z0-9\s-]+",
            r"\b(?:time|at|by|before|around|about)\s+(?:is\s+)?[a-z0-9\s-]{1,35}?\s*(?:a\s*m|p\s*m|am|pm)\b",
            r"\b(noon|midday|midnight|morning|afternoon|evening|night)\b",
        ]
        cleaned = self._normalise_datetime_text(text)
        for pattern in patterns:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", cleaned).strip()

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
