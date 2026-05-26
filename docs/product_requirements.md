# Juno Assist — Product Requirements Document

## Read This First

This document is the **system specification**: what JUNO Assist should do and how the software components are designed.

Use this file when you need:

- feature requirements and project scope
- backend/dashboard/ROS component specifications
- API contracts and data flow expectations
- technical design notes, including emotion recognition requirements
- implementation planning details

If you only want terminal commands to run the robot, use `docs/ros_integration_guide.md` instead. If you are preparing the final demo/report, use `docs/project_manual_scaled_demo.md`.

## Quick Navigation

| Need | Go to |
|---|---|
| Understand project scope and feature requirements | Sections 1-2 |
| Check ROS node catalogue and topic graph | Sections 3-4 |
| Check backend API and dashboard contracts | Sections 5-6 |
| Find launch/debug commands | Sections 7-8 |
| Read preserved detailed planning/component notes | Appendix A onwards |

---

> **Target platform:** Jupiter JUNO robot · ROS Noetic · Python 3.10+ · FastAPI · React/Vite  
> **Build system:** catkin_ws (`/src`) with packages connected to `/backend` via REST + WebSocket APIs  
> **Database:** SQLite (`backend/juno_assist.db`)

> **Python version note:** The supported minimum is **Python 3.10+**. The backend dependencies used on the integration branches (`fastapi`, `uvicorn`, `pydantic`, `python-multipart`, `pytest`) support Python 3.10+, and ROS Noetic robot-side scripts use `python3`. Python 3.12 can also be used for laptop/backend development, but it is not required as the project minimum.

> **Branch note:** This document describes the target/final implementation contract. Some referenced source paths may exist on integration branches before they are merged into the final submission branch.

---

## 1. Scope and Coding Agent Boundaries

Each feature below is owned by a named coding agent. Agents must not reach outside their layer boundary without going through the defined API contract.

| Agent | Layer | Directory |
| :--- | :--- | :--- |
| **ROS-Perception** | catkin_ws hardware input | `src/perception_pkg/` |
| **ROS-Language** | catkin_ws speech I/O | `src/language_pkg/` |
| **Backend-Activation** | Wake word + confirmation logic | `backend/src/activation/` |
| **Backend-Vision** | Facial emotion pipeline | `backend/src/vision/` |
| **Backend-NLP** | Intent classification + response generation | `backend/src/nlp/` |
| **Backend-Productivity** | Pomodoro timer + music | `backend/src/productivity/` |
| **Backend-Calendar** | Schedule, deadlines, reminders + SQLite | `backend/src/calendar_module/` |
| **Backend-HAL** | Jupiter JUNO hardware abstraction | `backend/src/robot/` |
| **Backend-API** | FastAPI orchestration layer | `backend/src/api/` |
| **Frontend-Dashboard** | React web dashboard | `dashboard/src/` |

---

## 2. Feature Requirements

### F1 — Wake Commands

**Agent:** ROS-Perception, Backend-Activation

#### Requirements
- The microphone node (`microphone_node.py`) shall continuously publish raw float32 audio frames to `/audio/raw` at 16 kHz, 512-sample chunks.
- The microphone node publishes audio to `/audio/raw`; `whisper_tiny_transcriber` transcribes it with `openai/whisper-tiny` and publishes `/speech/transcript`. Manual/external transcript fallback remains available through `/speech/raw_transcript`.
- The backend `WakeWordDetector` (`activation/wake_word_detector.py`) receives transcripts via `RosJupiterInterface.listen()`, which drains an internal queue populated by the `/speech/transcript` subscriber.
- The following trigger phrases shall activate the confirmation flow (case-insensitive, as configured by `JUNO_WAKE_PHRASE` env var, default `"hey john"`):
  - `"hey, john"` / `"hey john"`
  - `"ok juno"`
  - `"juno"`
- On detection, the backend transitions the global `RobotMode` to `CONFIRMATION`.
- False-positive rate must be below 5 per 30-minute idle session.
- Wake detection latency from end of utterance to state change: ≤ 800 ms.

#### ROS Interface (via RosJupiterInterface)

| Direction | Topic | Message Type | Description |
| :--- | :--- | :--- | :--- |
| Subscribe | `/speech/transcript` | `std_msgs/String` | recognised speech transcript, queued internally for `listen()` |

---

### F2 — Voice Confirmation Before Activation

**Agent:** Backend-Activation, ROS-Language

#### Requirements
- On entering `CONFIRMATION` mode, the system shall speak a confirmation prompt via `robot.speak()`, e.g., `"Are you sure you would like to power Juno on? Answer yes if you do, else ignore."`.
- The `ConfirmationHandler` (`activation/confirmation_handler.py`) shall wait up to **5 seconds** for a follow-up transcript via `robot.listen()`.
- The confirmation phrase is configurable via `JUNO_CONFIRMATION_PHRASE` env var (default `"yes"`).
- If a valid confirmation arrives within the window, mode transitions to `ACTIVE` and the transcript is forwarded to the NLP pipeline.
- If the window expires with no input, mode returns to `IDLE` and Juno speaks a fallback message.
- Current mode is tracked in `backend/src/core/state.py` as a `RobotMode` enum: `IDLE | CONFIRMATION | ACTIVE | SLEEP`.

#### ROS Interface (via RosJupiterInterface)

| Direction | Topic | Message Type | Description |
| :--- | :--- | :--- | :--- |
| Subscribe | `/speech/transcript` | `std_msgs/String` | Confirmation utterance, via `listen()` queue |
| Publish | `/juno/tts` | `std_msgs/String` | Spoken confirmation prompt, via `speak()` |

---

### F3 — Web Dashboard (Post-Activation)

**Agent:** Frontend-Dashboard, Backend-API

#### Requirements
- The dashboard (`dashboard/src/`) shall be a single-page React/Vite app served separately from the backend on port 5173.
- Dashboard activates its full interactive mode when Juno mode is `ACTIVE`; panels render in a muted/greyed style during `IDLE`.
- Required panels:

