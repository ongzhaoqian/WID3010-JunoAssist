# Juno Assist — Product Requirements Document

> **Target platform:** Jupiter JUNO robot · ROS Noetic · Python 3.10+ · FastAPI · React/Vite  
> **Build system:** catkin_ws (`/src`) with packages connected to `/backend` via REST + WebSocket APIs  
> **Database:** SQLite (`backend/juno_assist.db`)

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
- `moonshine_transcriber` converts audio to text and publishes on `/speech/transcript`.
- The backend `WakeWordDetector` (`activation/wake_word_detector.py`) receives transcripts via `RosJupiterInterface.listen()`, which drains an internal queue populated by the `/speech/transcript` subscriber.
- The following trigger phrases shall activate the confirmation flow (case-insensitive, as configured by `JUNO_WAKE_PHRASE` env var, default `"hey, juno"`):
  - `"hey, juno"` / `"hey juno"`
  - `"ok juno"`
  - `"juno"`
- On detection, the backend transitions the global `RobotMode` to `CONFIRMATION`.
- False-positive rate must be below 5 per 30-minute idle session.
- Wake detection latency from end of utterance to state change: ≤ 800 ms.

#### ROS Interface (via RosJupiterInterface)

| Direction | Topic | Message Type | Description |
| :--- | :--- | :--- | :--- |
| Subscribe | `/speech/transcript` | `std_msgs/String` | Incoming STT output, queued internally for `listen()` |

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
| `POST` | `/api/timer/start` | `{ minutes? }` | Start focus session |
| `POST` | `/api/music/play` | — | Start background music |
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
| `moonshine_transcriber` | `language_pkg` | `transcriber.py` | Runs Moonshine ONNX STT, publishes transcript strings |
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
│  │  microphone_node  │──────────────────────────────────────────────►│
│  └───────────────────┘                         │                     │
│                                                │                     │
│  [language_pkg]                                ▼                     │
│  ┌──────────────────────┐  /speech/transcript (std_msgs/String)      │
│  │ moonshine_transcriber│◄── /audio/raw                              │
│  │                      │──────────────────────────────────────────►│
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
| `/audio/raw` | `std_msgs/Float32MultiArray` | `microphone_node` | `moonshine_transcriber` | 16 kHz chunks |
| `/camera/image_raw` | `sensor_msgs/Image` | `camera_node` | Backend (`RosJupiterInterface`) | 30 Hz |
| `/speech/transcript` | `std_msgs/String` | `moonshine_transcriber` | Backend (`RosJupiterInterface`) | On utterance |
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
3. `moonshine_transcriber` (language_pkg) — depends on microphone_node
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
rostopic pub /speech/transcript std_msgs/String "data: 'Hey, Juno'"
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
rosnode info /moonshine_transcriber
```

### rosnode Expected List (after full bringup)

```
/camera_node
/microphone_node
/moonshine_transcriber
/juno_tts_node
```

State management, wake detection, emotion inference, and intent classification all run inside the backend process — they do not appear in `rosnode list`.

### Common Debug Patterns

| Symptom | Check |
| :--- | :--- |
| Wake word never fires | `rostopic echo /speech/transcript` — confirm STT is producing output; check `JUNO_WAKE_PHRASE` env var |
| Emotion always `unknown` | `rostopic hz /camera/image_raw` — confirm 30 Hz; check backend log for OpenCV/cv_bridge errors |
| TTS silent | `rostopic echo /juno/tts`; check pyttsx3 installation on robot |
| Dashboard not updating | Check WebSocket in browser DevTools; confirm backend running on port 8000 |
| Backend fails to import rospy | Source catkin workspace before starting backend: `source devel/setup.bash` |
| Timer not advancing | `GET /api/status`; check `_timer_loop` asyncio task in backend logs |
