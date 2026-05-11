import random
from src.core.models import EmotionState
from .emotion_smoothing import EmotionSmoother


class EmotionDetector:
    """Emotion detector with mock-first behaviour.

    In a full implementation:
    1. Capture a camera frame from Jupiter Robot.
    2. Detect face using OpenCV.
    3. Crop and preprocess face.
    4. Predict emotion using a CNN model.
    5. Smooth predictions across frames.

    This version uses a weighted mock predictor so the repository runs without
    a trained model or physical robot.
    """

    def __init__(self) -> None:
        self.smoother = EmotionSmoother(window_size=8)
        self.weighted_emotions = [
            EmotionState.NEUTRAL,
            EmotionState.NEUTRAL,
            EmotionState.NEUTRAL,
            EmotionState.TIRED,
            EmotionState.STRESSED,
            EmotionState.HAPPY,
            EmotionState.FRUSTRATED,
        ]

    def predict_from_frame(self, frame=None) -> EmotionState:
        # Replace this with OpenCV + CNN model inference when ready.
        predicted = random.choice(self.weighted_emotions)
        return self.smoother.add(predicted)
