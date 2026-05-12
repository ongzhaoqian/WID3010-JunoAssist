from src.core.state import robot_state


class TimerService:
    def start_timer(self, minutes: int, label: str = "Study timer") -> dict:
        seconds = minutes * 60
        robot_state.set_timer(seconds, label)
        return {
            "label": label,
            "minutes": minutes,
            "remaining_seconds": seconds,
        }
