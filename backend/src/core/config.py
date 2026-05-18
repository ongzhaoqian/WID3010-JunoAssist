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
    print(os.getenv("JUNO_ROBOT_INTERFACE"))
    #robot_interface: str = "ros"
    use_ros_robot: bool = _env_bool("JUNO_USE_ROS", False) or robot_interface == "ros"
    print(robot_interface, use_ros_robot)


settings = Settings()
