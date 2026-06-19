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
    """Transcript-based emotion inference using JUNO's Ekman taxonomy.

    The vision classifier estimates facial expression. When users explicitly say
    how they feel, speech content is treated as stronger evidence. Non-Ekman
    everyday words are mapped to the closest Ekman class, e.g. stressed/anxious
    -> fear, frustrated/annoyed -> anger, tired/drained -> sadness.
    """

    _NEGATION_RE = re.compile(r"\b(?:not|no longer|dont|don't|do not|isnt|isn't|am not|ain't|not really)\b")

    _PATTERNS: list[tuple[EmotionState, float, str, tuple[str, ...]]] = [
        (
            EmotionState.FEAR,
            0.96,
            "explicit stress/anxiety cue mapped to Ekman fear",
            (
                r"\bi\s*(?:am|'m|feel|feeling|felt)\s+(?:very\s+|really\s+|so\s+|quite\s+)?(?:stressed|stress|stressful|overwhelmed|anxious|worried|under pressure|pressured|panicking|panic|scared|afraid|fearful)\b",
                r"\b(?:i have|i've got|there is|there's)\s+(?:too much|a lot of)\s+(?:stress|pressure|work)\b",
                r"\b(?:stressed|overwhelmed|anxious|worried|under pressure|panicking|scared|afraid|fearful)\b",
            ),
        ),
        (
            EmotionState.ANGER,
            0.94,
            "explicit anger/frustration cue mapped to Ekman anger",
            (
                r"\bi\s*(?:am|'m|feel|feeling|felt)\s+(?:very\s+|really\s+|so\s+|quite\s+)?(?:frustrated|annoyed|angry|irritated|fed up|mad|furious|stuck)\b",
                r"\b(?:frustrated|annoyed|angry|irritated|fed up|this is annoying|this is frustrating|mad|furious)\b",
            ),
        ),
        (
            EmotionState.SADNESS,
            0.93,
            "explicit tiredness/sadness cue mapped to Ekman sadness",
            (
                r"\bi\s*(?:am|'m|feel|feeling|felt)\s+(?:very\s+|really\s+|so\s+|quite\s+)?(?:tired|sleepy|exhausted|drained|fatigued|burnt out|burned out|sad|down|upset)\b",
                r"\b(?:tired|sleepy|exhausted|drained|fatigued|burnt out|burned out|sad|upset|down)\b",
            ),
        ),
        (
            EmotionState.DISGUST,
            0.90,
            "explicit disgust/discomfort cue",
            (
                r"\bi\s*(?:am|'m|feel|feeling|felt)\s+(?:very\s+|really\s+|so\s+|quite\s+)?(?:disgusted|grossed out|repulsed|uncomfortable)\b",
                r"\b(?:disgusted|grossed out|repulsed|that is gross|this is gross)\b",
            ),
        ),
        (
            EmotionState.SURPRISE,
            0.88,
            "explicit surprise cue",
            (
                r"\bi\s*(?:am|'m|feel|feeling|felt)\s+(?:very\s+|really\s+|so\s+|quite\s+)?(?:surprised|shocked|startled|amazed)\b",
                r"\b(?:surprised|shocked|startled|amazed|unexpected)\b",
            ),
        ),
        (
            EmotionState.HAPPINESS,
            0.88,
            "positive spoken cue mapped to Ekman happiness",
            (
                r"\bi\s*(?:am|'m|feel|feeling|felt)\s+(?:very\s+|really\s+|so\s+|quite\s+)?(?:happy|good|great|excited|motivated|calm|relaxed|okay|fine|better|joyful)\b",
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
        window = text[max(0, match_start - 24):match_start]
        return bool(cls._NEGATION_RE.search(window))
