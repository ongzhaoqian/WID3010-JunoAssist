from enum import Enum
from pydantic import BaseModel, Field
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


class TimerRequest(BaseModel):
    minutes: int = Field(default=25, ge=1, le=180)


class RobotStatus(BaseModel):
    mode: RobotMode
    current_emotion: EmotionState
    last_response: str
    timer_remaining_seconds: int
    active_timer_label: Optional[str] = None