| Panel | Component File | Data Source |
| :--- | :--- | :--- |
| **Status Panel** | `StatusPanel.jsx` | `GET /api/status`, `WS /ws/status` |
| **Emotion Panel** | `StatusPanel.jsx` (embedded) | `WS /ws/status` (field: `current_emotion`) |
| **Schedule Panel** | `SchedulePanel.jsx` | `GET /api/schedule/today` |
| **Reminder Panel** | `ReminderPanel.jsx` | `GET /api/reminders` |
| **Timer Panel** | `TimerPanel.jsx` | `WS /ws/status` (fields: `timer_remaining_seconds`, `active_timer_label`) |
| **Command Panel** | `CommandPanel.jsx` | `POST /api/command` |

- WebSocket `/ws/status` shall push a JSON object containing: `{ mode, current_emotion, last_response, timer_remaining_seconds, active_timer_label }`.
- The dashboard must display the live emotion label and a confidence bar without requiring a page reload.
- Dashboard URL is configurable via `JUNO_DASHBOARD_URL` (default `http://localhost:5173`). If running on a separate machine, set to `http://ROBOT_IP:5173`.

---

### F4 — Facial Emotion Monitoring

**Agent:** Backend-Vision

#### Requirements
- `camera_node.py` shall publish `sensor_msgs/Image` frames at 30 Hz to `/camera/image_raw`.
- `RosJupiterInterface` subscribes to `/camera/image_raw` via `_camera_callback` and stores the latest frame as `self.latest_frame` (converted from `sensor_msgs/Image` to OpenCV BGR via `cv_bridge`).
- The backend retrieves the latest frame by calling `robot.get_camera_frame()`, which returns `self.latest_frame`.
- The `EmotionDetector` (`vision/emotion_detector.py`) shall classify each frame into exactly one of: `Happy | Neutral | Tired | Stressed | Frustrated` (see `EmotionState` in `core/models.py`).
- Smoothing and state determination logic is specified in `docs/technical_requirements_emotion.md`.
- The smoothed emotion and confidence shall be included in all `/ws/status` broadcasts and stored per NLP response for adaptive messaging.
- When the detected emotion is `Tired` or `Stressed`, the backend shall automatically suggest a break via TTS and flag `break_recommended: true` in the WebSocket payload.
- Emotion polling interval is configurable via `JUNO_EMOTION_UPDATE_SECONDS` (default `3.0`).

#### ROS Interface (via RosJupiterInterface)

| Direction | Topic | Message Type | Description |
| :--- | :--- | :--- | :--- |
| Subscribe | `/camera/image_raw` | `sensor_msgs/Image` | Raw camera frames, stored as latest OpenCV frame |

---

### F5 — Rule-Based Intent Detection

**Agent:** Backend-NLP

#### Requirements
- `IntentClassifier` (`nlp/intent_classifier.py`) shall use keyword/pattern matching (no external LLM required) to map transcript text to one of the following intents:

| Intent ID | Trigger Keywords / Patterns | Action |
| :--- | :--- | :--- |
| `CHECK_SCHEDULE` | "schedule", "class", "meeting", "today", "what's on" | Return today's schedule |
| `CHECK_DEADLINE` | "deadline", "due", "reminders", "what do I need" | List upcoming deadlines |
| `SET_TIMER` | "timer", "pomodoro", "focus for", "work for" | Start Pomodoro session |
| `ADD_REMINDER` | "remind me", "reminder", "don't forget" | Create reminder |
| `PLAY_MUSIC` | "play music", "some music", "background music" | Trigger music service |
| `REQUEST_BREAK` | "break", "rest", "pause" | Recommend a break |
| `ASK_STATUS` | "how am I", "status", "how's my day" | Return current summary |
| `SLEEP` | "sleep", "goodbye", "stop listening", "that's all" | Transition to SLEEP mode |
| `UNKNOWN` | (fallback) | Speak fallback response |

- These map to the `Intent` enum defined in `backend/src/core/models.py`.
- `ResponseGenerator` (`nlp/response_generator.py`) shall combine `intent` + current `EmotionState` to produce an affirmation string before executing the action.
- All intents and generated responses shall be logged to SQLite table `intent_log`.

---

### F6 — Calendar and Reminder Storage (SQLite)

**Agent:** Backend-Calendar

#### Requirements
- Database file: `backend/juno_assist.db` (path configurable via `JUNO_DATABASE_PATH`).
- The `CalendarService` (`calendar_module/calendar_service.py`) manages schedule and reminder storage.
- On startup, `sample_schedule.json` (`backend/data/`) is seeded into the schedule table if it is empty.

- REST endpoints exposed by Backend-API:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/schedule/today` | Events where `start_dt` date = today |
| `POST` | `/api/schedule` | Add a new dashboard schedule item |
| `DELETE` | `/api/schedule/{item_id}` | Remove a dashboard schedule item |
| `GET` | `/api/reminders` | All incomplete reminders, ordered by due date |
| `POST` | `/api/reminders` | Create reminder `{ title, due_date?, due_time?, priority? }` |
| `GET` | `/api/deadlines` | Reminders due within the next 7 days |

- The `ReminderRequest` model (defined in `core/models.py`) accepts: `title`, `due_date` (optional), `due_time` (optional), `priority` (default `"medium"`).

---

### F7 — Study Timer (Pomodoro Technique)

**Agent:** Backend-Productivity, Frontend-Dashboard

#### Requirements
- `TimerService` (`productivity/timer_service.py`) shall implement configurable Pomodoro sessions:
  - Default: **25 min focus / 5 min short break / 15 min long break after 4 cycles**.
  - Duration configurable via `POST /api/timer/start` body: `{ minutes }` (default 25, range 1–180).
- Timer state shall be broadcast on `/ws/status` at 1 Hz when running: `{ timer_remaining_seconds, active_timer_label }`.
- When a focus session ends, Juno shall speak `"Great work! Time for a break."` via `robot.speak()`.
- `MusicService` (`productivity/music_service.py`) shall start background audio when a focus session begins.
- The `TimerPanel.jsx` shall display a visual countdown, current phase label. Controls: Start / Stop.

#### REST API

| Method | Endpoint | Body | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/timer/start` | `{ minutes?, seconds? }` | Start focus session with minute-and-second precision |
| `POST` | `/api/music/play` | `{ emotion? }` | Select and display emotion-aware Spotify music on the dashboard |
| `POST` | `/api/robot/sleep` | — | Put Juno into SLEEP mode |
| `POST` | `/api/command` | `{ text: string }` | Manual text command (same pipeline as voice) |

---

### F8 — Jupiter JUNO Hardware Abstraction Layer (HAL)

**Agent:** Backend-HAL

