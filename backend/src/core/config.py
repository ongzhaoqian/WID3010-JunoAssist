from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "JUNO Assist"
    dashboard_url: str = "http://localhost:5173"
    database_path: str = "juno_assist.db"
    wake_phrase: str = "hey, juno"
    confirmation_phrase: str = "yes"
    emotion_update_seconds: float = 3.0
    use_mock_robot: bool = True


settings = Settings()
