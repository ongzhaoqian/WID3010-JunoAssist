from __future__ import annotations
from typing import Optional
import asyncio
import os
import re
import json
import time
import difflib
import threading

from fastapi import Depends, FastAPI, Header, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.activation.confirmation_handler import ConfirmationHandler
from src.activation.wake_word_detector import WakeWordDetector
from src.auth.user_service import AuthError, AuthService
from src.calendar_module.calendar_service import CalendarService
from src.core.config import settings
from src.core.models import AuthRequest, CommandRequest, ReminderRequest, ScheduleItemRequest, TimerRequest, MusicPlayRequest, VisionModeRequest, FitnessProfileRequest, FitnessSessionRequest, RobotMode, Intent, EmotionState, VisionEmotionMode
from src.core.state import robot_state
from src.nlp.intent_classifier import IntentClassifier
from src.nlp.input_normalizer import MalaysianInputNormalizer
from src.nlp.llm_client import MalaysianLlamaClient
from src.nlp.response_generator import ResponseGenerator
from src.nlp.phrase_bank import PhraseBank
from src.productivity.music_service import MusicService
from src.productivity.timer_service import TimerService
from src.productivity.fitness_service import FitnessService, FITNESS_GAME_URL
from src.robot.jupiter_interface import get_robot_interface
from src.speech.text_to_speech import TextToSpeech
from src.vision.speech_emotion import SpeechEmotionDetector
from src.system.dashboard_lifecycle import DashboardLifecycleManager