#### Requirements
- `JupiterInterface` (`robot/jupiter_interface.py`) is the abstract base class defining the hardware boundary. All robot-specific SDK or ROS calls must stay within this boundary.
- `MockJupiterInterface` (`robot/jupiter_interface.py`) is the **laptop/simulation** implementation used for off-robot development. It prints to stdout and uses `input()` for listen.
- `RosJupiterInterface` (`robot/ros_jupiter_interface.py`) is the **live hardware** implementation. It is loaded automatically when `JUNO_ROBOT_INTERFACE=ros` (or `JUNO_USE_ROS=true`) is set.
- The factory function `get_robot_interface()` selects the active implementation based on `settings.use_ros_robot`.

The interface contract (all implementations must match):

```python
class JupiterInterface(ABC):
    def speak(self, text: str) -> None: ...        # Publish to /juno/tts
    def listen(self) -> str: ...                    # Read from /speech/transcript queue (blocks up to 1 s)
    def get_camera_frame(self) -> Any: ...          # Return latest OpenCV BGR frame from /camera/image_raw
    def open_dashboard(self, url: str) -> None: ... # Open dashboard in browser / xdg-open
    def set_led_state(self, state: str) -> None: ...# Publish to /juno/led_state
```

- LED state string conventions (passed to `set_led_state`):

| RobotMode | LED State String |
| :--- | :--- |
| IDLE | `"idle"` |
| CONFIRMATION | `"confirmation"` |
| ACTIVE | `"active"` |
| SLEEP | `"sleep"` |

- `POST /api/robot/sleep` shall call `robot.speak()` with a goodbye message, then transition mode to `SLEEP`.

#### ROS Interface (RosJupiterInterface only)

| Direction | Topic | Message Type | Description |
| :--- | :--- | :--- | :--- |
| Subscribe | `/speech/transcript` | `std_msgs/String` | Queued for `listen()` calls |
| Subscribe | `/camera/image_raw` | `sensor_msgs/Image` | Stored as latest frame for `get_camera_frame()` |
| Publish | `/juno/tts` | `std_msgs/String` | Voice output via `speak()` |
| Publish | `/juno/led_state` | `std_msgs/String` | LED / status feedback via `set_led_state()` |

---

## 3. ROS Node Catalogue

### 3.1 Existing Nodes

| Node Name | Package | Script | Role |
| :--- | :--- | :--- | :--- |
| `camera_node` | `perception_pkg` | `camera_node.py` | Captures video from `/dev/video2`, publishes frames at 30 Hz |
| `microphone_node` | `perception_pkg` | `microphone_node.py` | Captures audio, publishes float32 chunks at 16 kHz |
| `whisper_tiny_transcriber` | `language_pkg` | `transcriber.py` | Transcribes microphone audio with Whisper Tiny and publishes transcript strings |
| `juno_tts_node` | `language_pkg` | `tts_node.py` | Subscribes to `/juno/tts`, speaks via pyttsx3/espeak |

All wake detection, state management, and emotion inference are handled inside the **FastAPI backend** via `RosJupiterInterface` — not by additional ROS nodes.

---

## 4. ROS Graph

```
┌──────────────────────────────────────────────────────────────────────┐
│  catkin_ws  (ROS Noetic)                                              │
│                                                                       │
│  [perception_pkg]                                                     │
│  ┌───────────────┐  /camera/image_raw (sensor_msgs/Image, 30 Hz)     │
│  │  camera_node  │──────────────────────────────────────────────────►│
│  └───────────────┘                                                    │
│                                                                       │
│  ┌───────────────────┐  /audio/raw (Float32MultiArray, 16 kHz)       │
│  │  microphone_node  │──────────────────────────► future ASR/manual  │
│  └───────────────────┘                         transcript source    │
│                                                │ /speech/raw_transcript
│  [language_pkg]                                ▼                     │
│  ┌──────────────────────┐  /speech/transcript (std_msgs/String)      │
│  │ whisper_tiny_     │◄── audio/transcript input               │
│  │ language_normalizer  │──────────────────────────────────────────►│
│  └──────────────────────┘                                            │
│                                                                       │
│  ┌──────────────────┐                                                │
│  │  juno_tts_node   │◄── /juno/tts (std_msgs/String)                │
│  │ (pyttsx3/espeak) │                                                │
│  └──────────────────┘                                                │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
          │  All four topics flow into / out of:
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FastAPI Backend  (RosJupiterInterface)                               │
│                                                                       │
│  Subscribes:  /camera/image_raw  →  _camera_callback → latest_frame  │
│               /speech/transcript →  _transcript_callback → queue     │
│                                                                       │
│  Publishes:   /juno/tts          ←  speak(text)                      │
│               /juno/led_state    ←  set_led_state(state)             │
│                                                                       │
│  Internal pipeline (no extra ROS nodes):                              │
│    listen() → WakeWordDetector → ConfirmationHandler                 │
│    get_camera_frame() → EmotionDetector → EmotionSmoother            │
│    transcript → IntentClassifier → ResponseGenerator → speak()       │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼  WebSocket /ws/status  (JSON, ≥ 2 Hz)
┌──────────────────────────────────────────────────────────────────────┐
│  React Dashboard  (dashboard/src/)                                    │
│  StatusPanel · SchedulePanel · ReminderPanel · TimerPanel            │
│  CommandPanel                                                         │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.1 Full Topic Register

| Topic | Message Type | Publisher | Subscriber(s) | Rate |
| :--- | :--- | :--- | :--- | :--- |
| `/audio/raw` | `std_msgs/Float32MultiArray` | `microphone_node` | Future ASR source / optional monitor | 16 kHz chunks |
| `/speech/raw_transcript` | `std_msgs/String` | Manual/external transcript fallback | `whisper_tiny_transcriber` | On utterance |
| `/camera/image_raw` | `sensor_msgs/Image` | `camera_node` | Backend (`RosJupiterInterface`) | 30 Hz |
| `/speech/transcript` | `std_msgs/String` | `whisper_tiny_transcriber` | Backend (`RosJupiterInterface`) | On utterance |
| `/juno/tts` | `std_msgs/String` | Backend (`RosJupiterInterface`) | `juno_tts_node` | On event |
| `/juno/led_state` | `std_msgs/String` | Backend (`RosJupiterInterface`) | Jupiter LED controller | On mode change |

---

## 5. Backend API Contract (Full)

All endpoints are served from `http://localhost:8000`. WebSocket lives on the same host.

