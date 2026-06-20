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
        self.dashboard_should_close = False
        self.dashboard_open = False
        self.dashboard_session_id = 0
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
        self.active_timer_type = "study"
        self.stress_started_at = 0.0
        self.awaiting_break_confirmation = False
        self.break_confirmation_reason: str | None = None
        self.study_timer_stashed = False
        self.stashed_study_remaining = 0
        self.stashed_study_label: str | None = None
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
                "dashboard_should_close": self.dashboard_should_close,
                "dashboard_open": self.dashboard_open,
                "dashboard_session_id": self.dashboard_session_id,
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
                "active_timer_type": self.active_timer_type,
                "awaiting_break_confirmation": self.awaiting_break_confirmation,
                "break_confirmation_reason": self.break_confirmation_reason,
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

    def mark_dashboard_open(self) -> None:
        with self._lock:
            self.dashboard_open = True
            self.dashboard_should_close = False
            self.dashboard_session_id += 1

    def request_dashboard_close(self) -> None:
        with self._lock:
            self.dashboard_open = False
            self.dashboard_should_close = True
            self.dashboard_session_id += 1

    def acknowledge_dashboard_closed(self) -> None:
        with self._lock:
            self.dashboard_open = False

    def clear_dashboard_close_request(self) -> None:
        with self._lock:
            self.dashboard_should_close = False
            self.dashboard_open = True

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
            self.active_timer_type = "study"
            self.awaiting_timer_duration = False
            self.awaiting_timer_minutes = False
            self.awaiting_timer_seconds = False
            self.timer_pending_minutes = 0
            self.timer_paused = False
            self.timer_paused_remaining = 0
            self.timer_duration_attempts = 0
            self.study_timer_stashed = False
            self.stashed_study_remaining = 0
            self.stashed_study_label = None
            self.awaiting_break_confirmation = False
            self.break_confirmation_reason = None

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
            self.active_timer_type = "study"
            self.timer_paused = False
            self.timer_paused_remaining = 0
            self.awaiting_timer_duration = False
            self.awaiting_timer_minutes = False
            self.awaiting_timer_seconds = False
            self.timer_pending_minutes = 0
            self.timer_duration_attempts = 0
            self.study_timer_stashed = False
            self.stashed_study_remaining = 0
            self.stashed_study_label = None
            self.awaiting_break_confirmation = False
            self.break_confirmation_reason = None

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
            completed_type = self.active_timer_type
            self.active_timer_label = None
            self.timer_completed_counter += 1
            self.last_timer_completed_label = completed_label
            self.last_timer_completed_at = time.time()

            # A break timer that completes while a study timer is stashed
            # underneath it (the user said "yes" to a break mid-session)
            # should hand control straight back to that study timer instead
            # of leaving everything idle.
            resumed_study = False
            if completed_type == "break" and self.study_timer_stashed:
                self.timer_remaining_seconds = self.stashed_study_remaining
                self.active_timer_label = self.stashed_study_label
                self.study_timer_stashed = False
                self.stashed_study_remaining = 0
                self.stashed_study_label = None
                self.active_timer_type = "study"
                resumed_study = True
            else:
                self.active_timer_type = "study"

            return {
                "label": completed_label,
                "timer_type": completed_type,
                "completed_counter": self.timer_completed_counter,
                "completed_at": self.last_timer_completed_at,
                "resumed_study": resumed_study,
            }

    def update_stress_tracking(self, in_stress_class: bool, threshold_seconds: float) -> bool:
        """Track continuous vision-detected stress and signal once per episode.

        Returns True exactly once, when sustained stress first crosses
        `threshold_seconds`. Leaving the stress class (even for a single
        frame) resets the counter, so "continuously" is interpreted strictly.
        """
        with self._lock:
            if not in_stress_class:
                self.stress_started_at = 0.0
                return False

            if self.awaiting_break_confirmation:
                # Already asking about a break; do not restart or re-signal.
                return False

            if self.stress_started_at <= 0:
                self.stress_started_at = time.monotonic()
                return False

            elapsed = time.monotonic() - self.stress_started_at
            return elapsed >= threshold_seconds

    def request_break_confirmation(self, reason: str) -> None:
        """Ask the user whether they want a break, freezing a running study timer.

        Freezing happens immediately when the question is asked (not when the
        user answers), so the study countdown stops for the duration of the
        question rather than continuing to run underneath it. The frozen
        remaining time is kept in a dedicated stash (distinct from the normal
        pause/resume fields) so a later break timer can use the live
        timer_remaining_seconds slot without losing track of it.
        """
        with self._lock:
            self.awaiting_break_confirmation = True
            self.break_confirmation_reason = reason
            if (
                reason == "stress"
                and self.active_timer_type == "study"
                and self.timer_remaining_seconds > 0
                and not self.timer_paused
                and not self.study_timer_stashed
            ):
                self.study_timer_stashed = True
                self.stashed_study_remaining = self.timer_remaining_seconds
                self.stashed_study_label = self.active_timer_label
                self.timer_remaining_seconds = 0

    def clear_break_confirmation(self) -> None:
        with self._lock:
            self.awaiting_break_confirmation = False
            self.break_confirmation_reason = None

    def accept_break(self, seconds: int, label: str) -> None:
        """Start the break timer. Any stashed study timer stays frozen underneath."""
        with self._lock:
            self.timer_remaining_seconds = max(0, seconds)
            self.active_timer_label = label
            self.active_timer_type = "break"
            self.awaiting_break_confirmation = False
            self.break_confirmation_reason = None

    def decline_break(self) -> bool:
        """Resume a study timer that was frozen for the question, if any.

        Returns True if a stashed study timer was resumed.
        """
        with self._lock:
            resumed = False
            if self.study_timer_stashed:
                self.timer_remaining_seconds = self.stashed_study_remaining
                self.active_timer_label = self.stashed_study_label
                self.active_timer_type = "study"
                self.study_timer_stashed = False
                self.stashed_study_remaining = 0
                self.stashed_study_label = None
                resumed = True
            self.awaiting_break_confirmation = False
            self.break_confirmation_reason = None
            return resumed


robot_state = RobotState()
