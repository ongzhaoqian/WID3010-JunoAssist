import numpy as np

from src.core.models import EmotionState

ALPHA: float = 0.30
DWELL_FRAMES: int = 45

# Ordered labels — index must match probability vector positions used throughout this module
_LABELS = [
    EmotionState.HAPPY,       # index 0
    EmotionState.NEUTRAL,     # index 1
    EmotionState.TIRED,       # index 2
    EmotionState.STRESSED,    # index 3
    EmotionState.FRUSTRATED,  # index 4
]


class EMAFusion:
    """Exponential Moving Average over the 5-class Juno emotion probability distribution.

    Retains uncertainty across frames. α=0.30 weights recent frames ~1.4× more than
    older ones while providing smooth output. Initialises to Neutral.
    """

    def __init__(self, alpha: float = ALPHA) -> None:
        self.alpha = alpha
        # P_t[1] = Neutral = 1.0 on start
        self.P_t = np.array([0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    def update(self, P_juno: np.ndarray) -> np.ndarray:
        """Blend new Juno-5 probability vector into the running estimate."""
        self.P_t = self.alpha * P_juno + (1.0 - self.alpha) * self.P_t
        return self.P_t.copy()

    def skip(self) -> np.ndarray:
        """Call when face detection fails — distribution held, not updated."""
        return self.P_t.copy()

    def reset(self) -> None:
        self.P_t = np.array([0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)


class HysteresisStateMachine:
    """Commits a new emotion only after it leads argmax for DWELL_FRAMES consecutive frames.

    Prevents the displayed emotion from flickering between adjacent states (e.g.
    Neutral ↔ Tired) due to momentary changes in a single frame.
    """

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

        if (self.dwell_count >= self.dwell_frames
                and new_candidate != self.current_state):
            self.current_state = new_candidate
            self.dwell_count = 0

        return self.current_state