| Method | Endpoint | Request Body | Response | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/features` | — | `{ features: string[] }` | Feature flag list |
| `GET` | `/api/status` | — | `RobotStatus` | Current mode, emotion, timer |
| `GET` | `/api/schedule/today` | — | `[{ id, title, start_dt, end_dt, location }]` | Today's schedule |
| `GET` | `/api/deadlines` | — | `[reminder]` | Reminders due in 7 days |
| `GET` | `/api/reminders` | — | `[reminder]` | All active reminders |
| `POST` | `/api/reminders` | `{ title, due_date?, due_time?, priority? }` | `{ id }` | Create reminder |
| `POST` | `/api/timer/start` | `{ minutes? }` | `{ ok }` | Start Pomodoro |
| `POST` | `/api/music/play` | — | `{ ok }` | Start background music |
| `POST` | `/api/robot/sleep` | — | `{ ok }` | Put Juno into SLEEP mode |
| `POST` | `/api/command` | `{ text: string }` | `{ intent, response, emotion }` | Manual text command |
| `WS` | `/ws/status` | — | JSON push ≥ 2 Hz | Live status stream |

### WebSocket `/ws/status` Payload Schema

Matches the `RobotStatus` model in `backend/src/core/models.py`:

```json
{
  "mode": "idle | confirmation | active | sleep",
  "current_emotion": "happy | neutral | tired | stressed | frustrated | unknown",
  "last_response": "Here is your schedule for today.",
  "timer_remaining_seconds": 1200,
  "active_timer_label": "Focus Session"
}
```

---

## 6. Frontend Dashboard Component Contract

Each component receives data exclusively through the shared WebSocket hook or REST calls.

| Component | File | Props / State | Updates via |
| :--- | :--- | :--- | :--- |
| `StatusPanel` | `StatusPanel.jsx` | `mode`, `current_emotion` | WS |
| `SchedulePanel` | `SchedulePanel.jsx` | `events[]` | REST on mount |
| `ReminderPanel` | `ReminderPanel.jsx` | `reminders[]` | REST on mount + mutation |
| `TimerPanel` | `TimerPanel.jsx` | `timer_remaining_seconds`, `active_timer_label` | WS |
| `CommandPanel` | `CommandPanel.jsx` | `last_response` | REST POST + WS |
| `Card` | `Card.jsx` | Generic wrapper | — |

The WebSocket connection (`dashboard/src/lib/api.js`) shall reconnect with exponential backoff (1 s → 2 s → 4 s → max 30 s) if disconnected.

---

## 7. Launch Configuration

The single entry point for all ROS nodes is `src/juno_bringup/launch/juno_robot.launch`. It launches nodes in dependency order:

1. `camera_node` (perception_pkg)
2. `microphone_node` (perception_pkg)
3. `whisper_tiny_transcriber` (language_pkg) — depends on `/audio/raw` for live ASR and can relay `/speech/raw_transcript` as a manual/external fallback
4. `juno_tts_node` (language_pkg)

The backend FastAPI server and React dashboard are **not** launched via ROS; they are started separately after sourcing the catkin workspace:

```bash
# Terminal 1 — ROS
roscore

# Terminal 2 — catkin nodes
catkin_make && source devel/setup.bash
roslaunch juno_bringup juno_robot.launch

# Terminal 3 — Backend (ROS mode)
cd backend
source ../devel/setup.bash
export JUNO_ROBOT_INTERFACE=ros
export JUNO_DASHBOARD_URL=http://localhost:5173
python main.py

# Terminal 4 — Dashboard
cd dashboard
npm install && npm run dev
```

If the dashboard runs on a different machine from the robot:

```bash
VITE_API_BASE=http://ROBOT_IP:8000 npm run dev
```

---

## 8. Debugging and Visualisation

### rqt_graph

Run `rqt_graph` after bringup to verify the node/topic graph matches Section 4.

### rostopic Cheat Sheet

```bash
# Watch live transcripts (and manually inject wake word)
rostopic echo /speech/transcript
rostopic pub /speech/transcript std_msgs/String "data: 'Hey, John'"
rostopic pub /speech/transcript std_msgs/String "data: 'yes'"
rostopic pub /speech/transcript std_msgs/String "data: 'What do I have today?'"

# Manually test TTS
rostopic pub /juno/tts std_msgs/String "data: 'Hello from terminal'"

# Check camera frames are arriving
rostopic hz /camera/image_raw

# Check audio is publishing
rostopic hz /audio/raw

# Check LED state changes
rostopic echo /juno/led_state

