import numpy as np

from src.core.models import EmotionState
from src.vision.emotion_labels import EKMAN_EMOTIONS, LABEL_TO_INDEX, empty_distribution

ALPHA: float = 0.35
DWELL_FRAMES: int = 1

# Ordered labels — index must match the 7-class Ekman probability vector.
_LABELS = list(EKMAN_EMOTIONS)


class EMAFusion:
    """Exponential moving average over Ekman-7 facial-emotion probabilities.

    Smoothed output prevents rapid dashboard flicker while keeping all classifier
    evidence in the native Ekman taxonomy: anger, disgust, fear, happiness,
    sadness, surprise, and neutral.
    """

    def __init__(self, alpha: float = ALPHA) -> None:
        self.alpha = alpha
        self.P_t = empty_distribution(neutral=True)

    def update(self, P_ekman: np.ndarray) -> np.ndarray:
        incoming = np.asarray(P_ekman, dtype=np.float32)
        if incoming.shape != self.P_t.shape:
            raise ValueError(f"Expected Ekman probability vector of shape {self.P_t.shape}, got {incoming.shape}")
        total = float(incoming.sum())
        if total > 0:
            incoming = incoming / total
        self.P_t = self.alpha * incoming + (1.0 - self.alpha) * self.P_t
        return self.P_t.copy()

    def skip(self) -> np.ndarray:
        return self.P_t.copy()

    def reset(self) -> None:
        self.P_t = empty_distribution(neutral=True)


class HysteresisStateMachine:
    """Commits a new emotion after it leads for `dwell_frames` updates."""

    def __init__(self, dwell_frames: int = DWELL_FRAMES) -> None:
        self.dwell_frames = dwell_frames
        self.current_state: EmotionState = EmotionState.NEUTRAL
        self.candidate: EmotionState = EmotionState.NEUTRAL
        self.dwell_count: int = 0

    def update(self, P_t: np.ndarray) -> EmotionState:
        new_candidate = _LABELS[int(np.argmax(P_t))]

        if new_candidate == self.candidate:
            self.dwell_count += 1
        else:
            self.candidate = new_candidate
            self.dwell_count = 1

        if self.dwell_count >= self.dwell_frames and new_candidate != self.current_state:
            self.current_state = new_candidate
            self.dwell_count = 0

        return self.current_state
