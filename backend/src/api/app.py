import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.activation.confirmation_handler import ConfirmationHandler
from src.activation.wake_word_detector import WakeWordDetector
from src.calendar_module.calendar_service import CalendarService
from src.core.config import settings
from src.core.models import CommandRequest, ReminderRequest, TimerRequest, RobotMode, Intent
from src.core.state import robot_state
from src.nlp.intent_classifier import IntentClassifier
from src.nlp.input_normalizer import MalaysianInputNormalizer
from src.nlp.llm_client import MalaysianLlamaClient
from src.nlp.response_generator import ResponseGenerator
from src.productivity.music_service import MusicService
from src.productivity.timer_service import TimerService
from src.robot.jupiter_interface import get_robot_interface
from src.speech.text_to_speech import TextToSpeech
from src.vision.emotion_detector import EmotionDetector


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
    calendar_service = CalendarService(settings.database_path)
    llm_client = MalaysianLlamaClient()
    input_normalizer = MalaysianInputNormalizer(llm_client)
    response_generator = ResponseGenerator(calendar_service, llm_client=llm_client)
    timer_service = TimerService()
    music_service = MusicService()
    emotion_detector = EmotionDetector(use_real=True)

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
        snapshot = robot_state.snapshot()

        if snapshot["mode"] == RobotMode.IDLE:
            if wake_detector.is_wake_command(text):
                robot_state.set_mode(RobotMode.CONFIRMATION)
                response = (
                    "Are you sure you would like to power Juno on? "
                    "Answer yes if you do, else ignore."
                )
                robot_state.set_response(response)
                tts.speak(response)
                return {"intent": Intent.WAKE, "response": response, "status": robot_state.snapshot()}

            response = "JUNO is sleeping. Say Hey, John to wake me up."
            robot_state.set_response(response)
            return {"intent": intent, "response": response, "status": robot_state.snapshot()}

        if snapshot["mode"] == RobotMode.CONFIRMATION:
            _explicit_no = {"no", "nope", "nah", "cancel", "stop", "ignore", "negative", "abort"}
            words = set(text.lower().split())

            # explicit rejection — reset to idle
            if words & _explicit_no:
                response = "Confirmation not received. JUNO will return to idle mode."
                robot_state.set_mode(RobotMode.IDLE)
                robot_state.set_response(response)
                tts.speak(response)
                return {"intent": intent, "response": response, "status": robot_state.snapshot()}

            # any non-empty speech that isn't a clear "no" = confirmation
            robot_state.set_mode(RobotMode.ACTIVE)
            robot.set_led_state("active")
            robot.open_dashboard(settings.dashboard_url)
            response = "JUNO Assist is now online. Opening your dashboard."
            robot_state.set_response(response)
            tts.speak(response)
            tts.speak("What can I help you with?")
            return {"intent": Intent.CONFIRM, "response": response, "status": robot_state.snapshot()}

            # unreachable — kept for structure
            return {"intent": intent, "response": snapshot["last_response"], "status": robot_state.snapshot()}

        if snapshot["mode"] == RobotMode.ACTIVE:
            if intent == Intent.SLEEP:
                robot_state.set_mode(RobotMode.IDLE)
                response = "JUNO is going back to sleep mode."
                robot_state.set_response(response)
                tts.speak(response)
                return {"intent": intent, "response": response, "status": robot_state.snapshot()}

            if intent == Intent.SET_TIMER:
                minutes = intent_classifier.extract_timer_minutes(text)
                timer_service.start_timer(minutes)
                response = f"Study timer started for {minutes} minutes."
            elif intent == Intent.PLAY_MUSIC:
                response = music_service.play_soothing_music()["message"]
            else:
                response = response_generator.generate(
                    intent=intent,
                    emotion=snapshot["current_emotion"],
                    user_text=raw_text,
                )

            robot_state.set_response(response)
            is_fallback = response == "Sorry, I can't help with that yet."
            if not is_fallback:
                tts.speak(response)
            return {"intent": intent, "response": response, "status": robot_state.snapshot()}

        response = "JUNO is not ready yet."
        robot_state.set_response(response)
        return {"intent": intent, "response": response, "status": robot_state.snapshot()}

    @app.on_event("startup")
    async def startup_event():
        calendar_service.seed_from_json_if_empty(str(Path("data/sample_schedule.json")))
        asyncio.create_task(_emotion_monitor_loop())
        asyncio.create_task(_timer_loop())
        if settings.use_ros_robot:
            asyncio.create_task(_ros_speech_command_loop())

    async def _emotion_monitor_loop():
        while True:
            if robot_state.snapshot()["mode"] == RobotMode.ACTIVE:
                frame = robot.get_camera_frame()
                emotion = emotion_detector.predict_from_frame(frame)
                robot_state.set_emotion(emotion)
            await asyncio.sleep(settings.emotion_update_seconds)

    async def _timer_loop():
        while True:
            robot_state.decrement_timer()
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
            {"name": "Today's Schedule", "description": "Check classes, meetings, and deadlines."},
            {"name": "Study Timer", "description": "Start a Pomodoro-style focus session."},
            {"name": "Facial Emotion Estimate", "description": "Estimate visible emotion state using camera input."},
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
            "led_topic": settings.led_topic,
            "publisher_wait_seconds": settings.tts_publisher_wait_seconds,
            "publish_retries": settings.tts_publish_retries,
        }
        return status

    @app.get("/api/schedule/today")
    def get_today_schedule():
        return calendar_service.get_today_schedule()

    @app.get("/api/deadlines")
    def get_deadlines():
        return calendar_service.get_upcoming_deadlines()

    @app.get("/api/reminders")
    def get_reminders():
        return calendar_service.list_reminders()

    @app.post("/api/reminders")
    def add_reminder(request: ReminderRequest):
        reminder = calendar_service.add_reminder(
            title=request.title,
            due_date=request.due_date,
            due_time=request.due_time,
            priority=request.priority,
        )
        robot_state.set_response(f"Reminder added: {request.title}.")
        return reminder

    @app.post("/api/timer/start")
    def start_timer(request: TimerRequest):
        result = timer_service.start_timer(request.minutes)
        robot_state.set_response(f"Study timer started for {request.minutes} minutes.")
        return result

    @app.post("/api/music/play")
    def play_music():
        result = music_service.play_soothing_music()
        robot_state.set_response(result["message"])
        tts.speak(result["message"])
        return result

    @app.post("/api/robot/sleep")
    def sleep_robot():
        robot_state.set_mode(RobotMode.IDLE)
        robot_state.set_response("JUNO is now in sleep mode.")
        robot.set_led_state("sleep")
        tts.speak("JUNO is now in sleep mode.")
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