# Node health
rosnode list
rosnode info /whisper_tiny_transcriber
```

### rosnode Expected List (after full bringup)

```
/camera_node
/microphone_node
/whisper_tiny_transcriber
/juno_tts_node
```

State management, wake detection, emotion inference, and intent classification all run inside the backend process — they do not appear in `rosnode list`.

### Common Debug Patterns

| Symptom | Check |
| :--- | :--- |
| Wake word never fires | `rostopic echo /speech/transcript` — confirm the ASR/manual transcript source is producing output; check `JUNO_WAKE_PHRASE` env var |
| Emotion always `unknown` | `rostopic hz /camera/image_raw` — confirm 30 Hz; check backend log for OpenCV/cv_bridge errors |
| TTS silent | `rostopic echo /juno/tts`; check pyttsx3 installation on robot |
| Dashboard not updating | Check WebSocket in browser DevTools; confirm backend running on port 8000 |
| Backend fails to import rospy | Source catkin workspace before starting backend: `source devel/setup.bash` |
| Timer not advancing | `GET /api/status`; check `_timer_loop` asyncio task in backend logs |

---

# Appendix A: Preserved Requirements, Components, and Technical Planning Notes


## Appendix A1: Preserved from `docs/project_components.md`

## Juno Project Component Specifications

This document details the planned/final components of the Juno codebase, a Jupiter JUNO powered Personal Assistant Robot. On documentation-only branches, some implementation folders may not be present until the relevant integration branches are merged.

### 1. Backend (Python / FastAPI)
Located in `/backend`, this serves as the central brain of the system, handling business logic, data persistence, and orchestration.

#### Core Components
- **API Server (`main.py`, `src/api/app.py`)**: 
    - Built using **FastAPI**.
    - Manages REST endpoints and WebSockets for real-time state updates.
    - Orchestrates the "Command Pipeline" (Wake word -> Intent -> Action -> Response -> TTS).
- **Vision Module (`src/vision/`)**:
    - **Emotion Detector**: Uses camera frames to identify facial emotions (Happy, Neutral, Tired, Stressed, Frustrated). The current MVP uses a weighted mock predictor for testing/demo reliability.
    - **Emotion Smoother**: The current MVP uses a simple rolling-window/mode-based smoother. The proposed upgraded design in `docs/technical_requirements_emotion.md` replaces this with EMA fusion and hysteresis when time permits.
- **Speech Module (`src/speech/`)**:
    - **Text-to-Speech (TTS)**: Interfaces with the robot's speech capabilities to provide vocal affirmations and responses.
- **NLP Module (`src/nlp/`)**:
    - **Intent Classifier**: Parses user input (text or speech) to identify actions (Set Timer, Check Schedule, Play Music, etc.).
    - **Response Generator**: Crafts personalized responses based on the detected intent and the user's current emotional state.
- **Productivity Module (`src/productivity/`)**:
    - **Timer Service**: Implements focus timers (Pomodoro style).
    - **Music Service**: Plays calming/soothing background music to aid concentration.
- **Calendar Module (`src/calendar_module/`)**:
    - **Calendar Service**: Manages daily schedules, academic deadlines, and reminders.
    - **Database**: Uses SQLite (`juno_assist.db`) for persistent storage.

#### Testing
- **Backend Tests (`tests/`)**: Includes unit tests for `emotion_smoothing` and `intent_classifier` to ensure logic correctness.

---

### 2. Dashboard (React / Vite / Tailwind CSS)
Located in `/dashboard`, this provides a visual interface for the user to monitor Juno's status and manage their schedule.

#### Key Features
- **Status Panel**: Displays Juno's current mode (Idle, Active, Confirmation) and real-time emotion detection results.
- **Schedule Panel**: Lists the user's classes and meetings for the day.
- **Reminder Panel**: Shows upcoming deadlines and custom reminders.
- **Timer Panel**: Provides a visual countdown and controls for study sessions.
- **Command Panel**: Allows manual text input for users who prefer typing over voice commands.
- **WebSocket Integration**: Listens to `/ws/status` for instantaneous updates from the backend.

---

### 3. Catkin Workspace (ROS Noetic / Python)
Located in `/src`, these packages handle low-level hardware interaction and sensor processing.

#### Packages
- **`perception_pkg`**:
    - **Camera Node**: Captures and publishes video streams from the Jupiter robot's camera.
    - **Microphone Node**: Captures audio data for speech recognition.
- **`language_pkg`**:
    - **Whisper Tiny Transcriber**: Transcribes microphone audio using Hugging Face `openai/whisper-tiny` and publishes recognised text to `/speech/transcript`.
    - **TTS Node**: Subscribes to text messages and performs voice synthesis (using `pyttsx3` or `espeak`).
- **`juno_bringup`**:
    - **Centralized Launch (`launch/juno_robot.launch`)**: Initializes the camera, microphone, transcriber, and TTS nodes in a single command.

---

### 4. Documentation
Located in `/docs`, providing guidance on system architecture and integration.

- **Implementation Plan**: Roadmap for features like emotion recognition and productivity tools.
- **ROS Integration Guide**: Instructions for setting up the ROS environment on the Jupiter robot.
- **Jupiter Integration Notes**: Specifics on interfacing with the Jupiter hardware (LEDs, movement, sensors).
- **Project Component Specifications**: (This document) Detailed breakdown of the system architecture.

---

### 5. Functional Overview
| Feature | Implementation | Component |
| :--- | :--- | :--- |
| **Emotion Recognition** | OpenCV + CNN (Mocked in current version) | `backend/src/vision` |
| **Speech recognition** | Whisper Tiny ASR | `src/language_pkg` |
| **Text-to-Speech (TTS)** | ROS TTS Node / `pyttsx3` | `src/language_pkg` |
| **Schedule Management** | SQLite + Calendar Service | `backend/src/calendar_module` |
| **Affirmations** | NLP Response Generator | `backend/src/nlp` |
| **Study Support** | Timer Service + Music Service | `backend/src/productivity` |


## Appendix A2: Preserved from `docs/implementation_plan.md`

## Implementation Plan

### Phase 1: Mock-Based Prototype

Objective: prove the workflow without physical robot dependency.

Tasks:

1. Implement wake command detection.
2. Implement confirmation step.
3. Implement FastAPI backend.
4. Implement React dashboard.
5. Implement SQLite-based calendar/reminders.
6. Implement mock emotion detection.

Deliverable:

- System can be demonstrated from a laptop browser.

### Phase 2: Speech and Robot I/O

Objective: connect command input and response output to the robot.

Tasks:

1. Replace dashboard command input with Jupiter microphone input where available.
2. Replace mock speak output with Jupiter speaker output.
3. Keep dashboard as visual feedback for demonstration.

Deliverable:

- User can speak to the robot and hear responses.

### Phase 3: Vision Integration

Objective: replace mock emotion detection with real camera-based inference.

Tasks:

1. Capture frames from Jupiter camera.
2. Use OpenCV for face detection.
3. Crop face region.
4. Run CNN emotion classification.
5. Smooth predictions across recent frames.

Deliverable:

- Dashboard displays real-time estimated emotion.

### Phase 4: Evaluation

Suggested evaluation metrics:

- Wake command success rate.
- Confirmation success rate.
- Intent classification accuracy on predefined commands.
- Timer reliability.
- User satisfaction.
- Emotion detection stability across lighting and face-angle conditions.


## Appendix A3: Preserved from `docs/jupiter_integration_notes.md`

## Jupiter Robot Integration Notes

This repository uses `MockJupiterInterface` by default.

To integrate the physical Jupiter Robot, implement a new class such as:

```python
class RealJupiterInterface(JupiterInterface):
    def speak(self, text: str) -> None:
        # call Jupiter speaker / TTS API
        pass

    def listen(self) -> str:
        # call Jupiter microphone / STT API
        pass

    def get_camera_frame(self):
        # return camera frame
        pass

    def open_dashboard(self, url: str) -> None:
        # open dashboard on robot screen or connected browser
        pass

    def set_led_state(self, state: str) -> None:
        # optional LED / expression feedback
        pass
