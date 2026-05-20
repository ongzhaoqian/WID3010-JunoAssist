from __future__ import annotations
from threading import Lock
from .models import RobotMode, EmotionState


class RobotState:
    def __init__(self) -> None:
        self._lock = Lock()
        self.mode = RobotMode.IDLE
        self.current_emotion = EmotionState.UNKNOWN
        self.last_response = "JUNO is waiting for the wake command."
        self.timer_remaining_seconds = 0
        self.active_timer_label = None
        self.vision_enabled = False

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "mode": self.mode,
                "current_emotion": self.current_emotion,
                "last_response": self.last_response,
                "timer_remaining_seconds": self.timer_remaining_seconds,
                "active_timer_label": self.active_timer_label,
                "vision_enabled": self.vision_enabled,
            }

    def set_mode(self, mode: RobotMode) -> None:
        with self._lock:
            self.mode = mode

    def set_emotion(self, emotion: EmotionState) -> None:
        with self._lock:
            self.current_emotion = emotion

    def set_response(self, response: str) -> None:
        with self._lock:
            self.last_response = response

    def set_vision_enabled(self, enabled: bool) -> None:
        with self._lock:
            self.vision_enabled = bool(enabled)

    def set_timer(self, seconds: int, label: str | None = None) -> None:
        with self._lock:
            self.timer_remaining_seconds = max(0, seconds)
            self.active_timer_label = label

    def decrement_timer(self) -> None:
        with self._lock:
            if self.timer_remaining_seconds > 0:
                self.timer_remaining_seconds -= 1
            if self.timer_remaining_seconds == 0:
                self.active_timer_label = None
        self.vision_enabled = False


robot_state = RobotState()
