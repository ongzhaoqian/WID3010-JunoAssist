from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import Optional


class RobotMode(str, Enum):
    IDLE = "idle"
    CONFIRMATION = "confirmation"
    ACTIVE = "active"
    SLEEP = "sleep"


class EmotionState(str, Enum):
    HAPPY = "happy"
    NEUTRAL = "neutral"
    TIRED = "tired"
    STRESSED = "stressed"
    FRUSTRATED = "frustrated"
    UNKNOWN = "unknown"


class Intent(str, Enum):
    WAKE = "wake"
    CONFIRM = "confirm"
    CHECK_SCHEDULE = "check_schedule"
    CHECK_DEADLINE = "check_deadline"
    SET_TIMER = "set_timer"
    ADD_REMINDER = "add_reminder"
    PLAY_MUSIC = "play_music"
    REQUEST_BREAK = "request_break"
    ASK_STATUS = "ask_status"
    SLEEP = "sleep"
    UNKNOWN = "unknown"


class CommandRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ReminderRequest(BaseModel):
    title: str
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    priority: str = "medium"


class ScheduleItemRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    date: Optional[str] = None
    time: Optional[str] = None
    type: str = Field(default="study", max_length=40)
    priority: str = Field(default="medium", max_length=20)


class TimerRequest(BaseModel):
    # Keep minutes for backwards compatibility, but allow seconds too so the
    # dashboard and voice flow can start timers such as 1 minute 30 seconds.
    minutes: int = Field(default=25, ge=0, le=180)
    seconds: int = Field(default=0, ge=0, le=59)

    @model_validator(mode="after")
    def validate_duration(self):
        if self.minutes == 0 and self.seconds == 0:
            raise ValueError("Timer duration must be at least one second.")
        return self


class MusicPlayRequest(BaseModel):
    emotion: Optional[EmotionState] = None


class RobotStatus(BaseModel):
    mode: RobotMode
    current_emotion: EmotionState
    last_response: str
    timer_remaining_seconds: int
    active_timer_label: Optional[str] = None