```

Then register it in the existing factory without removing mock/ROS selection. For example:

```python
def get_robot_interface() -> JupiterInterface:
    if settings.robot_interface == "real":
        return RealJupiterInterface()
    if settings.use_ros_robot:
        return RosJupiterInterface()
    return MockJupiterInterface()
```

This keeps laptop/mock mode available for development and demo fallback while allowing a real Jupiter implementation when the correct environment variable is set.

### Recommended Integration Priority

1. Speaker output
2. Microphone input
3. Camera input
4. LED or screen feedback
5. Optional movement or gestures

Movement is optional because the project scope is a desk-based personal assistant.


## Appendix A4: Preserved from `docs/technical_requirements_emotion.md`

## Facial Emotion Recognition — Technical Requirements

> Companion to `docs/product_requirements.md` § F4.  
> Covers the proposed full CV pipeline: face detection → CNN inference → class remapping → state determination.  
> **Coding agent:** Backend-Vision (`backend/src/vision/`)

> **Implementation note:** The current demo MVP may use a mock/simple emotion detector with smoothing for reliability. This document describes the proposed upgraded implementation for the final code branch or future work. Referenced backend paths may exist on integration branches before being merged into the documentation branch.

---

### 1. Problem Statement

The system must reliably classify a user's emotional state into one of five Juno-specific labels:

| Juno Label | Behavioural Meaning |
| :--- | :--- |
| `Happy` | Positive, engaged — Juno responds warmly |
| `Neutral` | Default resting state — Juno responds normally |
| `Tired` | Low energy / drowsy — Juno suggests a break or shorter responses |
| `Stressed` | Anxious or under pressure — Juno lowers stimulus, offers calm guidance |
| `Frustrated` | Irritated, blocked — Juno uses shorter sentences, offers help |

These labels are **not** directly available from any standard emotion dataset. The pipeline must bridge from a standard CNN's output to these five operational states in a principled way.

---

### 2. Pipeline Overview

Camera frames enter the pipeline via `RosJupiterInterface.get_camera_frame()`, which returns `self.latest_frame` — an OpenCV BGR array stored by `_camera_callback` each time a `sensor_msgs/Image` message arrives on `/camera/image_raw`. No intermediate ROS node is required; the backend subscribes directly.

```
camera_node  →  /camera/image_raw  →  RosJupiterInterface._camera_callback
                                              │
                              robot.get_camera_frame()
                                              │
                                              ▼
Camera Frame (latest, up to 30 Hz)
        │
        ▼
┌───────────────────┐
│  Face Detection   │  OpenCV DNN or MediaPipe Face Mesh
│  (confidence > θ) │  Reject frame if no face or confidence < 0.70
└────────┬──────────┘
         │  Bounding box
         ▼
┌───────────────────┐
│  Preprocessing    │  Crop → 48×48 or 224×224 → normalise
└────────┬──────────┘
         │  Tensor
         ▼
┌───────────────────┐
│  CNN Inference    │  Softmax over 7 standard FER classes
│  (FER+ or Mini-   │  Output: probability vector P_raw ∈ ℝ⁷
│   Xception)       │
└────────┬──────────┘
         │  P_raw
         ▼
┌───────────────────┐
│  Class Remapping  │  Projection matrix M ∈ ℝ⁵ˣ⁷
│                   │  P_juno = M · P_raw  (see § 5)
└────────┬──────────┘
         │  P_juno ∈ ℝ⁵
         ▼
┌───────────────────┐
│  EMA Fusion       │  P_t = α · P_juno + (1-α) · P_{t-1}
│  (on distribution)│  α = 0.30, skip update if face not detected
└────────┬──────────┘
         │  P_t (smoothed distribution)
         ▼
┌───────────────────┐
│  Hysteresis       │  Candidate = argmax(P_t)
│  State Machine    │  Transition only after dwell ≥ T_dwell frames
└────────┬──────────┘
         │  EmotionState (final)
         ▼
   Stored in backend state (core/state.py)
   Broadcast → /ws/status  (field: current_emotion)
   Optional: robot.set_led_state() on emotion-triggered break recommendation
```

---

### 3. Face Detection

#### 3.1 Recommended Model

Use **OpenCV's DNN face detector** (`deploy.prototxt` + `res10_300x300_ssd_iter_140000.caffemodel`) rather than Haar cascades, as it handles partial occlusion and varied lighting better.

```python
net = cv2.dnn.readNetFromCaffe(prototxt_path, caffemodel_path)
blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104, 177, 123))
net.setInput(blob)
detections = net.forward()
confidence = detections[0, 0, i, 2]
```

Alternatively, **MediaPipe FaceMesh** is acceptable if the robot has sufficient compute for the heavier model.

#### 3.2 Frame Rejection Policy

- If no face is detected in the frame: **do not update** the EMA smoother. The last known smoothed distribution `P_t` is retained.
- If face detection confidence < 0.70: treat as no-face (reject frame).
- If face bounding box area < 1 000 px²: reject (too far from camera to be reliable).

This is **confidence gating** — it ensures only high-quality frames contribute to the emotional state, which is strictly better than naive window averaging where noisy frames pollute the history.

---

### 4. CNN Model Selection

#### 4.1 Recommended: Mini-Xception (FER+ trained)

| Property | Value |
| :--- | :--- |
| Input | 64×64 grayscale |
| Output | 7-class softmax (FER2013 classes) |
| Size | ~2 MB |
| Inference (CPU) | ~15 ms per frame |
| Source | `oarriaga/face_classification` (MIT licence) |

The 7 standard FER2013 classes output by this model are:

```
Index  Label
  0    Angry
  1    Disgust
  2    Fear
  3    Happy
  4    Sad
  5    Surprise
  6    Neutral