def _fuzzy_matches(word: str, candidates: list[str] | tuple[str, ...], threshold: float = 0.78) -> bool:
    """Return True when an ASR token is close enough to an expected command word."""
    clean = re.sub(r"[^a-z0-9]", "", word.lower())
    if not clean:
        return False
    for candidate in candidates:
        target = re.sub(r"[^a-z0-9]", "", candidate.lower())
        if not target:
            continue
        if clean == target or clean.startswith(target) or target.startswith(clean):
            return True
        if difflib.SequenceMatcher(None, clean, target).ratio() >= threshold:
            return True
    return False


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://0.0.0.0:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    robot = get_robot_interface()
    tts = TextToSpeech(robot)
    wake_detector = WakeWordDetector()
    confirmation_handler = ConfirmationHandler()
    intent_classifier = IntentClassifier()
    db_path = os.getenv("JUNO_DATABASE_PATH", settings.database_path)
    auth_service = AuthService(db_path)
    calendar_service = CalendarService(db_path)
    llm_client = MalaysianLlamaClient()
    input_normalizer = MalaysianInputNormalizer(llm_client)
    phrase_bank = PhraseBank()
    response_generator = ResponseGenerator(calendar_service, llm_client=llm_client, phrase_bank=phrase_bank)
    timer_service = TimerService()
    music_service = MusicService()
    fitness_service = FitnessService(db_path)

    def _database_refresh_on_start_enabled() -> bool:
        return os.getenv("JUNO_DATABASE_REFRESH_ON_START", "true").strip().lower() in {"1", "true", "yes", "y", "on"}

    def _refresh_runtime_database() -> None:
        calendar_service.reset_runtime_data()
        fitness_service.reset_runtime_data()

    # Refresh immediately when the backend app is constructed. This also makes
    # test clients and non-lifespan launch paths start from a clean database.
    if _database_refresh_on_start_enabled():
        _refresh_runtime_database()

    # Ensure the two requested demo accounts exist after any database refresh.
    auth_service.ensure_default_accounts()

    def _token_from_authorization(authorization: Optional[str]) -> Optional[str]:
        if not authorization:
            return None
        value = authorization.strip()
        if value.lower().startswith("bearer "):
            return value.split(" ", 1)[1].strip()
        return value

    def _set_active_user(user: Optional[dict]) -> None:
        user_id = int(user["id"]) if user else None
        auth_service.set_active_user(user_id)
        calendar_service.set_active_user(user_id)
        fitness_service.set_active_user(user_id)

    def _require_user(authorization: Optional[str] = Header(default=None)) -> dict:
        token = _token_from_authorization(authorization)
        user = auth_service.get_user_by_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Please log in to access this dashboard data.")
        _set_active_user(user)
        return user

    def _optional_user(authorization: Optional[str] = Header(default=None)) -> Optional[dict]:
        token = _token_from_authorization(authorization)
        user = auth_service.get_user_by_token(token)
        if user:
            _set_active_user(user)
        return user

    def _active_user_or_none() -> Optional[int]:
        return auth_service.active_user_id()

    speech_emotion_detector = SpeechEmotionDetector()
    # The emotion model is created only when the operator explicitly enables
    # the Vision Module. This keeps the dashboard camera lightweight by default.
    emotion_detector: Optional[object] = None
    dashboard_lifecycle = DashboardLifecycleManager(
        dashboard_title=settings.dashboard_window_title,
        reuse_existing=settings.dashboard_reuse_existing,
        close_browser_on_sleep=settings.dashboard_close_on_sleep,
        cleanup_enabled=settings.powerdown_cleanup_enabled,
        cleanup_patterns=(settings.powerdown_cleanup_patterns,),
        cleanup_exclude_patterns=(settings.powerdown_cleanup_exclude_patterns,),
        cleanup_grace_seconds=settings.powerdown_cleanup_grace_seconds,
    )

    def _latest_camera_jpeg() -> Optional[bytes]:
        """Return the latest ROS camera frame encoded as JPEG for the dashboard."""
        frame = robot.get_camera_frame()
        if frame is None:
            return None

        try:
            import cv2
        except Exception:
            return None

        quality = max(10, min(100, int(settings.camera_jpeg_quality)))
        ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), quality],
        )
        if not ok:
            return None
        return encoded.tobytes()

    def _camera_stream_generator():
        """MJPEG stream consumed by the React dashboard camera window.

        The raw camera stream is controlled independently from the heavier
        vision/emotion model. When the camera is off, the endpoint remains open
        but does not emit frames until the operator switches the camera on.
        """
        fps = max(1.0, min(30.0, float(settings.camera_stream_fps)))
        delay = 1.0 / fps

        while True:
            if robot_state.snapshot().get("camera_enabled"):
                jpeg = _latest_camera_jpeg()
                if jpeg:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Cache-Control: no-store\r\n\r\n" + jpeg + b"\r\n"
                    )
            time.sleep(delay)

    def _vision_status() -> dict:
        snapshot = robot_state.snapshot()
        camera_enabled = bool(snapshot.get("camera_enabled"))
        vision_model_enabled = bool(snapshot.get("vision_model_enabled"))
        detector = emotion_detector
        return {
            "camera_enabled": camera_enabled,
            "vision_model_enabled": vision_model_enabled,
            # Backwards-compatible alias; now means the emotion-recognition model.
            "enabled": vision_model_enabled,
            "frame_available": robot.get_camera_frame() is not None,
            "camera_topic": settings.camera_topic,
            "stream_fps": settings.camera_stream_fps,
            "stream_url": "/api/vision/camera/stream",
            "emotion": snapshot.get("display_emotion"),
            "display_emotion": snapshot.get("display_emotion"),
            "juno_emotion": snapshot.get("juno_emotion"),
            "raw_ekman_emotion": snapshot.get("raw_ekman_emotion"),
            "raw_ekman_scores": snapshot.get("raw_ekman_scores", {}),
            "vision_emotion_mode": snapshot.get("vision_emotion_mode", "juno"),
            "emotion_source": snapshot.get("emotion_source"),
            "emotion_confidence": snapshot.get("emotion_confidence"),
            "break_suggested": snapshot.get("break_suggested", False),
            "vision_backend": detector.backend_name if detector is not None else settings.vision_backend,
            "model_id": detector.model_id if detector is not None else settings.vision_model_id,
            "model_loaded": bool(detector.model_loaded) if detector is not None else False,
            "analysis_description": detector.last_description if detector is not None else "",
            "analysis_error": detector.last_error if detector is not None else None,
        }

    def _ensure_emotion_detector():
        # Import lazily so the normal backend can start with requirements.txt only.
        # Vision dependencies such as numpy/torch/opencv are required only when the
        # dashboard Vision Module is actually switched on.
        nonlocal emotion_detector
        if emotion_detector is None:
            from src.vision.emotion_detector import EmotionDetector
            emotion_detector = EmotionDetector(use_real=True)
        return emotion_detector

    def _schedule_powerdown_cleanup() -> None:
        if not settings.powerdown_cleanup_enabled:
            return
        timer = threading.Timer(
            max(0.0, settings.powerdown_cleanup_delay_seconds),
            dashboard_lifecycle.cleanup_powerdown_processes,
        )
        timer.daemon = True
        timer.start()

    def _activate_robot_with_dashboard() -> dict:
        robot_state.set_mode(RobotMode.ACTIVE)
        robot_state.clear_dashboard_close_request()
        robot.set_led_state("active")
        dashboard_result = dashboard_lifecycle.open_or_focus(settings.dashboard_url)
        robot_state.mark_dashboard_open()
        return dashboard_result

    def _power_down_robot(response_key: str = "sleep", speak: bool = True) -> dict:
        # Keep the backend alive so JUNO can be woken again in the same run, but
        # close/hide the dashboard and clean up auxiliary runtime processes.
        robot_state.set_mode(RobotMode.IDLE)
        robot_state.set_camera_enabled(False)
        robot_state.set_vision_model_enabled(False)
        robot_state.delete_timer()
        music_service.stop()
        robot.set_led_state("sleep")
        response = phrase_bank.say(response_key)
        robot_state.set_response(response)
        if speak:
            tts.speak(response)
        robot_state.request_dashboard_close()
        dashboard_close = dashboard_lifecycle.close_dashboard()
        _schedule_powerdown_cleanup()
        return {
            "intent": Intent.SLEEP,
            "response": response,
            "dashboard": dashboard_close,
            "status": robot_state.snapshot(),
        }

    def _apply_speech_emotion_from_text(text: str) -> None:
        """Prioritise explicit speech emotion cues over webcam-only inference."""
        result = speech_emotion_detector.infer(text)
        if result and result.confidence >= 0.70:
            robot_state.set_emotion(
                result.emotion,
                source="speech",
                confidence=result.confidence,
                speech_text=text,
            )

    def _format_timer_duration(minutes: int, seconds: int) -> str:
        parts: list[str] = []
        if minutes:
            parts.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))
        if seconds:
            parts.append(f"{seconds} second" + ("s" if seconds != 1 else ""))
        return " and ".join(parts) if parts else "0 seconds"

    def _start_study_timer_from_seconds(total_seconds: int) -> dict:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        result = timer_service.start_timer_duration(minutes=minutes, seconds=seconds)
        response = phrase_bank.say("timer_started", duration=_format_timer_duration(minutes, seconds))
        robot_state.set_response(response)
        tts.speak(response)
        return {"intent": Intent.SET_TIMER, "response": response, "timer": result, "status": robot_state.snapshot()}

    def _ask_for_timer_minutes() -> dict:
        response = phrase_bank.say("timer_ask_minutes")
        robot_state.set_awaiting_timer_minutes(True)
        robot_state.set_response(response)
        tts.speak(response)
        return {"intent": Intent.SET_TIMER, "response": response, "status": robot_state.snapshot()}

    def _ask_for_timer_seconds(minutes: int) -> dict:
        response = phrase_bank.say("timer_ask_seconds", minutes=minutes)
        robot_state.set_awaiting_timer_seconds(True, pending_minutes=minutes)
        robot_state.set_response(response)
        tts.speak(response)
        return {"intent": Intent.SET_TIMER, "response": response, "status": robot_state.snapshot()}

    def _ask_for_timer_duration() -> dict:
        # Ask once for the complete duration instead of splitting minutes and
        # seconds into two fragile speech turns. The parser accepts both full
        # answers ("five minutes thirty seconds") and bare minutes ("25").
        response = phrase_bank.say("timer_ask")
        robot_state.set_awaiting_timer_duration(True)
        robot_state.set_response(response)
        tts.speak(response)
        return {"intent": Intent.SET_TIMER, "response": response, "status": robot_state.snapshot()}

    def _cancel_timer_setup(reason_key: str = "timer_cancelled") -> dict:
        robot_state.set_awaiting_timer_duration(False)
        robot_state.set_awaiting_timer_minutes(False)
        robot_state.set_awaiting_timer_seconds(False)
        response = phrase_bank.say(reason_key)
        robot_state.set_response(response)
        tts.speak(response)
        return {"intent": Intent.SET_TIMER, "response": response, "status": robot_state.snapshot()}

    def _extract_bare_number(text: str) -> Optional[int]:
        # Legacy helper for the older two-step minute/second flow. It now uses
        # the same tolerant spoken-number parser as the single-shot duration
        # flow, so replies such as "five minutes", "make it thirty", or
        # "zero seconds" are understood.
        return intent_classifier.extract_spoken_number(text)

    _NUMBER_CONTENT_RE = re.compile(
        r"\b(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
        r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|half|quarter)\b"
    )

    def _has_number_content(text: str) -> bool:
        """Return True when text contains any digit or number word.

        Used to distinguish a real-but-unclear answer ("twenty ish", "one")
        from pure ASR noise ("what the hell is this") so that noise does not
        burn the limited attempt counter and trigger premature cancellation.
        """
        return bool(_NUMBER_CONTENT_RE.search(text.lower()))

    def _timer_is_active_or_paused() -> bool:
        snap = robot_state.snapshot()
        return snap.get("timer_remaining_seconds", 0) > 0 or bool(snap.get("timer_paused"))

    def _handle_timer_pause_resume_delete(text: str) -> Optional[dict]:
        """Handle spoken timer control while the timer is running or paused.

        The robot's ASR can produce noisy variants such as "stap timer",
        "end the countdown", or "cancel focus session". This handler favours
        explicit stop/end/cancel wording as a request to stop/delete the timer,
        while pause/resume remain available as separate controls.
        """
        _PAUSE_WORDS = ("pause", "hold", "freeze", "wait", "suspend")
        _RESUME_WORDS = ("resume", "continue", "proceed", "restart", "carry", "carryon")
        _STOP_WORDS = (
            "stop", "stopped", "stap", "end", "finish", "cancel", "delete",
            "reset", "remove", "clear", "terminate", "quit", "abort",
            "kill", "drop", "dismiss", "erase", "cancell", "cancle",
        )
        _TIMER_CONTEXT_WORDS = (
            "timer", "countdown", "clock", "pomodoro", "focus", "session",
            "study", "time", "alarm",
        )

        cleaned = re.sub(r"[^a-z0-9 ]", " ", text.lower())
        words = cleaned.split()
        joined = " ".join(words)
        snap = robot_state.snapshot()
        is_running = snap.get("timer_remaining_seconds", 0) > 0
        is_paused = bool(snap.get("timer_paused"))

        if not is_running and not is_paused:
            return None

        _OUTPUT_CONTEXT_WORDS = ("music", "song", "songs", "audio", "speech", "voice", "talking", "speaking", "tts")
        has_timer_context = any(_fuzzy_matches(w, _TIMER_CONTEXT_WORDS, threshold=0.74) for w in words)
        has_output_context = any(_fuzzy_matches(w, _OUTPUT_CONTEXT_WORDS, threshold=0.74) for w in words)
        has_stop = any(_fuzzy_matches(w, _STOP_WORDS, threshold=0.73) for w in words)
        has_pause = any(_fuzzy_matches(w, _PAUSE_WORDS, threshold=0.76) for w in words)
        has_resume = any(_fuzzy_matches(w, _RESUME_WORDS, threshold=0.76) for w in words)

        stop_phrases = (
            "stop timer", "stop the timer", "stop my timer", "end timer",
            "end the timer", "cancel timer", "cancel the timer", "delete timer",
            "reset timer", "clear timer", "stop countdown", "end countdown",
            "cancel countdown", "stop study timer", "stop focus session",
            "finish timer", "terminate timer", "turn off timer",
        )
        pause_phrases = ("pause timer", "pause the timer", "hold timer", "freeze timer")
        resume_phrases = ("resume timer", "resume the timer", "continue timer", "continue the timer")

        explicit_stop_phrase = any(phrase in joined for phrase in stop_phrases)
        explicit_pause_phrase = any(phrase in joined for phrase in pause_phrases)
        explicit_resume_phrase = any(phrase in joined for phrase in resume_phrases)

        # Stop/delete takes priority when the user explicitly mentions a timer
        # context, or when the command is a short bare stop-like command while
        # a timer is the only active countdown on the dashboard.
        short_bare_stop = has_stop and len(words) <= 3 and not has_pause and not has_resume and not has_output_context
        if explicit_stop_phrase or (has_stop and has_timer_context) or short_bare_stop:
            timer_service.delete_timer()
            response = phrase_bank.say("timer_deleted")
            robot_state.set_response(response)
            tts.speak(response)
            return {"intent": Intent.SET_TIMER, "response": response, "timer_action": "stopped", "status": robot_state.snapshot()}

        if explicit_resume_phrase or (has_resume and is_paused):
            timer_service.resume_timer()
            response = phrase_bank.say("timer_resumed")
            robot_state.set_response(response)
            tts.speak(response)
            return {"intent": Intent.SET_TIMER, "response": response, "timer_action": "resumed", "status": robot_state.snapshot()}

        if explicit_pause_phrase or (has_pause and is_running):
            timer_service.pause_timer()
            response = phrase_bank.say("timer_paused")
            robot_state.set_response(response)
            tts.speak(response)
            return {"intent": Intent.SET_TIMER, "response": response, "timer_action": "paused", "status": robot_state.snapshot()}

        if has_pause and is_paused:
            response = phrase_bank.say("timer_already_paused")
            robot_state.set_response(response)
            tts.speak(response)
            return {"intent": Intent.SET_TIMER, "response": response, "timer_action": "already_paused", "status": robot_state.snapshot()}

        return None

    def _handle_stop_command(text: str = "") -> dict:
        """Immediately interrupt speech/music; stop the timer when the command targets it."""
        robot_state.set_awaiting_timer_duration(False)
        tts.stop()
        music_result = music_service.stop()

        # If a timer is currently visible and the spoken command is stop-like,
        # honour it as a timer stop as well. This makes bare "stop" useful while
        # the countdown is running, while still supporting explicit "stop music"
        # / "stop speaking" through the same endpoint.
        lowered = text.lower().strip()
        music_or_speech_only = bool(re.search(r"\b(music|song|songs|audio|speech|voice|talking|speaking|tts)\b", lowered))
        timer_related = bool(re.search(r"\b(timer|countdown|pomodoro|focus|study|session|clock)\b", lowered))
        if _timer_is_active_or_paused() and (timer_related or not music_or_speech_only):
            timer_service.delete_timer()
            response = phrase_bank.say("timer_deleted")
        else:
            response = phrase_bank.say("stop_acknowledged")

        robot_state.set_response(response)
        return {
            "intent": Intent.STOP,
            "response": response,
            "music": music_result,
            "status": robot_state.snapshot(),
        }

    def _add_schedule_from_transcript(command_text: str) -> dict:
        active_user_id = _active_user_or_none()
        if active_user_id is None:
            response = "Please log in on the dashboard before adding schedule items."
            robot_state.set_response(response)
            tts.speak(response)
            return {"intent": Intent.ADD_SCHEDULE, "response": response, "status": robot_state.snapshot()}
        parsed = intent_classifier.extract_schedule_item(command_text)
        if not parsed.get("title"):
            response = phrase_bank.say("schedule_missing")
            robot_state.set_response(response)
            tts.speak(response)
            return {"intent": Intent.ADD_SCHEDULE, "response": response, "status": robot_state.snapshot()}

        item = calendar_service.add_schedule_item(
            title=str(parsed["title"]).strip(),
            date=parsed.get("date"),
            time=parsed.get("time"),
            type=parsed.get("type") or "study",
            priority=parsed.get("priority") or "medium",
            user_id=active_user_id,
        )
        response = phrase_bank.say(
            "schedule_added",
            purpose=item["title"],
            date=item.get("formatted_date") or item.get("date") or "not specified",
            time=item.get("time") or "not specified",
            priority=item.get("priority") or "medium",
        )
        robot_state.set_response(response)
        tts.speak(response)
        return {
            "intent": Intent.ADD_SCHEDULE,
            "response": response,
            "schedule_item": item,
            "status": robot_state.snapshot(),
        }

    def _add_reminder_from_transcript(command_text: str) -> dict:
        active_user_id = _active_user_or_none()
        if active_user_id is None:
            response = "Please log in on the dashboard before adding reminders."
            robot_state.set_response(response)
            tts.speak(response)
            return {"intent": Intent.ADD_REMINDER, "response": response, "status": robot_state.snapshot()}
        parsed = intent_classifier.extract_reminder_item(command_text)
        if not parsed.get("title"):
            response = phrase_bank.say("reminder_missing")
            robot_state.set_response(response)
            tts.speak(response)
            return {"intent": Intent.ADD_REMINDER, "response": response, "status": robot_state.snapshot()}

        item = calendar_service.add_reminder(
            title=str(parsed["title"]).strip(),
            date=parsed.get("date"),
            time=parsed.get("time"),
            type=parsed.get("type") or "reminder",
            priority=parsed.get("priority") or "medium",
            user_id=active_user_id,
        )
        response = phrase_bank.say(
            "reminder_added",
            title=item["title"],
            date=item.get("formatted_date") or item.get("date") or "not specified",
            time=item.get("time") or "not specified",
            priority=item.get("priority") or "medium",
        )
        robot_state.set_response(response)
        tts.speak(response)
        return {
            "intent": Intent.ADD_REMINDER,
            "response": response,
            "reminder": item,
            "status": robot_state.snapshot(),
        }

    def process_command_text(text: str) -> dict:
        """Shared command pipeline for dashboard text and ROS speech input.

        Speech input is transcribed by the ROS Whisper Tiny node before it
        reaches this backend. If an optional text LLM is configured, it may
        further normalise the transcript before intent classification; otherwise
        deterministic backend rules are used. Spoken responses are kept in
        British English.
        """
        raw_text = text.strip()
        text = input_normalizer.normalise(raw_text)
        intent = intent_classifier.classify(text)
        _apply_speech_emotion_from_text(text)
        snapshot = robot_state.snapshot()

        if intent == Intent.STOP:
            # Check timer control before the global stop branch so spoken
            # commands like "stop timer" or a bare "stop" during a running
            # countdown can stop the study timer instead of only interrupting
            # speech/music.
            timer_action = _handle_timer_pause_resume_delete(text)
            if timer_action:
                return timer_action
            return _handle_stop_command(text)

        if snapshot["mode"] == RobotMode.IDLE:
            if wake_detector.is_wake_command(text):
                robot_state.set_mode(RobotMode.CONFIRMATION)
                response = phrase_bank.say("wake_confirmation")
                robot_state.set_response(response)
                tts.speak(response)
                return {"intent": Intent.WAKE, "response": response, "status": robot_state.snapshot()}

            response = phrase_bank.say("idle_sleep")
            robot_state.set_response(response)
            return {"intent": intent, "response": response, "status": robot_state.snapshot()}

        if snapshot["mode"] == RobotMode.CONFIRMATION:
            _explicit_no = {"no", "nope", "nah", "cancel", "stop", "ignore", "negative", "abort"}
            _explicit_yes = {"yes", "yeah", "yep", "yup", "sure", "ok", "okay", "confirm", "go", "start", "ready", "affirmative", "please", "activate"}
            words = set(re.sub(r"[^a-z0-9 ]", "", text.lower()).split())

            # explicit rejection — reset to idle
            if words & _explicit_no:
                response = phrase_bank.say("confirmation_cancelled")
                robot_state.set_mode(RobotMode.IDLE)
                robot_state.set_response(response)
                tts.speak(response)
                return {"intent": intent, "response": response, "status": robot_state.snapshot()}

            # require explicit positive confirmation — reject hallucinated noise
            if not (words & _explicit_yes):
                return {"intent": intent, "response": snapshot["last_response"], "status": robot_state.snapshot()}

            dashboard_result = _activate_robot_with_dashboard()
            response = phrase_bank.say("online")
            robot_state.set_response(response)
            tts.speak(response)
            tts.speak(phrase_bank.say("prompt_help"))
            return {"intent": Intent.CONFIRM, "response": response, "dashboard": dashboard_result, "status": robot_state.snapshot()}

            # unreachable — kept for structure
            return {"intent": intent, "response": snapshot["last_response"], "status": robot_state.snapshot()}

        if snapshot["mode"] == RobotMode.ACTIVE:
            # --- step 1: awaiting minutes ---
            if snapshot.get("awaiting_timer_minutes"):
                if intent_classifier.is_timer_duration_cancel(text):
                    return _cancel_timer_setup("timer_cancelled")
                minutes = _extract_bare_number(text)
                if minutes is not None:
                    return _ask_for_timer_seconds(minutes)
                if not _has_number_content(text):
                    return {"intent": Intent.SET_TIMER, "response": snapshot["last_response"], "status": robot_state.snapshot()}
                attempts = robot_state.increment_timer_duration_attempts()
                if attempts >= 2:
                    return _cancel_timer_setup("timer_cancelled_after_unclear")
                response = phrase_bank.say("timer_unclear_minutes")
                robot_state.set_response(response)
                tts.speak(response)
                return {"intent": Intent.SET_TIMER, "response": response, "status": robot_state.snapshot()}

            # --- step 2: awaiting seconds ---
            if snapshot.get("awaiting_timer_seconds"):
                if intent_classifier.is_timer_duration_cancel(text):
                    return _cancel_timer_setup("timer_cancelled")
                seconds = _extract_bare_number(text)
                if seconds is not None:
                    pending_minutes = snapshot.get("timer_pending_minutes", 0)
                    total = pending_minutes * 60 + seconds
                    if total <= 0:
                        response = phrase_bank.say("timer_unclear_seconds")
                        robot_state.set_response(response)
                        tts.speak(response)
                        return {"intent": Intent.SET_TIMER, "response": response, "status": robot_state.snapshot()}
                    return _start_study_timer_from_seconds(total)
                if not _has_number_content(text):
                    return {"intent": Intent.SET_TIMER, "response": snapshot["last_response"], "status": robot_state.snapshot()}
                attempts = robot_state.increment_timer_duration_attempts()
                if attempts >= 2:
                    return _cancel_timer_setup("timer_cancelled_after_unclear")
                response = phrase_bank.say("timer_unclear_seconds")
                robot_state.set_response(response)
                tts.speak(response)
                return {"intent": Intent.SET_TIMER, "response": response, "status": robot_state.snapshot()}

            # --- legacy single-shot path (kept for API/test compatibility) ---
            if snapshot.get("awaiting_timer_duration"):
                if intent_classifier.is_timer_duration_cancel(text):
                    return _cancel_timer_setup("timer_cancelled")
                duration_seconds = intent_classifier.extract_timer_duration_seconds(text)
                if duration_seconds:
                    return _start_study_timer_from_seconds(duration_seconds)
                if intent_classifier.is_likely_different_active_intent(text):
                    robot_state.set_awaiting_timer_duration(False)
                    return process_command_text(raw_text)
                if not _has_number_content(text):
                    return {"intent": Intent.SET_TIMER, "response": snapshot["last_response"], "status": robot_state.snapshot()}
                attempts = robot_state.increment_timer_duration_attempts()
                if attempts >= 2:
                    return _cancel_timer_setup("timer_cancelled_after_unclear")
                response = phrase_bank.say("timer_unclear")
                robot_state.set_response(response)
                tts.speak(response)
                return {"intent": Intent.SET_TIMER, "response": response, "status": robot_state.snapshot()}

            # --- pause / resume / delete while timer is running or paused ---
            timer_action = _handle_timer_pause_resume_delete(text)
            if timer_action:
                return timer_action

            if intent == Intent.SLEEP:
                return _power_down_robot("sleep", speak=True)

            if intent == Intent.SET_TIMER:
                duration_seconds = intent_classifier.extract_timer_duration_seconds(text)
                if duration_seconds:
                    return _start_study_timer_from_seconds(duration_seconds)
                return _ask_for_timer_minutes()
            elif intent == Intent.ADD_SCHEDULE:
                return _add_schedule_from_transcript(text)
            elif intent == Intent.ADD_REMINDER:
                return _add_reminder_from_transcript(text)
            elif intent == Intent.CHECK_REMINDERS:
                response = response_generator.generate(
                    intent=intent,
                    emotion=snapshot["current_emotion"],
                    user_text=raw_text,
                )
                robot_state.set_response(response)
                tts.speak(response)
                return {"intent": intent, "response": response, "reminders": calendar_service.list_reminders(include_completed=False), "status": robot_state.snapshot()}
            elif intent == Intent.PLAY_MUSIC:
                music_result = music_service.play_for_emotion(snapshot.get("current_emotion", EmotionState.UNKNOWN))
                response = music_result["message"]
            else:
                response = response_generator.generate(
                    intent=intent,
                    emotion=snapshot["current_emotion"],
                    user_text=raw_text,
                )

            robot_state.set_response(response)
            is_fallback = intent == Intent.UNKNOWN and response.startswith("I am not sure how to help")
            if not is_fallback:
                tts.speak(response)
            return {"intent": intent, "response": response, "status": robot_state.snapshot()}

        response = phrase_bank.say("not_ready")
        robot_state.set_response(response)
        return {"intent": intent, "response": response, "status": robot_state.snapshot()}

    @app.on_event("startup")
    async def startup_event():
        # Start each backend run from an empty operational database. This removes
        # stale rows and avoids loading hardcoded/sample schedule data.
        if _database_refresh_on_start_enabled():
            _refresh_runtime_database()
        auth_service.ensure_default_accounts()
        robot_state.set_camera_enabled(settings.camera_enabled_default)
        robot_state.set_vision_model_enabled(settings.vision_model_enabled_default)
        robot_state.set_vision_emotion_mode(settings.vision_emotion_mode_default)
        asyncio.create_task(_emotion_monitor_loop())
        asyncio.create_task(_timer_loop())
        if settings.use_ros_robot:
            asyncio.create_task(_ros_speech_command_loop())

    async def _emotion_monitor_loop():
        while True:
            snapshot = robot_state.snapshot()
            if snapshot.get("camera_enabled") and snapshot.get("vision_model_enabled"):
                frame = robot.get_camera_frame()
                if frame is not None:
                    if not robot_state.speech_emotion_override_active(settings.speech_emotion_override_seconds):
                        detector = _ensure_emotion_detector()
                        emotion = detector.predict_from_frame(frame)
                        scores = getattr(detector.last_analysis, "scores", {}) if detector.last_analysis is not None else {}
                        robot_state.set_emotion(
                            emotion,
                            source=f"vision",
                            confidence=detector.last_confidence,
                            scores=scores,
                        )
            await asyncio.sleep(settings.emotion_update_seconds)

    async def _timer_loop():
        while True:
            completed = robot_state.decrement_timer()
            if completed:
                response = phrase_bank.say("timer_finished", label=completed.get("label") or "study timer")
                robot_state.set_response(response)
                robot.set_led_state("timer_complete")
                tts.speak(response)
            await asyncio.sleep(1)

    async def _ros_speech_command_loop():
        """Consumes transcripts published by language_pkg/transcriber.py."""
        import logging
        _log = logging.getLogger("juno.ros_loop")
        loop = asyncio.get_event_loop()
        while True:
            try:
                transcript = await loop.run_in_executor(None, robot.listen)
                if transcript:
                    process_command_text(transcript)
            except Exception as exc:
                _log.error("ROS speech loop error (continuing): %s", exc)
            await asyncio.sleep(0.05)

    @app.post("/api/auth/signup")
    def signup(request: AuthRequest):
        try:
            auth_service.create_user(request.username, request.password)
            result = auth_service.login(request.username, request.password)
            _set_active_user(result["user"])
            return result
        except AuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/auth/login")
    def login(request: AuthRequest):
        try:
            result = auth_service.login(request.username, request.password)
            _set_active_user(result["user"])
            return result
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc))

    @app.post("/api/auth/logout")
    def logout(authorization: Optional[str] = Header(default=None)):
        token = _token_from_authorization(authorization)
        if token:
            auth_service.logout(token)
        _set_active_user(None)
        return {"logged_out": True}

    @app.get("/api/auth/me")
    def auth_me(user: dict = Depends(_require_user)):
        return {"user": user}

    @app.get("/api/features")
    def get_features():
        return [
            {"name": "Today's Schedule", "description": "Check classes, meetings, deadlines, and add structured schedule items by voice."},
            {"name": "Voice Schedule Capture", "description": "Accept date, time, purpose, and priority from speech, then format dates such as 2026-05-20 as 20 May, 2026."},
            {"name": "Study Timer", "description": "Start a Pomodoro-style focus session."},
            {"name": "Dashboard Camera View", "description": "Choose when to view the Jupiter webcam directly inside the dashboard, with a refreshable MJPEG stream."},
            {"name": "Optional Vision Module", "description": "Enable emotion recognition only when needed; camera-only monitoring remains available."},
            {"name": "Break Recommendation", "description": "Suggest breaks based on emotion and workload."},
            {"name": "Whisper Tiny Speech Recognition", "description": "Lightweight Hugging Face ASR for robot microphone input, publishing recognised speech to the same backend transcript topic."},
            {"name": "Soothing Music", "description": "Play calming sounds for study support."},
            {"name": "Reminders", "description": "Add and view simple academic reminders."},
            {"name": "Fitness Game", "description": "Open the 6-7 fitness game, save scores, and estimate calories for one-off or cumulative statistics."},
        ]

    @app.get("/api/status")
    def get_status():
        return robot_state.snapshot()

    @app.get("/api/ai/status")
    def get_ai_status():
        status = response_generator.ai_status()
        status["speech_recognition"] = {
            "enabled": settings.asr_enabled,
            "model_id": settings.asr_model_id,
            "task": settings.asr_task,
            "language": settings.asr_language or None,
            "sample_rate": settings.asr_sample_rate,
            "window_seconds": settings.asr_window_seconds,
            "min_rms": settings.asr_min_rms,
            "device": settings.asr_device,
            "input_topic": "/audio/raw",
            "output_topic": "/speech/transcript",
        }
        status["text_to_speech"] = {
            "robot_interface": settings.robot_interface,
            "ros_enabled": settings.use_ros_robot,
            "tts_topic": settings.tts_topic,
            "tts_stop_topic": settings.tts_stop_topic,
            "led_topic": settings.led_topic,
            "publisher_wait_seconds": settings.tts_publisher_wait_seconds,
            "publish_retries": settings.tts_publish_retries,
        }
        status["vision_stream"] = _vision_status()
        return status

    @app.get("/api/vision/status")
    def get_vision_status():
        return _vision_status()

    @app.post("/api/vision/camera/start")
    def start_camera():
        robot_state.set_camera_enabled(True)
        return _vision_status()

    @app.post("/api/vision/camera/stop")
    def stop_camera():
        robot_state.set_camera_enabled(False)
        # Stop emotion inference too; without a live camera stream the model
        # should not continue running in the background.
        robot_state.set_vision_model_enabled(False)
        return _vision_status()

    @app.post("/api/vision/camera/refresh")
    def refresh_camera():
        # The ROS camera node continuously publishes frames. Refreshing the
        # browser stream only needs a fresh status payload; the frontend updates
        # the stream URL cache-buster.
        return _vision_status()

    @app.post("/api/vision/model/start")
    def start_vision_model():
        robot_state.set_vision_model_enabled(True)
        _ensure_emotion_detector()
        return _vision_status()

    @app.post("/api/vision/model/stop")
    def stop_vision_model():
        robot_state.set_vision_model_enabled(False)
        return _vision_status()

    @app.get("/api/vision/mode")
    def get_vision_mode():
        snapshot = robot_state.snapshot()
        return {
            "mode": snapshot.get("vision_emotion_mode", VisionEmotionMode.JUNO.value),
            "display_emotion": snapshot.get("display_emotion", "unknown"),
            "juno_emotion": snapshot.get("juno_emotion", "unknown"),
            "raw_ekman_emotion": snapshot.get("raw_ekman_emotion", EmotionState.UNKNOWN),
        }

    @app.post("/api/vision/mode")
    def set_vision_mode(request: VisionModeRequest):
        robot_state.set_vision_emotion_mode(request.mode)
        return _vision_status()

    @app.post("/api/vision/analyse")
    def analyse_current_camera_frame():
        """Run one immediate facial-expression analysis on the latest camera frame."""
        frame = robot.get_camera_frame()
        if frame is None:
            raise HTTPException(status_code=404, detail="No camera frame is currently available.")
        detector = _ensure_emotion_detector()
        analysis = detector.analyse_frame(frame)
        try:
            emotion = EmotionState(analysis.get("emotion", EmotionState.UNKNOWN.value))
        except ValueError:
            emotion = EmotionState.UNKNOWN
        robot_state.set_emotion(
            emotion,
            source=f"vision",
            confidence=float(analysis.get("confidence") or 0.0),
            scores=getattr(detector.last_analysis, "scores", {}) if detector.last_analysis is not None else {},
        )
        return {"analysis": analysis, "status": robot_state.snapshot(), "vision": _vision_status()}

    # Backwards compatibility for earlier dashboard builds. These now control
    # the emotion-recognition model, not the raw camera stream.
    @app.post("/api/vision/start")
    def start_vision():
        return start_vision_model()

    @app.post("/api/vision/stop")
    def stop_vision():
        return stop_vision_model()

    @app.get("/api/vision/camera/frame.jpg")
    def get_camera_frame_jpeg():
        jpeg = _latest_camera_jpeg()
        if jpeg is None:
            return Response(status_code=204)
        return Response(content=jpeg, media_type="image/jpeg")

    @app.get("/api/vision/camera/stream")
    def stream_camera():
        return StreamingResponse(
            _camera_stream_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @app.get("/api/schedule/today")
    def get_today_schedule(user: dict = Depends(_require_user)):
        return calendar_service.get_today_schedule(user_id=user["id"])

    @app.post("/api/schedule")
    def add_schedule_item(request: ScheduleItemRequest, user: dict = Depends(_require_user)):
        item = calendar_service.add_schedule_item(
            title=request.title.strip(),
            date=request.date,
            time=request.time,
            type=request.type or "study",
            priority=request.priority or "medium",
            user_id=user["id"],
        )
        robot_state.set_response(phrase_bank.say("schedule_added", purpose=item["title"], date=item.get("formatted_date") or item.get("date") or "not specified", time=item.get("time") or "not specified", priority=item.get("priority") or "medium"))
        return item

    @app.delete("/api/schedule/{item_id}")
    def delete_schedule_item(item_id: int, user: dict = Depends(_require_user)):
        deleted = calendar_service.delete_schedule_item(item_id, user_id=user["id"])
        if not deleted:
            raise HTTPException(status_code=404, detail="Schedule item not found")
        robot_state.set_response("Schedule item removed.")
        return {"deleted": True, "id": item_id}

    @app.get("/api/deadlines")
    def get_deadlines(user: dict = Depends(_require_user)):
        return calendar_service.get_upcoming_deadlines(user_id=user["id"])

    @app.get("/api/reminders")
    def get_reminders(user: dict = Depends(_require_user)):
        return calendar_service.list_reminders(user_id=user["id"])

    @app.post("/api/reminders")
    def add_reminder(request: ReminderRequest, user: dict = Depends(_require_user)):
        reminder = calendar_service.add_reminder(
            title=request.title.strip(),
            date=request.date,
            time=request.time,
            type=request.type or "reminder",
            priority=request.priority or "medium",
            user_id=user["id"],
        )
        robot_state.set_response(
            phrase_bank.say(
                "reminder_added",
                title=reminder["title"],
                date=reminder.get("formatted_date") or reminder.get("date") or "not specified",
                time=reminder.get("time") or "not specified",
                priority=reminder.get("priority") or "medium",
            )
        )
        return reminder

    @app.delete("/api/reminders/{item_id}")
    def delete_reminder(item_id: int, user: dict = Depends(_require_user)):
        deleted = calendar_service.delete_reminder(item_id, user_id=user["id"])
        if not deleted:
            raise HTTPException(status_code=404, detail="Reminder not found")
        robot_state.set_response(phrase_bank.say("reminder_removed"))
        return {"deleted": True, "id": item_id}

    @app.post("/api/timer/start")
    def start_timer(request: TimerRequest):
        result = timer_service.start_timer_duration(
            minutes=request.minutes,
            seconds=request.seconds,
        )
        response = phrase_bank.say("timer_started", duration=_format_timer_duration(result["minutes"], result["seconds"]))
        robot_state.set_response(response)
        return {**result, "message": response, "status": robot_state.snapshot()}

    @app.post("/api/timer/pause")
    def pause_timer():
        result = timer_service.pause_timer()
        response = phrase_bank.say("timer_paused" if result["paused"] else "timer_not_running")
        robot_state.set_response(response)
        return {**result, "message": response, "status": robot_state.snapshot()}

    @app.post("/api/timer/resume")
    def resume_timer():
        result = timer_service.resume_timer()
        response = phrase_bank.say("timer_resumed" if result["resumed"] else "timer_not_running")
        robot_state.set_response(response)
        return {**result, "message": response, "status": robot_state.snapshot()}

    @app.post("/api/timer/stop")
    def stop_timer():
        timer_service.delete_timer()
        response = phrase_bank.say("timer_deleted")
        robot_state.set_response(response)
        return {"stopped": True, "message": response, "status": robot_state.snapshot()}

    @app.post("/api/timer/delete")
    def delete_timer():
        # Alias kept for dashboard/legacy wording.
        timer_service.delete_timer()
        response = phrase_bank.say("timer_deleted")
        robot_state.set_response(response)
        return {"deleted": True, "message": response, "status": robot_state.snapshot()}

    @app.get("/api/fitness/profile")
    def get_fitness_profile(user: dict = Depends(_require_user)):
        return fitness_service.get_profile(user_id=user["id"])

    @app.post("/api/fitness/profile")
    def save_fitness_profile(request: FitnessProfileRequest, user: dict = Depends(_require_user)):
        return fitness_service.save_profile(height_m=request.height_m, weight_kg=request.weight_kg, user_id=user["id"])

    @app.get("/api/fitness/sessions")
    def get_fitness_sessions(limit: int = 20, user: dict = Depends(_require_user)):
        return fitness_service.list_sessions(limit=limit, user_id=user["id"])

    @app.post("/api/fitness/sessions")
    def add_fitness_session(request: FitnessSessionRequest, user: dict = Depends(_require_user)):
        session = fitness_service.add_session(
            score_67=request.score_67,
            source=request.source,
            duration_seconds=request.duration_seconds,
            user_id=user["id"],
        )
        robot_state.set_response(f"Fitness score saved: {session['score_67']} six-seven motions.")
        return session

    @app.get("/api/fitness/stats")
    def get_fitness_stats(scope: str = "latest", user: dict = Depends(_require_user)):
        return fitness_service.stats(scope=scope, user_id=user["id"])

    @app.get("/api/fitness/game")
    def get_fitness_game_info():
        return {
            "game_url": FITNESS_GAME_URL,
            "capture_method": "postMessage_or_manual",
            "note": "Automatic score capture depends on whether the third-party game exposes score data to the parent page. Manual score entry is kept as a reliable fallback.",
        }

    @app.get("/api/music/status")
    def get_music_status():
        return music_service.status()

    @app.post("/api/music/play")
    def play_music(request: Optional[MusicPlayRequest] = None):
        snapshot = robot_state.snapshot()
        selected_emotion = request.emotion if request and request.emotion else snapshot.get("current_emotion")
        result = music_service.play_for_emotion(selected_emotion)
        robot_state.set_response(result["message"])
        tts.speak(result["message"])
        return result

    @app.post("/api/music/stop")
    def stop_music():
        result = music_service.stop()
        robot_state.set_response(result["message"])
        return result

    @app.post("/api/robot/stop")
    def stop_robot_outputs():
        return _handle_stop_command("stop")

    @app.post("/api/music/refresh")
    def refresh_music():
        # The frontend refreshes the iframe cache-buster; the backend returns
        # the latest selection so the dashboard remains in sync with voice commands.
        return music_service.status()

    @app.post("/api/robot/sleep")
    def sleep_robot():
        return _power_down_robot("direct_sleep", speak=True)

    @app.post("/api/dashboard/closed")
    def dashboard_closed():
        robot_state.acknowledge_dashboard_closed()
        return {"acknowledged": True, "status": robot_state.snapshot()}

    @app.post("/api/dashboard/open")
    def dashboard_open():
        dashboard_result = dashboard_lifecycle.open_or_focus(settings.dashboard_url)
        robot_state.mark_dashboard_open()
        return {"dashboard": dashboard_result, "status": robot_state.snapshot()}

    @app.post("/api/robot/speak")
    def speak_robot(request: CommandRequest):
        """Direct TTS diagnostic endpoint.

        This is useful when STT works but the robot is silent: call this endpoint
        to verify the backend-to-ROS /juno/tts path independently from intent
        classification.
        """
        text = request.text.strip()
        robot_state.set_response(text)
        tts.speak(text)
        return {"message": "Speech request published", "text": text, "status": robot_state.snapshot()}

    @app.post("/api/command")
    def handle_command(request: CommandRequest, user: dict = Depends(_require_user)):
        return process_command_text(request.text)

    @app.websocket("/ws/status")
    async def websocket_status(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                await websocket.send_text(json.dumps(robot_state.snapshot(), default=str))
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            return

    return app
