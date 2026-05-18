import random
from typing import Any

import numpy as np

from src.core.models import EmotionState
from .emotion_fusion import EMAFusion, HysteresisStateMachine

_MOCK_WEIGHTS = [
    EmotionState.NEUTRAL,
    EmotionState.NEUTRAL,
    EmotionState.NEUTRAL,
    EmotionState.TIRED,
    EmotionState.STRESSED,
    EmotionState.HAPPY,
    EmotionState.FRUSTRATED,
]

# One-hot Juno-5 vectors — index order must match emotion_fusion._LABELS exactly:
# [Happy=0, Neutral=1, Tired=2, Stressed=3, Frustrated=4]
_JUNO_ONE_HOT: dict = {
    EmotionState.HAPPY:      np.array([1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32),
    EmotionState.NEUTRAL:    np.array([0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32),
    EmotionState.TIRED:      np.array([0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32),
    EmotionState.STRESSED:   np.array([0.0, 0.0, 0.0, 1.0, 0.0], dtype=np.float32),
    EmotionState.FRUSTRATED: np.array([0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32),
}


class EmotionDetector:
    """Emotion detector: mock-first, upgradeable to real CNN.

    Phase 1 (MVP): weighted mock predictor  → EMA + Hysteresis smoother.
    Phase 2 (opt): face detection + CNN     → EMA + Hysteresis smoother.

    Public interface unchanged from MVP — app.py requires no modification.
    """

    def __init__(self) -> None:
        self.ema = EMAFusion()
        self.hsm = HysteresisStateMachine()

    def predict_from_frame(self, frame: Any = None) -> EmotionState:
        P_juno = self._mock_predict()
        P_t = self.ema.update(P_juno)
        return self.hsm.update(P_t)

    def _mock_predict(self) -> np.ndarray:
        mock_emotion = random.choice(_MOCK_WEIGHTS)
        return _JUNO_ONE_HOT[mock_emotion].copy()