```

#### 4.2 Alternative: DeepFace Library

If the team prefers a plug-and-play approach, `deepface` wraps multiple pre-trained models (VGG-Face, ArcFace, Facenet):

```python
from deepface import DeepFace
result = DeepFace.analyze(frame, actions=["emotion"], enforce_detection=False)
probabilities = result[0]["emotion"]  # dict: {angry, disgust, fear, happy, sad, surprise, neutral}
```

Use `enforce_detection=False` to gracefully handle frames where a face is marginal.

**Trade-off:** DeepFace is easier to integrate but adds ~200 MB of dependencies and is slower (~80 ms/frame on CPU). Mini-Xception is preferred for the Jupiter robot's limited compute.

#### 4.3 Preprocessing (Mini-Xception path)

```python
face_roi = frame[y:y+h, x:x+w]
face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
face_resized = cv2.resize(face_gray, (64, 64))
face_norm = face_resized.astype("float32") / 255.0
face_tensor = np.expand_dims(np.expand_dims(face_norm, -1), 0)  # (1, 64, 64, 1)
P_raw = model.predict(face_tensor)[0]  # shape (7,)
```

---

### 5. Class Remapping: FER7 → Juno5

This is the critical design decision. Standard FER2013 classes do not include `Tired`, `Stressed`, or `Frustrated`. The remapping uses a fixed **projection matrix M** that encodes domain knowledge about which standard emotions correspond to each Juno state.

#### 5.1 Projection Matrix

```
            Angry  Disgust  Fear  Happy   Sad  Surprise  Neutral
             [0]     [1]    [2]    [3]    [4]     [5]      [6]
Happy      [  0.0    0.0    0.0    1.0    0.0     0.0      0.0  ]
Neutral    [  0.0    0.0    0.0    0.0    0.0     0.2      0.8  ]
Tired      [  0.0    0.0    0.0    0.0    1.0     0.0      0.0  ]
Stressed   [  0.3    0.1    0.6    0.0    0.0     0.0      0.0  ]
Frustrated [  0.7    0.3    0.0    0.0    0.0     0.0      0.0  ]
```

As Python (stored in `backend/src/vision/emotion_detector.py`):

```python
import numpy as np

MAPPING_MATRIX = np.array([
    # Angry  Disgust  Fear  Happy   Sad  Surprise  Neutral
    [  0.0,    0.0,   0.0,   1.0,   0.0,    0.0,     0.0],  # Happy
    [  0.0,    0.0,   0.0,   0.0,   0.0,    0.2,     0.8],  # Neutral
    [  0.0,    0.0,   0.0,   0.0,   1.0,    0.0,     0.0],  # Tired
    [  0.3,    0.1,   0.6,   0.0,   0.0,    0.0,     0.0],  # Stressed
    [  0.7,    0.3,   0.0,   0.0,   0.0,    0.0,     0.0],  # Frustrated
], dtype=np.float32)

def remap(P_raw: np.ndarray) -> np.ndarray:
    """Project 7-class FER softmax onto 5 Juno emotion classes."""
    P_juno = MAPPING_MATRIX @ P_raw          # shape (5,)
    P_juno = P_juno / P_juno.sum()           # re-normalise to sum to 1
    return P_juno
```

#### 5.2 Mapping Rationale

| Juno State | FER Source | Weight Justification |
| :--- | :--- | :--- |
| `Happy` | Happy (1.0) | Direct 1:1 correspondence |
| `Neutral` | Neutral (0.8) + Surprise (0.2) | Surprise is often neutral in brief interactions; slight blend prevents over-sensitivity to mild surprise |
| `Tired` | Sad (1.0) | Fatigue manifests as low-arousal negative affect, visually closest to sadness (drooped eyelids, downturned mouth) |
| `Stressed` | Fear (0.6) + Angry (0.3) + Disgust (0.1) | Stress is high-arousal negative affect; fear dominates, anger secondary for deadline stress |
| `Frustrated` | Angry (0.7) + Disgust (0.3) | Frustration sits between anger and disgust; anger slightly dominant |

> **Note:** These weights are a starting point. They should be validated empirically on a small dataset of the target user population if time permits. The matrix rows need not sum to 1 (renormalisation is applied in `remap()`), so individual row weights express relative contribution strength.

---

### 6. State Determination: EMA + Hysteresis

This is the replacement for the current majority-vote smoother. The approach operates in two stages.

#### 6.1 Stage 1 — EMA on the Probability Distribution

Rather than collecting discrete labels and voting on them, we apply an exponential moving average **directly on the 5-class probability vector**. This retains uncertainty information across frames — a distinction the majority vote discards.

```
P_t = α · P_juno_new + (1 - α) · P_{t-1}
```

- **α = 0.30** (smoothing factor; lower = more inertia, higher = more reactive)
- `P_{t-1}` is initialised to `[0, 1, 0, 0, 0]` (Neutral) on startup
- Update is **skipped** (P_t unchanged) on frames where face detection fails

**Why EMA on distributions is better than label averaging:**
- Label averaging (majority vote, mean) loses the *degree* of confidence. A frame with 55% Tired and 44% Stressed votes the same as a frame with 99% Tired. EMA on distributions preserves this.
- The resulting `P_t` is a proper probability distribution and can be directly reported as `emotion_confidence` in the WebSocket payload.

```python
ALPHA = 0.30

