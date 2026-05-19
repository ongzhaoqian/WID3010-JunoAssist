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
    database_path: str = os.getenv("JUNO_DATABASE_PATH", "juno_assist.db")
    wake_phrase: str = os.getenv("JUNO_WAKE_PHRASE", "hey, juno")
    confirmation_phrase: str = os.getenv("JUNO_CONFIRMATION_PHRASE", "yes")
    emotion_update_seconds: float = float(os.getenv("JUNO_EMOTION_UPDATE_SECONDS", "3.0"))

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

    # ROS text-to-speech publishing configuration. The backend publishes responses
    # to /juno/tts and waits briefly for the ROS TTS subscriber so speech messages
    # are not dropped during startup or after node restarts.
    tts_topic: str = os.getenv("JUNO_TTS_TOPIC", "/juno/tts")
    led_topic: str = os.getenv("JUNO_LED_TOPIC", "/juno/led_state")
    tts_publisher_wait_seconds: float = float(os.getenv("JUNO_TTS_PUBLISHER_WAIT_SECONDS", "2.0"))
    tts_publish_retries: int = int(os.getenv("JUNO_TTS_PUBLISH_RETRIES", "3"))
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
