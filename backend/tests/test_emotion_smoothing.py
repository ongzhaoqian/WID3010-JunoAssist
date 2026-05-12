from src.vision.emotion_smoothing import EmotionSmoother
from src.core.models import EmotionState


def test_emotion_smoother_returns_majority():
    smoother = EmotionSmoother(window_size=5)
    smoother.add(EmotionState.TIRED)
    smoother.add(EmotionState.NEUTRAL)
    smoother.add(EmotionState.NEUTRAL)
    assert smoother.current() == EmotionState.NEUTRAL