class EMAFusion:
    def __init__(self):
        self.P_t = np.array([0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)  # start Neutral

    def update(self, P_juno: np.ndarray) -> np.ndarray:
        self.P_t = ALPHA * P_juno + (1 - ALPHA) * self.P_t
        return self.P_t

    def skip(self) -> np.ndarray:
        return self.P_t  # no update; return last known distribution
```

#### 6.2 Stage 2 — Hysteresis State Machine

The candidate emotion is `argmax(P_t)`, but the **output state does not change immediately**. A transition is only committed after the candidate has been the argmax for at least `T_dwell` consecutive frames.

```
T_dwell = 45 frames  (≈ 1.5 seconds at 30 Hz)
```

This prevents the displayed state from flickering between adjacent emotions (e.g., Neutral ↔ Tired) due to momentary expression changes.

```python
DWELL_FRAMES = 45

class HysteresisStateMachine:
    def __init__(self):
        self.current_state = EmotionState.NEUTRAL
        self.candidate = EmotionState.NEUTRAL
        self.dwell_count = 0

    def update(self, P_t: np.ndarray) -> EmotionState:
        LABELS = [EmotionState.HAPPY, EmotionState.NEUTRAL,
                  EmotionState.TIRED, EmotionState.STRESSED, EmotionState.FRUSTRATED]
        new_candidate = LABELS[int(np.argmax(P_t))]

        if new_candidate == self.candidate:
            self.dwell_count += 1
        else:
            self.candidate = new_candidate
            self.dwell_count = 1

        if self.dwell_count >= DWELL_FRAMES and new_candidate != self.current_state:
            self.current_state = new_candidate
            self.dwell_count = 0  # reset after committing transition

        return self.current_state
```

#### 6.3 Combined Flow

```python
## Called once per camera frame
def process_frame(frame) -> tuple[EmotionState, float]:
    face, face_confidence = detect_face(frame)

    if face is None or face_confidence < 0.70:
        P_t = ema.skip()
    else:
        P_raw = cnn.infer(preprocess(face))       # shape (7,)
        P_juno = remap(P_raw)                      # shape (5,)
        P_t = ema.update(P_juno)

    state = hsm.update(P_t)
    confidence = float(P_t[np.argmax(P_t)])
    return state, confidence
```

---

### 7. Summary: Why Not Averaging?

| Method | What it discards | Problem |
| :--- | :--- | :--- |
| **Label mean** (e.g., encode Happy=0, Neutral=1…) | Ordinal structure is meaningless for emotions | "Average of Happy and Frustrated" has no semantic value |
| **Rolling mode / majority vote** (current impl) | Per-frame confidence scores | A barely-winning label in a noisy window looks identical to a dominant one |
| **Simple rolling average of probabilities** | History weighting | All frames in window weighted equally; old stale frames matter as much as the latest |
| **EMA on distributions + Hysteresis** (proposed) | Nothing meaningful | Retains confidence, weights recent frames more, prevents flickering on transitions |

The proposed method has two tunable parameters with clear semantics:
- `α` (EMA decay): controls how quickly the system responds to genuine changes
- `T_dwell` (hysteresis frames): controls how long a new emotion must persist before it is committed

---

### 8. Proposed Changes to Existing/Future Code

#### 8.1 `backend/src/vision/emotion_smoothing.py`

When implementing the upgraded emotion pipeline, replace the `EmotionSmoother` class with `EMAFusion` + `HysteresisStateMachine` as specified in § 6.1 and § 6.2.

The existing/simple `Counter.most_common` approach in `EmotionSmoother` is the mode-based discrete smoother used by the MVP. It can be retired when the upgraded pipeline is implemented.

Rename the file to `emotion_fusion.py` (or keep `emotion_smoothing.py` and replace the class) — keep the import path stable so `emotion_detector.py` doesn't break.

#### 8.2 `backend/src/vision/emotion_detector.py`

Replace the mock random predictor with the real pipeline:

1. Load face detection model on init
2. Load CNN model on init  
3. In `predict_from_frame(frame)`:
   - Call face detector
   - If face found and confident: preprocess → CNN infer → remap → EMA update
   - If no face: EMA skip
   - Call hysteresis state machine
   - Return `(EmotionState, confidence: float)`

The method signature should change from `predict_from_frame(frame) -> EmotionState` to `predict_from_frame(frame) -> tuple[EmotionState, float]` to expose confidence to the WebSocket payload.

#### 8.3 Update `backend/tests/test_emotion_smoothing.py`

The existing test:

```python
def test_emotion_smoother_returns_majority():
    smoother = EmotionSmoother(window_size=5)
    smoother.add(EmotionState.TIRED)
    smoother.add(EmotionState.NEUTRAL)
    smoother.add(EmotionState.NEUTRAL)
    assert smoother.current() == EmotionState.NEUTRAL
```

Must be replaced with tests for `EMAFusion` and `HysteresisStateMachine`:

| Test | Assertion |
| :--- | :--- |
| EMA initialises to Neutral distribution | `P_t[1] == 1.0` on fresh instance |
| EMA skip does not change distribution | Identical `P_t` before and after `skip()` |
| EMA update moves toward new input | `P_t` after update closer to `P_juno` than before |
| Hysteresis does not transition on fewer than `DWELL_FRAMES` | State unchanged after 44 Tired candidates |
| Hysteresis transitions after `DWELL_FRAMES` | State becomes Tired after 45 Tired candidates |
| Hysteresis resets dwell count on candidate change | Injecting Neutral mid-run resets count |

---

### 9. Tuning Parameters

| Parameter | Location | Default | Guidance |
| :--- | :--- | :--- | :--- |
| `ALPHA` | `emotion_fusion.py` | `0.30` | Increase → faster response, more noise. Decrease → smoother, slower |
| `DWELL_FRAMES` | `emotion_fusion.py` | `45` (1.5 s) | Decrease for faster UI updates; increase to reduce false transitions |
| Face confidence threshold | `emotion_detector.py` | `0.70` | Lower if robot is far from user; raise if too many false detections |
| Min face area (px²) | `emotion_detector.py` | `1000` | Tune based on typical user distance from robot camera |
| Emotion poll interval | `core/config.py` | `3.0 s` | Set via env var `JUNO_EMOTION_UPDATE_SECONDS` |
| CNN model path | `core/config.py` | `models/emotion_model.h5` | Set via env var `EMOTION_MODEL_PATH` |

---

### 10. File Locations

```
backend/
├── src/
│   └── vision/
│       ├── emotion_detector.py     ← REPLACE mock with real pipeline (§ 8.2)
│       ├── emotion_smoothing.py    ← REPLACE Counter with EMA + Hysteresis (§ 8.1)
│       └── __init__.py
└── tests/
    └── test_emotion_smoothing.py   ← UPDATE tests (§ 8.3)

models/                             ← ADD: store CNN weights here (not in src/)
└── emotion_model.h5                ← Mini-Xception weights
```

The face detection model weights (Caffe `.prototxt` + `.caffemodel`) should also live in `models/` and be loaded via path from `core/config.py`, not hardcoded.


### Ekman-7 Emotion Taxonomy Update

The current implementation keeps the original JUNO emotion vocabulary (`happy`, `sad`, `tired`, `frustrated`, `stressed`, `neutral`) while adding a switchable Ekman mode display labels (`angry`, `disgusted`, `scared`, `happy`, `sad`, `surprised`, `neutral`) while preserving raw Ekman values (`anger`, `disgust`, `fear`, `happiness`, `sadness`, `surprise`, `neutral`). The backend stores canonical Ekman evidence internally and maps it to the selected dashboard mode without reloading the model. It may return `unknown` when the camera frame or classifier confidence is insufficient. The default model is now `mo-thecreator/vit-Facial-Expression-Recognition` through the `face_expression` backend, replacing the previous SmolVLM default for normal robot operation.
