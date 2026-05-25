from __future__ import annotations
from typing import Optional
import asyncio
import os
import re
import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.activation.confirmation_handler import ConfirmationHandler
from src.activation.wake_word_detector import WakeWordDetector
from src.calendar_module.calendar_service import CalendarService
from src.core.config import settings
from src.core.models import CommandRequest, ReminderRequest, ScheduleItemRequest, TimerRequest, MusicPlayRequest, RobotMode, Intent, EmotionState
from src.core.state import robot_state
from src.nlp.intent_classifier import IntentClassifier
from src.nlp.input_normalizer import MalaysianInputNormalizer
from src.nlp.llm_client import MalaysianLlamaClient
from src.nlp.response_generator import ResponseGenerator
from src.nlp.phrase_bank import PhraseBank
from src.productivity.music_service import MusicService
from src.productivity.timer_service import TimerService
from src.robot.jupiter_interface import get_robot_interface
from src.speech.text_to_speech import TextToSpeech
from src.vision.emotion_detector import EmotionDetector
from src.vision.speech_emotion import SpeechEmotionDetector


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
    calendar_service = CalendarService(os.getenv("JUNO_DATABASE_PATH", settings.database_path))
    llm_client = MalaysianLlamaClient()
    input_normalizer = MalaysianInputNormalizer(llm_client)
    phrase_bank = PhraseBank()
    response_generator = ResponseGenerator(calendar_service, llm_client=llm_client, phrase_bank=phrase_bank)
    timer_service = TimerService()
    music_service = MusicService()
    speech_emotion_detector = SpeechEmotionDetector()
    # The emotion model is created only when the operator explicitly enables
    # the Vision Module. This keeps the dashboard camera lightweight by default.
    emotion_detector: Optional[EmotionDetector] = None

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
            "emotion": snapshot.get("current_emotion"),
            "emotion_source": snapshot.get("emotion_source"),
            "emotion_confidence": snapshot.get("emotion_confidence"),
            "vision_backend": detector.backend_name if detector is not None else settings.vision_backend,
            "model_id": detector.model_id if detector is not None else settings.vision_model_id,
            "model_loaded": bool(detector.model_loaded) if detector is not None else False,
            "analysis_description": detector.last_description if detector is not None else "",
            "analysis_error": detector.last_error if detector is not None else None,
        }

    def _ensure_emotion_detector() -> EmotionDetector:
        nonlocal emotion_detector
        if emotion_detector is None:
            emotion_detector = EmotionDetector(use_real=True)
        return emotion_detector

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
        return _ask_for_timer_minutes()

    def _cancel_timer_setup(reason_key: str = "timer_cancelled") -> dict:
        robot_state.set_awaiting_timer_duration(False)
        robot_state.set_awaiting_timer_minutes(False)
        robot_state.set_awaiting_timer_seconds(False)
        response = phrase_bank.say(reason_key)
        robot_state.set_response(response)
        tts.speak(response)
        return {"intent": Intent.SET_TIMER, "response": response, "status": robot_state.snapshot()}

    def _extract_bare_number(text: str) -> int | None:
        t = text.lower().strip()
        t = re.sub(r"[^a-z0-9\s]", " ", t).strip()
        digit_match = re.search(r"\b(\d{1,3})\b", t)
        if digit_match:
            return int(digit_match.group(1))
        word_val = intent_classifier._words_to_number(t)
        if word_val is not None:
            return word_val
        # "none" / "no" / "nothing" → 0 seconds
        if t in {"none", "no", "nothing", "nope", "zero", "nil"}:
            return 0
        return None

    def _handle_timer_pause_resume_delete(text: str) -> dict | None:
        t = text.lower()
        if any(w in t for w in ("pause", "hold", "wait", "stop timer")):
            if timer_service.pause_timer()["paused"]:
                response = phrase_bank.say("timer_paused")
            else:
                response = phrase_bank.say("timer_already_paused")
            robot_state.set_response(response)
            tts.speak(response)
            return {"intent": Intent.SET_TIMER, "response": response, "status": robot_state.snapshot()}
        if any(w in t for w in ("resume", "continue", "unpause", "go")):
            if timer_service.resume_timer()["resumed"]:
                response = phrase_bank.say("timer_resumed")
            else:
                response = phrase_bank.say("timer_not_running")
            robot_state.set_response(response)
            tts.speak(response)
            return {"intent": Intent.SET_TIMER, "response": response, "status": robot_state.snapshot()}
        if any(w in t for w in ("delete", "reset", "cancel timer", "remove timer", "clear timer")):
            timer_service.delete_timer()
            response = phrase_bank.say("timer_deleted")
            robot_state.set_response(response)
            tts.speak(response)
            return {"intent": Intent.SET_TIMER, "response": response, "status": robot_state.snapshot()}
        return None

    def _handle_stop_command() -> dict:
        """Immediately interrupt speech and music without speaking another reply."""
        robot_state.set_awaiting_timer_duration(False)
        tts.stop()
        music_result = music_service.stop()
        response = phrase_bank.say("stop_acknowledged")
        robot_state.set_response(response)
        return {
            "intent": Intent.STOP,
            "response": response,
            "music": music_result,
            "status": robot_state.snapshot(),
        }

    def _add_schedule_from_transcript(command_text: str) -> dict:
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
            return _handle_stop_command()

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

            robot_state.set_mode(RobotMode.ACTIVE)
            robot.set_led_state("active")
            robot.open_dashboard(settings.dashboard_url)
            response = phrase_bank.say("online")
            robot_state.set_response(response)
            tts.speak(response)
            tts.speak(phrase_bank.say("prompt_help"))
            return {"intent": Intent.CONFIRM, "response": response, "status": robot_state.snapshot()}

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
                robot_state.set_mode(RobotMode.IDLE)
                response = phrase_bank.say("sleep")
                robot_state.set_response(response)
                tts.speak(response)
                return {"intent": intent, "response": response, "status": robot_state.snapshot()}

            if intent == Intent.SET_TIMER:
                duration_seconds = intent_classifier.extract_timer_duration_seconds(text)
                if duration_seconds:
                    return _start_study_timer_from_seconds(duration_seconds)
                return _ask_for_timer_duration()
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
        calendar_service.seed_from_json_if_empty(str(Path("data/sample_schedule.json")))
        robot_state.set_camera_enabled(settings.camera_enabled_default)
        robot_state.set_vision_model_enabled(settings.vision_model_enabled_default)
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
                        robot_state.set_emotion(
                            emotion,
                            source=f"vision:{detector.backend_name}",
                            confidence=detector.last_confidence or 0.60,
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

    @app.post("/api/vision/analyse")
    def analyse_current_camera_frame():
        """Run one immediate SmolVLM/vision analysis on the latest camera frame."""
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
            source=f"vision:{detector.backend_name}",
            confidence=float(analysis.get("confidence") or 0.0),
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
    def get_today_schedule():
        return calendar_service.get_today_schedule()

    @app.post("/api/schedule")
    def add_schedule_item(request: ScheduleItemRequest):
        item = calendar_service.add_schedule_item(
            title=request.title.strip(),
            date=request.date,
            time=request.time,
            type=request.type or "study",
            priority=request.priority or "medium",
        )
        robot_state.set_response(phrase_bank.say("schedule_added", purpose=item["title"], date=item.get("formatted_date") or item.get("date") or "not specified", time=item.get("time") or "not specified", priority=item.get("priority") or "medium"))
        return item

    @app.delete("/api/schedule/{item_id}")
    def delete_schedule_item(item_id: int):
        deleted = calendar_service.delete_schedule_item(item_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Schedule item not found")
        robot_state.set_response("Schedule item removed.")
        return {"deleted": True, "id": item_id}

    @app.get("/api/deadlines")
    def get_deadlines():
        return calendar_service.get_upcoming_deadlines()

    @app.get("/api/reminders")
    def get_reminders():
        return calendar_service.list_reminders()

    @app.post("/api/reminders")
    def add_reminder(request: ReminderRequest):
        reminder = calendar_service.add_reminder(
            title=request.title.strip(),
            date=request.date,
            time=request.time,
            type=request.type or "reminder",
            priority=request.priority or "medium",
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
    def delete_reminder(item_id: int):
        deleted = calendar_service.delete_reminder(item_id)
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
        return {**result, "message": response}

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
        return _handle_stop_command()

    @app.post("/api/music/refresh")
    def refresh_music():
        # The frontend refreshes the iframe cache-buster; the backend returns
        # the latest selection so the dashboard remains in sync with voice commands.
        return music_service.status()

    @app.post("/api/robot/sleep")
    def sleep_robot():
        robot_state.set_mode(RobotMode.IDLE)
        response = phrase_bank.say("direct_sleep")
        robot_state.set_response(response)
        robot.set_led_state("sleep")
        tts.speak(response)
        return robot_state.snapshot()

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
    def handle_command(request: CommandRequest):
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
