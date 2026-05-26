from __future__ import annotations
from threading import Lock
import time
from .models import RobotMode, EmotionState, VisionEmotionMode
from src.vision.emotion_labels import format_emotion_for_mode, normalise_vision_mode


class RobotState:
    def __init__(self) -> None:
        self._lock = Lock()
        self.mode = RobotMode.IDLE
        self.current_emotion = EmotionState.UNKNOWN
        self.raw_ekman_emotion = EmotionState.UNKNOWN
        self.raw_ekman_scores: dict[EmotionState, float] = {}
        self.vision_emotion_mode = VisionEmotionMode.JUNO
        self.display_emotion = "unknown"
        self.juno_emotion = "unknown"
        self.last_response = "JUNO is waiting for the wake command."
        self.timer_remaining_seconds = 0
        self.active_timer_label = None
        self.awaiting_timer_duration = False
        self.awaiting_timer_minutes = False
        self.awaiting_timer_seconds = False
        self.timer_pending_minutes = 0
        self.timer_paused = False
        self.timer_paused_remaining = 0
        self.timer_duration_attempts = 0
        self.timer_completed_counter = 0
        self.last_timer_completed_label = None
        self.last_timer_completed_at = 0.0
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
                "raw_ekman_emotion": self.raw_ekman_emotion,
                "raw_ekman_scores": {key.value: float(value) for key, value in self.raw_ekman_scores.items()},
                "vision_emotion_mode": self.vision_emotion_mode.value,
                "display_emotion": self.display_emotion,
                "juno_emotion": self.juno_emotion,
                "last_response": self.last_response,
                "timer_remaining_seconds": self.timer_remaining_seconds,
                "active_timer_label": self.active_timer_label,
                "awaiting_timer_duration": self.awaiting_timer_duration,
                "awaiting_timer_minutes": self.awaiting_timer_minutes,
                "awaiting_timer_seconds": self.awaiting_timer_seconds,
                "timer_pending_minutes": self.timer_pending_minutes,
                "timer_paused": self.timer_paused,
                "timer_paused_remaining": self.timer_paused_remaining,
                "timer_duration_attempts": self.timer_duration_attempts,
                "timer_completed_counter": self.timer_completed_counter,
                "last_timer_completed_label": self.last_timer_completed_label,
                "last_timer_completed_at": self.last_timer_completed_at,
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
        scores: dict[EmotionState, float] | dict[str, float] | None = None,
    ) -> None:
        with self._lock:
            try:
                emotion_state = emotion if isinstance(emotion, EmotionState) else EmotionState(str(emotion or "unknown"))
            except Exception:
                emotion_state = EmotionState.UNKNOWN

            normalised_scores: dict[EmotionState, float] = {}
            for key, value in (scores or {}).items():
                try:
                    key_state = key if isinstance(key, EmotionState) else EmotionState(str(key))
                    normalised_scores[key_state] = float(value)
                except Exception:
                    continue

            self.current_emotion = emotion_state
            self.raw_ekman_emotion = emotion_state
            self.raw_ekman_scores = normalised_scores
            self.last_emotion_source = source
            self.emotion_confidence = float(confidence or 0.0)
            if source == "speech":
                self.last_speech_emotion_text = speech_text
                self.last_speech_emotion_at = time.monotonic()

            active_speech_text = speech_text if source == "speech" else self.last_speech_emotion_text
            self.juno_emotion = format_emotion_for_mode(
                VisionEmotionMode.JUNO,
                emotion_state,
                scores=normalised_scores,
                source=source,
                speech_text=active_speech_text,
            )
            self.display_emotion = format_emotion_for_mode(
                self.vision_emotion_mode,
                emotion_state,
                scores=normalised_scores,
                source=source,
                speech_text=active_speech_text,
            )

    def set_vision_emotion_mode(self, mode: VisionEmotionMode | str) -> None:
        with self._lock:
            self.vision_emotion_mode = normalise_vision_mode(mode)
            self.display_emotion = format_emotion_for_mode(
                self.vision_emotion_mode,
                self.raw_ekman_emotion,
                scores=self.raw_ekman_scores,
                source=self.last_emotion_source,
                speech_text=self.last_speech_emotion_text,
            )

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
                self.raw_ekman_emotion = EmotionState.UNKNOWN
                self.raw_ekman_scores = {}
                self.display_emotion = "unknown"
                self.juno_emotion = "unknown"
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
            self.awaiting_timer_minutes = False
            self.awaiting_timer_seconds = False
            self.timer_pending_minutes = 0
            self.timer_paused = False
            self.timer_paused_remaining = 0
            self.timer_duration_attempts = 0

    def pause_timer(self) -> bool:
        with self._lock:
            if self.timer_remaining_seconds <= 0 or self.timer_paused:
                return False
            self.timer_paused = True
            self.timer_paused_remaining = self.timer_remaining_seconds
            self.timer_remaining_seconds = 0
            return True

    def resume_timer(self) -> bool:
        with self._lock:
            if not self.timer_paused:
                return False
            self.timer_remaining_seconds = self.timer_paused_remaining
            self.timer_paused = False
            self.timer_paused_remaining = 0
            return True

    def delete_timer(self) -> None:
        with self._lock:
            self.timer_remaining_seconds = 0
            self.active_timer_label = None
            self.timer_paused = False
            self.timer_paused_remaining = 0
            self.awaiting_timer_duration = False
            self.awaiting_timer_minutes = False
            self.awaiting_timer_seconds = False
            self.timer_pending_minutes = 0
            self.timer_duration_attempts = 0

    def set_awaiting_timer_duration(self, awaiting: bool) -> None:
        with self._lock:
            self.awaiting_timer_duration = bool(awaiting)
            self.awaiting_timer_minutes = False
            self.awaiting_timer_seconds = False
            self.timer_pending_minutes = 0
            self.timer_duration_attempts = 0

    def set_awaiting_timer_minutes(self, awaiting: bool) -> None:
        with self._lock:
            self.awaiting_timer_minutes = bool(awaiting)
            self.awaiting_timer_seconds = False
            self.awaiting_timer_duration = False
            self.timer_duration_attempts = 0

    def set_awaiting_timer_seconds(self, awaiting: bool, pending_minutes: int = 0) -> None:
        with self._lock:
            self.awaiting_timer_seconds = bool(awaiting)
            self.awaiting_timer_minutes = False
            self.awaiting_timer_duration = False
            self.timer_pending_minutes = int(pending_minutes)
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

    def decrement_timer(self) -> dict | None:
        """Tick the active timer once and return a completion payload exactly once.

        Returning a payload lets the API loop trigger TTS and the dashboard bell
        only when the countdown transitions from 1 second to 0 seconds, instead
        of repeating the alert every loop while the timer remains at zero.
        """
        with self._lock:
            if self.timer_paused or self.timer_remaining_seconds <= 0:
                return None

            self.timer_remaining_seconds -= 1
            if self.timer_remaining_seconds > 0:
                return None

            completed_label = self.active_timer_label or "Study timer"
            self.active_timer_label = None
            self.timer_completed_counter += 1
            self.last_timer_completed_label = completed_label
            self.last_timer_completed_at = time.time()
            return {
                "label": completed_label,
                "completed_counter": self.timer_completed_counter,
                "completed_at": self.last_timer_completed_at,
            }


robot_state = RobotState()
