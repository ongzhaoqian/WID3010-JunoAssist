from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import Optional


class RobotMode(str, Enum):
    IDLE = "idle"
    CONFIRMATION = "confirmation"
    ACTIVE = "active"
    SLEEP = "sleep"


class VisionEmotionMode(str, Enum):
    JUNO = "juno"
    EKMAN = "ekman"


class EmotionState(str, Enum):
    # Ekman-style facial emotion taxonomy used by the vision module:
    # six basic emotions plus neutral. UNKNOWN means the system does not have
    # enough evidence to make a responsible judgement.
    ANGER = "anger"
    DISGUST = "disgust"
    FEAR = "fear"
    HAPPINESS = "happiness"
    SADNESS = "sadness"
    SURPRISE = "surprise"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"

    # Backwards-compatible aliases used by older response/music code. These
    # now resolve to the Ekman classes instead of creating a separate taxonomy.
    ANGRY = "anger"
    HAPPY = "happiness"
    SAD = "sadness"
    TIRED = "sadness"
    STRESSED = "fear"
    FRUSTRATED = "anger"

    @classmethod
    def _missing_(cls, value):
        label = str(value or "unknown").strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "angry": cls.ANGER,
            "anger": cls.ANGER,
            "annoyed": cls.ANGER,
            "frustrated": cls.ANGER,
            "irritated": cls.ANGER,
            "disgust": cls.DISGUST,
            "disgusted": cls.DISGUST,
            "repulsed": cls.DISGUST,
            "fear": cls.FEAR,
            "fearful": cls.FEAR,
            "afraid": cls.FEAR,
            "scared": cls.FEAR,
            "anxious": cls.FEAR,
            "stressed": cls.FEAR,
            "stress": cls.FEAR,
            "worried": cls.FEAR,
            "happy": cls.HAPPINESS,
            "happiness": cls.HAPPINESS,
            "joy": cls.HAPPINESS,
            "joyful": cls.HAPPINESS,
            "smiling": cls.HAPPINESS,
            "sad": cls.SADNESS,
            "sadness": cls.SADNESS,
            "tired": cls.SADNESS,
            "sleepy": cls.SADNESS,
            "fatigued": cls.SADNESS,
            "surprise": cls.SURPRISE,
            "surprised": cls.SURPRISE,
            "shock": cls.SURPRISE,
            "shocked": cls.SURPRISE,
            "neutral": cls.NEUTRAL,
            "calm": cls.NEUTRAL,
            "relaxed": cls.NEUTRAL,
            "normal": cls.NEUTRAL,
            "unknown": cls.UNKNOWN,
            "uncertain": cls.UNKNOWN,
        }
        return aliases.get(label, cls.UNKNOWN)


class Intent(str, Enum):
    WAKE = "wake"
    CONFIRM = "confirm"
    CHECK_SCHEDULE = "check_schedule"
    CHECK_DEADLINE = "check_deadline"
    ADD_SCHEDULE = "add_schedule"
    CHECK_REMINDERS = "check_reminders"
    ADD_REMINDER = "add_reminder"
    SET_TIMER = "set_timer"
    PLAY_MUSIC = "play_music"
    STOP = "stop"
    REQUEST_BREAK = "request_break"
    ASK_STATUS = "ask_status"
    SLEEP = "sleep"
    UNKNOWN = "unknown"


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)


class AuthUser(BaseModel):
    id: int
    username: str
    created_at: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    user: AuthUser


class CommandRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ReminderRequest(BaseModel):
    # The reminder schema now mirrors schedule items: title, date, time, type, priority.
    # due_date/due_time remain accepted for backwards compatibility with older frontend/API calls.
    title: str = Field(..., min_length=1, max_length=120)
    date: Optional[str] = None
    time: Optional[str] = None
    type: str = Field(default="reminder", max_length=40)
    priority: str = Field(default="medium", max_length=20)
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    completed: bool | None = None

    @model_validator(mode="after")
    def normalise_legacy_due_fields(self):
        if not self.date and self.due_date:
            self.date = self.due_date
        if not self.time and self.due_time:
            self.time = self.due_time
        return self


class ReminderUpdateRequest(BaseModel):
    completed: bool


class ScheduleItemRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    date: Optional[str] = None
    time: Optional[str] = None
    type: str = Field(default="study", max_length=40)
    priority: str = Field(default="medium", max_length=20)


class ScheduleItemUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    date: Optional[str] = None
    time: Optional[str] = None
    type: Optional[str] = Field(default=None, max_length=40)
    priority: Optional[str] = Field(default=None, max_length=20)
    completed: Optional[bool] = None


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


class VisionModeRequest(BaseModel):
    mode: VisionEmotionMode = VisionEmotionMode.JUNO

class FitnessProfileRequest(BaseModel):
    height_m: Optional[float] = Field(default=None, ge=0.5, le=2.5)
    weight_kg: Optional[float] = Field(default=None, ge=20, le=250)


class FitnessSessionRequest(BaseModel):
    score_67: int = Field(..., ge=0, le=10000)
    source: str = Field(default="manual", max_length=40)
    duration_seconds: Optional[int] = Field(default=None, ge=1, le=600)



class RobotStatus(BaseModel):
    mode: RobotMode
    current_emotion: EmotionState
    last_response: str
    timer_remaining_seconds: int
    active_timer_label: Optional[str] = None
    awaiting_timer_duration: bool = False
    timer_completed_counter: int = 0
    last_timer_completed_label: Optional[str] = None
