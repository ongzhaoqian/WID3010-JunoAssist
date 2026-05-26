from __future__ import annotations

import numpy as np

from src.core.models import EmotionState, VisionEmotionMode

# Ekman's six basic facial emotions plus neutral. UNKNOWN is intentionally kept
# out of probability vectors because it represents insufficient evidence rather
# than a classifier class.
EKMAN_EMOTIONS: tuple[EmotionState, ...] = (
    EmotionState.ANGER,
    EmotionState.DISGUST,
    EmotionState.FEAR,
    EmotionState.HAPPINESS,
    EmotionState.SADNESS,
    EmotionState.SURPRISE,
    EmotionState.NEUTRAL,
)


# Original JUNO-facing emotion mode. This is deliberately separate from
# EmotionState because Ekman labels and everyday robot-facing labels do not map
# one-to-one. The vision model stays Ekman internally, while this adapter keeps
# the previous dashboard/robot vocabulary available to users.
JUNO_EMOTIONS: tuple[str, ...] = (
    "happy",
    "sad",
    "tired",
    "frustrated",
    "stressed",
    "neutral",
)

# User-facing labels for Ekman mode. Raw Ekman labels are still preserved in
# `raw_ekman_emotion` and `raw_ekman_scores`; these labels are only for display.
EKMAN_DISPLAY_LABELS: dict[EmotionState, str] = {
    EmotionState.ANGER: "angry",
    EmotionState.DISGUST: "disgusted",
    EmotionState.FEAR: "scared",
    EmotionState.HAPPINESS: "happy",
    EmotionState.SADNESS: "sad",
    EmotionState.SURPRISE: "surprised",
    EmotionState.NEUTRAL: "neutral",
    EmotionState.UNKNOWN: "unknown",
}


def normalise_vision_mode(value: object) -> VisionEmotionMode:
    if isinstance(value, VisionEmotionMode):
        return value
    try:
        return VisionEmotionMode(str(value or VisionEmotionMode.JUNO.value).strip().lower())
    except Exception:
        return VisionEmotionMode.JUNO


def _text_contains_any(text: str | None, words: tuple[str, ...]) -> bool:
    if not text:
        return False
    normalised = str(text).lower()
    return any(word in normalised for word in words)


def ekman_to_juno_label(
    emotion: EmotionState | str | None,
    scores: dict[EmotionState, float] | None = None,
    source: str | None = None,
    speech_text: str | None = None,
) -> str:
    """Map canonical Ekman emotion evidence into JUNO's original labels.

    `tired` is not an Ekman facial expression. To avoid pretending the camera
    can reliably detect tiredness, it is only emitted when the user explicitly
    says tired/exhausted/drained, or when a future upstream module passes that
    speech cue through `speech_text`.
    """
    try:
        state = emotion if isinstance(emotion, EmotionState) else EmotionState(str(emotion or "unknown"))
    except Exception:
        state = EmotionState.UNKNOWN

    speech_text = speech_text or ""
    if source == "speech":
        if _text_contains_any(speech_text, ("tired", "sleepy", "exhausted", "drained", "fatigued", "burnt out", "burned out")):
            return "tired"
        if _text_contains_any(speech_text, ("stressed", "stress", "overwhelmed", "anxious", "worried", "pressure", "panicking", "scared", "afraid")):
            return "stressed"
        if _text_contains_any(speech_text, ("frustrated", "annoyed", "angry", "irritated", "fed up", "mad", "furious")):
            return "frustrated"
        if _text_contains_any(speech_text, ("sad", "upset", "down")):
            return "sad"
        if _text_contains_any(speech_text, ("happy", "good", "great", "excited", "motivated", "joyful")):
            return "happy"

    if state == EmotionState.HAPPINESS:
        return "happy"
    if state == EmotionState.SADNESS:
        return "sad"
    if state in {EmotionState.ANGER, EmotionState.DISGUST}:
        return "frustrated"
    if state == EmotionState.FEAR:
        return "stressed"
    if state == EmotionState.NEUTRAL:
        return "neutral"
    if state == EmotionState.SURPRISE:
        # Surprise is ambiguous in the old JUNO mode. Use secondary evidence if
        # available; otherwise keep the old label set honest by showing neutral.
        scores = scores or {}
        happiness = float(scores.get(EmotionState.HAPPINESS, 0.0) or 0.0)
        fear = float(scores.get(EmotionState.FEAR, 0.0) or 0.0)
        anger = float(scores.get(EmotionState.ANGER, 0.0) or 0.0)
        if fear >= 0.25:
            return "stressed"
        if anger >= 0.25:
            return "frustrated"
        if happiness >= 0.25:
            return "happy"
        return "neutral"
    return "unknown"


def format_emotion_for_mode(
    mode: VisionEmotionMode | str | None,
    emotion: EmotionState | str | None,
    scores: dict[EmotionState, float] | None = None,
    source: str | None = None,
    speech_text: str | None = None,
) -> str:
    selected_mode = normalise_vision_mode(mode)
    try:
        state = emotion if isinstance(emotion, EmotionState) else EmotionState(str(emotion or "unknown"))
    except Exception:
        state = EmotionState.UNKNOWN
    if selected_mode == VisionEmotionMode.EKMAN:
        return EKMAN_DISPLAY_LABELS.get(state, state.value)
    return ekman_to_juno_label(state, scores=scores, source=source, speech_text=speech_text)


LABEL_TO_INDEX: dict[EmotionState, int] = {emotion: idx for idx, emotion in enumerate(EKMAN_EMOTIONS)}


def empty_distribution(neutral: bool = True) -> np.ndarray:
    probs = np.zeros(len(EKMAN_EMOTIONS), dtype=np.float32)
    if neutral:
        probs[LABEL_TO_INDEX[EmotionState.NEUTRAL]] = 1.0
    return probs


def one_hot(emotion: EmotionState, confidence: float = 1.0) -> np.ndarray:
    confidence = float(max(0.0, min(1.0, confidence)))
    probs = np.full(len(EKMAN_EMOTIONS), (1.0 - confidence) / max(1, len(EKMAN_EMOTIONS) - 1), dtype=np.float32)
    if emotion not in LABEL_TO_INDEX:
        probs = empty_distribution(neutral=True)
    else:
        probs[LABEL_TO_INDEX[emotion]] = confidence
    total = float(probs.sum())
    if total > 0:
        probs /= total
    return probs


def normalise_emotion_label(value: object) -> EmotionState:
    try:
        return EmotionState(str(value or "unknown"))
    except Exception:
        return EmotionState.UNKNOWN


def normalise_distribution(scores: dict[EmotionState, float]) -> np.ndarray:
    probs = np.zeros(len(EKMAN_EMOTIONS), dtype=np.float32)
    for emotion, raw_score in scores.items():
        if emotion in LABEL_TO_INDEX:
            try:
                probs[LABEL_TO_INDEX[emotion]] += max(0.0, float(raw_score))
            except Exception:
                continue
    total = float(probs.sum())
    if total <= 0:
        return empty_distribution(neutral=True)
    return probs / total
