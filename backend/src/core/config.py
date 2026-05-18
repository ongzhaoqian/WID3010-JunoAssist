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

    # Hugging Face language model configuration. The model remains behind the
    # NLP layer so ROS nodes only handle robot I/O. Enable this on a machine
    # with sufficient RAM/GPU using JUNO_LLM_ENABLED=true.
    llm_enabled: bool = _env_bool("JUNO_LLM_ENABLED", False)
    llm_model_id: str = os.getenv(
        "JUNO_LLM_MODEL_ID",
        "mesolitica/Malaysian-Llama-3.2-3B-Instruct",
    )
    llm_device_map: str = os.getenv("JUNO_LLM_DEVICE_MAP", "auto")
    llm_torch_dtype: str = os.getenv("JUNO_LLM_TORCH_DTYPE", "auto")
    llm_max_new_tokens: int = int(os.getenv("JUNO_LLM_MAX_NEW_TOKENS", "96"))
    llm_max_response_words: int = int(os.getenv("JUNO_LLM_MAX_RESPONSE_WORDS", "80"))
    llm_temperature: float = float(os.getenv("JUNO_LLM_TEMPERATURE", "0.4"))
    llm_top_p: float = float(os.getenv("JUNO_LLM_TOP_P", "0.9"))


settings = Settings()
