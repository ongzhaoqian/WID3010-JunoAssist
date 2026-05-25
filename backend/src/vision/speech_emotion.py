from __future__ import annotations

import re
from dataclasses import dataclass

from src.core.models import EmotionState


@dataclass(frozen=True)
class SpeechEmotionResult:
    emotion: EmotionState
    confidence: float
    reason: str


class SpeechEmotionDetector:
    """Lightweight transcript-based emotion inference for JUNO.

    The webcam model is useful for visible expression, but users can state their
    feelings directly. This detector gives explicit spoken emotion cues higher
    priority than visual inference, especially when the two conflict.
    """

    _NEGATION_RE = re.compile(r"\b(?:not|no longer|dont|don't|do not|isnt|isn't|am not|ain't|not really)\b")

    _PATTERNS: list[tuple[EmotionState, float, str, tuple[str, ...]]] = [
        (
            EmotionState.STRESSED,
            0.96,
            "explicit stress cue",
            (
                r"\bi\s*(?:am|'m|feel|feeling|felt)\s+(?:very\s+|really\s+|so\s+|quite\s+)?(?:stressed|stress|stressful|overwhelmed|anxious|worried|under pressure|pressured|panicking|panic)\b",
                r"\b(?:i have|i've got|there is|there's)\s+(?:too much|a lot of)\s+(?:stress|pressure|work)\b",
                r"\b(?:stressed|overwhelmed|anxious|worried|under pressure|panicking)\b",
            ),
        ),
        (
            EmotionState.FRUSTRATED,
            0.94,
            "explicit frustration cue",
            (
                r"\bi\s*(?:am|'m|feel|feeling|felt)\s+(?:very\s+|really\s+|so\s+|quite\s+)?(?:frustrated|annoyed|angry|irritated|fed up|stuck)\b",
                r"\b(?:frustrated|annoyed|angry|irritated|fed up|this is annoying|this is frustrating)\b",
            ),
        ),
        (
            EmotionState.TIRED,
            0.93,
            "explicit tiredness cue",
            (
                r"\bi\s*(?:am|'m|feel|feeling|felt)\s+(?:very\s+|really\s+|so\s+|quite\s+)?(?:tired|sleepy|exhausted|drained|fatigued|burnt out|burned out)\b",
                r"\b(?:tired|sleepy|exhausted|drained|fatigued|burnt out|burned out)\b",
            ),
        ),
        (
            EmotionState.HAPPY,
            0.88,
            "positive spoken cue",
            (
                r"\bi\s*(?:am|'m|feel|feeling|felt)\s+(?:very\s+|really\s+|so\s+|quite\s+)?(?:happy|good|great|excited|motivated|calm|relaxed|okay|fine|better)\b",
                r"\b(?:i'm good|i am good|feeling good|feeling great|doing well|all good|pretty good)\b",
            ),
        ),
    ]

    def infer(self, transcript: str) -> SpeechEmotionResult | None:
        text = self._normalise(transcript)
        if not text:
            return None

        for emotion, confidence, reason, patterns in self._PATTERNS:
            for pattern in patterns:
                match = re.search(pattern, text)
                if not match:
                    continue
                if self._is_negated(text, match.start()):
                    return SpeechEmotionResult(EmotionState.NEUTRAL, 0.76, "negated emotional cue")
                return SpeechEmotionResult(emotion, confidence, reason)
        return None

    @classmethod
    def _normalise(cls, value: str) -> str:
        text = value.lower().strip()
        text = text.replace("i’m", "i'm").replace("im ", "i'm ")
        text = re.sub(r"[^a-z0-9:'\s-]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _is_negated(cls, text: str, match_start: int) -> bool:
        # Only inspect a short window before the emotion word so phrases such as
        # "not stressed" do not override the visual/emotional state as stressed.
        window = text[max(0, match_start - 24):match_start]
        return bool(cls._NEGATION_RE.search(window))
