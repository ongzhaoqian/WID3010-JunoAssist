from src.core.state import robot_state


class TimerService:
    def start_timer(self, minutes: int, label: str = "Study timer") -> dict:
        return self.start_timer_duration(minutes=minutes, seconds=0, label=label)

    def start_timer_duration(
        self,
        minutes: int = 25,
        seconds: int = 0,
        label: str = "Study timer",
    ) -> dict:
        total_seconds = max(0, int(minutes) * 60 + int(seconds))
        if total_seconds <= 0:
            raise ValueError("Timer duration must be at least one second.")
        robot_state.set_timer(total_seconds, label)
        return {
            "label": label,
            "minutes": total_seconds // 60,
            "seconds": total_seconds % 60,
            "remaining_seconds": total_seconds,
        }
