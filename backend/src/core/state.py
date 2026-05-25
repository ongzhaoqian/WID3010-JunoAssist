from __future__ import annotations
from threading import Lock
import time
from .models import RobotMode, EmotionState


class RobotState:
    def __init__(self) -> None:
        self._lock = Lock()
        self.mode = RobotMode.IDLE
        self.current_emotion = EmotionState.UNKNOWN
        self.last_response = "JUNO is waiting for the wake command."
        self.timer_remaining_seconds = 0
        self.active_timer_label = None
        self.awaiting_timer_duration = False
        self.timer_duration_attempts = 0
        self.last_emotion_source = "none"
        self.last_speech_emotion_text = None
        self.last_speech_emotion_at = 0.0
        self.emotion_confidence = 0.0
        # Camera stream and vision/emotion recognition are deliberately
        # controlled separately. This lets operators view the webcam without
        # loading or running the emotion-recognition model.
        self.camera_enabled = False
        self.vision_model_enabled = False
        self.music = {
            "status": "stopped",
            "provider": "spotify",
            "title": None,
            "description": None,
            "emotion": None,
            "embed_url": None,
            "external_url": None,
            "message": "No music is currently selected.",
        }

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "mode": self.mode,
                "current_emotion": self.current_emotion,
                "last_response": self.last_response,
                "timer_remaining_seconds": self.timer_remaining_seconds,
                "active_timer_label": self.active_timer_label,
                "awaiting_timer_duration": self.awaiting_timer_duration,
                "timer_duration_attempts": self.timer_duration_attempts,
                "emotion_source": self.last_emotion_source,
                "emotion_confidence": self.emotion_confidence,
                "last_speech_emotion_text": self.last_speech_emotion_text,
                "last_speech_emotion_at": self.last_speech_emotion_at,
                "camera_enabled": self.camera_enabled,
                "vision_model_enabled": self.vision_model_enabled,
                # Backwards-compatible alias for older dashboard code/tests.
                "vision_enabled": self.vision_model_enabled,
                "music": dict(self.music),
            }

    def set_mode(self, mode: RobotMode) -> None:
        with self._lock:
            self.mode = mode

    def set_emotion(
        self,
        emotion: EmotionState,
        source: str = "vision",
        confidence: float = 0.0,
        speech_text: str | None = None,
    ) -> None:
        with self._lock:
            self.current_emotion = emotion
            self.last_emotion_source = source
            self.emotion_confidence = float(confidence or 0.0)
            if source == "speech":
                self.last_speech_emotion_text = speech_text
                self.last_speech_emotion_at = time.monotonic()

    def set_response(self, response: str) -> None:
        with self._lock:
            self.last_response = response

    def set_camera_enabled(self, enabled: bool) -> None:
        with self._lock:
            self.camera_enabled = bool(enabled)

    def set_vision_model_enabled(self, enabled: bool) -> None:
        with self._lock:
            self.vision_model_enabled = bool(enabled)
            if not self.vision_model_enabled:
                self.current_emotion = EmotionState.UNKNOWN
                self.last_emotion_source = "none"
                self.emotion_confidence = 0.0

    def set_vision_enabled(self, enabled: bool) -> None:
        """Backwards-compatible helper for older routes.

        Historically, `vision_enabled` controlled both camera streaming and
        emotion inference. The dashboard now separates them, but this method is
        retained so older tests/integrations do not break.
        """
        self.set_vision_model_enabled(enabled)

    def set_timer(self, seconds: int, label: str | None = None) -> None:
        with self._lock:
            self.timer_remaining_seconds = max(0, seconds)
            self.active_timer_label = label
            self.awaiting_timer_duration = False
            self.timer_duration_attempts = 0

    def set_awaiting_timer_duration(self, awaiting: bool) -> None:
        with self._lock:
            self.awaiting_timer_duration = bool(awaiting)
            if awaiting:
                self.timer_duration_attempts = 0
            else:
                self.timer_duration_attempts = 0

    def increment_timer_duration_attempts(self) -> int:
        with self._lock:
            self.timer_duration_attempts += 1
            return self.timer_duration_attempts

    def speech_emotion_override_active(self, override_seconds: float) -> bool:
        with self._lock:
            if self.last_emotion_source != "speech" or self.last_speech_emotion_at <= 0:
                return False
            return (time.monotonic() - self.last_speech_emotion_at) <= override_seconds

    def set_music(self, payload: dict) -> None:
        with self._lock:
            self.music = {**self.music, **payload}

    def decrement_timer(self) -> None:
        with self._lock:
            if self.timer_remaining_seconds > 0:
                self.timer_remaining_seconds -= 1
            if self.timer_remaining_seconds == 0:
                self.active_timer_label = None


robot_state = RobotState()
