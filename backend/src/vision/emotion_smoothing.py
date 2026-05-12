from collections import deque, Counter
from src.core.models import EmotionState


class EmotionSmoother:
    def __init__(self, window_size: int = 10) -> None:
        self.window_size = window_size
        self._window: deque[EmotionState] = deque(maxlen=window_size)

    def add(self, emotion: EmotionState) -> EmotionState:
        self._window.append(emotion)
        return self.current()

    def current(self) -> EmotionState:
        if not self._window:
            return EmotionState.UNKNOWN
        counts = Counter(self._window)
        return counts.most_common(1)[0][0]
