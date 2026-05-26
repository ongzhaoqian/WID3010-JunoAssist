from dataclasses import dataclass
import os


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "JUNO Assist"
    dashboard_url: str = os.getenv("JUNO_DASHBOARD_URL", "http://localhost:5173")
    dashboard_window_title: str = os.getenv("JUNO_DASHBOARD_WINDOW_TITLE", "JUNO Assist Dashboard")
    dashboard_reuse_existing: bool = _env_bool("JUNO_DASHBOARD_REUSE_EXISTING", True)
    dashboard_close_on_sleep: bool = _env_bool("JUNO_DASHBOARD_CLOSE_ON_SLEEP", True)
    # Best-effort runtime cleanup when JUNO powers down. The backend and roscore
    # are excluded so the robot can still be woken again in the same run.
    powerdown_cleanup_enabled: bool = _env_bool("JUNO_POWERDOWN_CLEANUP_ENABLED", True)
    powerdown_cleanup_grace_seconds: float = float(os.getenv("JUNO_POWERDOWN_CLEANUP_GRACE_SECONDS", "1.0"))
    powerdown_cleanup_delay_seconds: float = float(os.getenv("JUNO_POWERDOWN_CLEANUP_DELAY_SECONDS", "2.0"))
    powerdown_cleanup_patterns: str = os.getenv(
        "JUNO_POWERDOWN_CLEANUP_PATTERNS",
        r"npm\s+run\s+dev|vite|roslaunch\s+juno_bringup|camera_node\.py|microphone_node\.py|tts_node\.py|transcriber\.py|camera_listener_node\.py|microphone_listener_node\.py"
    )
    powerdown_cleanup_exclude_patterns: str = os.getenv(
        "JUNO_POWERDOWN_CLEANUP_EXCLUDE_PATTERNS",
        r"roscore|rosmaster|rosout|backend/main\.py|uvicorn.*backend|pytest"
    )
    database_path: str = os.getenv("JUNO_DATABASE_PATH", "juno_assist.db")
    wake_phrase: str = os.getenv("JUNO_WAKE_PHRASE", "hey john")
    confirmation_phrase: str = os.getenv("JUNO_CONFIRMATION_PHRASE", "yes")
    emotion_update_seconds: float = float(os.getenv("JUNO_EMOTION_UPDATE_SECONDS", "3.0"))
    # When the user explicitly states an emotion in speech, keep that as the
    # trusted emotion for this many seconds before visual inference may override it.
    speech_emotion_override_seconds: float = float(os.getenv("JUNO_SPEECH_EMOTION_OVERRIDE_SECONDS", "45.0"))

    # Set JUNO_ROBOT_INTERFACE=ros when running on the Jupiter/ROS machine.
    robot_interface: str = os.getenv("JUNO_ROBOT_INTERFACE", "mock").lower()
    use_ros_robot: bool = _env_bool("JUNO_USE_ROS", False) or robot_interface == "ros"

    # Robot-friendly speech recognition configuration. The ROS transcriber node
    # uses the same defaults and publishes recognised speech to /speech/transcript.
    asr_enabled: bool = _env_bool("JUNO_ASR_ENABLED", True)
    asr_model_id: str = os.getenv("JUNO_ASR_MODEL_ID", "openai/whisper-tiny")
    asr_task: str = os.getenv("JUNO_ASR_TASK", "translate").strip().lower()
    asr_language: str = os.getenv("JUNO_ASR_LANGUAGE", "").strip()
    asr_sample_rate: int = int(os.getenv("JUNO_ASR_SAMPLE_RATE", "16000"))
    asr_window_seconds: float = float(os.getenv("JUNO_ASR_WINDOW_SECONDS", "3.0"))
    asr_min_rms: float = float(os.getenv("JUNO_ASR_MIN_RMS", "0.03"))
    asr_device: str = os.getenv("JUNO_ASR_DEVICE", "-1")
    asr_tts_resume_delay: float = float(os.getenv("JUNO_ASR_TTS_RESUME_DELAY", "0.5"))

    # Dashboard camera streaming. The ROS backend subscribes to this image topic
    # and exposes it as an MJPEG feed for the web dashboard, replacing the
    # separate OpenCV pop-up viewer normally used in ROS demos.
    camera_topic: str = os.getenv("JUNO_CAMERA_TOPIC", "/camera/image_raw")
    camera_stream_fps: float = float(os.getenv("JUNO_CAMERA_STREAM_FPS", "12"))
    camera_jpeg_quality: int = int(os.getenv("JUNO_CAMERA_JPEG_QUALITY", "80"))
    camera_enabled_default: bool = _env_bool("JUNO_CAMERA_ENABLED_DEFAULT", False)
    vision_model_enabled_default: bool = _env_bool("JUNO_VISION_MODEL_ENABLED_DEFAULT", False)
    vision_emotion_mode_default: str = os.getenv("JUNO_VISION_EMOTION_MODE_DEFAULT", "juno").strip().lower()

    # Core face-emotion model. The default is a lightweight Hugging Face image
    # classifier fine-tuned for FER2013/Ekman-style facial expressions. The
    # dashboard can switch between the original JUNO labels and native Ekman labels
    # without reloading this model. SmolVLM remains available only as
    # JUNO_VISION_BACKEND=smolvlm for experiments.
    vision_backend: str = os.getenv("JUNO_VISION_BACKEND", "face_expression").strip().lower()
    vision_model_id: str = os.getenv("JUNO_VISION_MODEL_ID", "mo-thecreator/vit-Facial-Expression-Recognition")
    # Optional comma-separated override for image-classification models with numeric labels.
    # Leave blank for Hugging Face id2label strings; set e.g. angry,disgust,fear,happy,sad,surprise,neutral only if your model lacks id2label.
    vision_label_order: str = os.getenv("JUNO_VISION_LABEL_ORDER", "").strip()
    vision_device: str = os.getenv("JUNO_VISION_DEVICE", "auto")
    vision_max_new_tokens: int = int(os.getenv("JUNO_VISION_MAX_NEW_TOKENS", "96"))
    vision_min_confidence: float = float(os.getenv("JUNO_VISION_MIN_CONFIDENCE", "0.30"))
    # Prevent a vague SmolVLM answer such as "neutral, 40%" from being shown as
    # a confident robot emotion. Non-neutral labels above the fast-switch threshold
    # are allowed to update the dashboard immediately instead of being diluted by
    # the previous neutral EMA state.
    vision_neutral_uncertain_confidence: float = float(os.getenv("JUNO_VISION_NEUTRAL_UNCERTAIN_CONFIDENCE", "0.45"))
    vision_fast_switch_confidence: float = float(os.getenv("JUNO_VISION_FAST_SWITCH_CONFIDENCE", "0.52"))
    # If true, return UNKNOWN when no face crop is found. Default false keeps the
    # robot demo forgiving by using a centre crop fallback when Haar detection is weak.
    vision_require_face: bool = _env_bool("JUNO_VISION_REQUIRE_FACE", False)

    # Emotion-aware music. The dashboard uses Spotify embeds by default because
    # they do not require storing API secrets in this student prototype. Direct
    # Spotify playback through the Web Playback SDK can be layered later with
    # OAuth and a Premium account. Each URL can be overridden in .env.
    music_provider: str = os.getenv("JUNO_MUSIC_PROVIDER", "spotify")
    spotify_happiness_url: str = os.getenv("JUNO_SPOTIFY_HAPPINESS_URL", os.getenv("JUNO_SPOTIFY_HAPPY_URL", "https://open.spotify.com/playlist/37i9dQZF1DXdPec7aLTmlC"))
    spotify_neutral_url: str = os.getenv("JUNO_SPOTIFY_NEUTRAL_URL", "https://open.spotify.com/playlist/37i9dQZF1DWZeKCadgRdKQ")
    spotify_sadness_url: str = os.getenv("JUNO_SPOTIFY_SADNESS_URL", os.getenv("JUNO_SPOTIFY_TIRED_URL", "https://open.spotify.com/playlist/37i9dQZF1DX4sWSpwq3LiO"))
    spotify_fear_url: str = os.getenv("JUNO_SPOTIFY_FEAR_URL", os.getenv("JUNO_SPOTIFY_STRESSED_URL", "https://open.spotify.com/playlist/37i9dQZF1DWWQRwui0ExPn"))
    spotify_anger_url: str = os.getenv("JUNO_SPOTIFY_ANGER_URL", os.getenv("JUNO_SPOTIFY_FRUSTRATED_URL", "https://open.spotify.com/playlist/37i9dQZF1DX4WYpdgoIcn6"))
    spotify_disgust_url: str = os.getenv("JUNO_SPOTIFY_DISGUST_URL", "https://open.spotify.com/playlist/37i9dQZF1DWZeKCadgRdKQ")
    spotify_surprise_url: str = os.getenv("JUNO_SPOTIFY_SURPRISE_URL", "https://open.spotify.com/playlist/37i9dQZF1DX4WYpdgoIcn6")
    spotify_unknown_url: str = os.getenv("JUNO_SPOTIFY_UNKNOWN_URL", "https://open.spotify.com/playlist/37i9dQZF1DWZeKCadgRdKQ")

    # ROS text-to-speech publishing configuration. The backend publishes responses
    # to /juno/tts and waits briefly for the ROS TTS subscriber so speech messages
    # are not dropped during startup or after node restarts.
    tts_topic: str = os.getenv("JUNO_TTS_TOPIC", "/juno/tts")
    tts_stop_topic: str = os.getenv("JUNO_TTS_STOP_TOPIC", "/juno/tts_stop")
    led_topic: str = os.getenv("JUNO_LED_TOPIC", "/juno/led_state")
    tts_publisher_wait_seconds: float = float(os.getenv("JUNO_TTS_PUBLISHER_WAIT_SECONDS", "2.0"))
    tts_publish_retries: int = int(os.getenv("JUNO_TTS_PUBLISH_RETRIES", "1"))
    tts_publish_retry_delay: float = float(os.getenv("JUNO_TTS_PUBLISH_RETRY_DELAY", "0.15"))

    # Optional text-generation LLM. Disabled by default because the robot target
    # cannot reliably run Malaysian Llama + LoRA locally. If left blank, no text
    # LLM will be loaded and deterministic backend responses are used.
    llm_enabled: bool = _env_bool("JUNO_LLM_ENABLED", False)
    llm_model_id: str = os.getenv("JUNO_LLM_MODEL_ID", "")
    llm_adapter_id: str = os.getenv("JUNO_LLM_ADAPTER_ID", "")
    llm_device_map: str = os.getenv("JUNO_LLM_DEVICE_MAP", "auto")
    llm_torch_dtype: str = os.getenv("JUNO_LLM_TORCH_DTYPE", "auto")
    llm_max_new_tokens: int = int(os.getenv("JUNO_LLM_MAX_NEW_TOKENS", "96"))
    llm_normalise_max_new_tokens: int = int(os.getenv("JUNO_LLM_NORMALISE_MAX_NEW_TOKENS", "48"))
    llm_max_response_words: int = int(os.getenv("JUNO_LLM_MAX_RESPONSE_WORDS", "80"))
    llm_temperature: float = float(os.getenv("JUNO_LLM_TEMPERATURE", "0.3"))
    llm_top_p: float = float(os.getenv("JUNO_LLM_TOP_P", "0.9"))

settings = Settings()
