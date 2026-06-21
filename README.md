# WID3010-JunoAssist

## WID3010: Autonomous Robots
Universiti Malaya, Academic Year 2025/2026, Semester 2  
Group 5

| Name | Matric ID |
|---|---|
| Wong Yoong Yee | S2118482 |
| Jonathan Siew Zunxian | 23004944 |
| Ong Zhao Qian | 23004986 |
| Vanness Liu Chuen Wei | 23005021 |
| Anas Abdurahman Mohammad | 23055727 |

# JUNO Assist: Jupiter Robot Personal Daily Assistant

JUNO Assist is a Jupiter Robot-based personal daily assistant prototype. It combines ROS nodes, a FastAPI backend, a React dashboard, speech interaction, facial-expression analysis, schedule/reminder management, study timer controls, emotion-aware music, a destressing game workflow, and user-scoped data storage.

The project is built for the WID3010 Autonomous Robots alternative assessment and can run in two practical environments, as follows.

1. **Mock / Laptop Mode** — runs the FastAPI backend and React dashboard without the Jupiter Robot hardware.
2. **Jupiter Robot / ROS Mode** — connects the backend to ROS topics for the Jupiter camera, microphone, ASR transcriber, TTS node, and robot interaction loop.

## Current System at a Glance

| Area | Current implementation |
|---|---|
| Robot activation | Wake phrase, confirmation flow, active/sleep state handling |
| Dashboard access | Login and sign-up with bearer-token authentication |
| Default accounts | `mackwongyy@gmail.com / 12345678`, `jonathansiew@hotmail.com / 87654321` |
| Storage | SQLite with user-scoped data tables and automatic clean-start refresh |
| Speech input | ROS microphone stream with Whisper Tiny transcription; manual dashboard text-based command fallback |
| Speech output | ROS TTS bridge with configurable British English eSpeak profile and stop control |
| Vision | Jupiter camera stream, user-controlled camera toggle, optional facial-emotion model |
| Emotion modes | Switchable **JUNO Mode** and **Ekman Mode** using one internal Ekman evidence pipeline, with a large colour-coded dashboard emotion indicator |
| Schedules/reminders | User-scoped CRUD from dashboard and voice commands |
| Study timer | Flexible spoken duration parsing, pause/resume/stop buttons, fuzzy voice stop commands, completion bell |
| Music | Spotify dashboard embed selected by current displayed emotion |
| Movement break / destressing game | motions.games popup workflow, stress-relief movement-break prompt |
| Date/time | Dashboard clock with timezone/location selector and local storage persistence |
| Power lifecycle | Sleep/power-off closes dashboard or shows fallback overlay, stops runtime services, and preserves ROS Core |
| Testing | Pytest backend tests and Vite frontend production build |

## Documentation Guide

| File | Purpose |
|---|---|
| `README.md` | Main project overview, architecture, setup, and current feature summary |
| `docs/product_requirements.md` | Product requirements, design decisions, and expanded system specification |
| `docs/ros_integration_guide.md` | ROS launch guide, terminal flow, topics, robot setup, and troubleshooting |
| `docs/project_manual_scaled_demo.md` | Demo plan, rubric mapping, team responsibilities, and evidence planning |
| `docs/final_submission_checklist.md` | Final submission and video checklist |
| `docs/q2_evidence.md`, `docs/q3_answer.md` | Evidence and explanations for ROS workspace/API assessment questions |

For robot execution, start with `docs/ros_integration_guide.md`.

For project scope and design rationale, start with `docs/product_requirements.md`.

## Assessment Mapping

| Assessment Item | Repository Support | Responsible Members |
|---|---|---|
| Q1 — robotics application, objectives, AI techniques, experimental setup, testing scenarios | README, `docs/product_requirements.md`, `docs/final_submission_checklist.md` | Vanness |
| Q2 — ROS workspace and catkin setup | `src/` catkin workspace with `perception_pkg`, `language_pkg`, `juno_bringup` | Yoong Yee, Jonathan, Anas |
| Q3 — ROS packages, APIs, publishers/subscribers, unit testing | ROS scripts, launch file, backend ROS bridge, FastAPI tests | Yoong Yee, Jonathan, Vanness, Anas |
| Q4 — `rqt_graph` visualisation | ROS guide and troubleshooting notes | Zhao Qian |
| Q5 — manual launch/run instructions | ROS integration guide and quick-start sections below | Yoong Yee, Anas |
| Q6 — robot demo video | Demo flow and final submission checklist | Zhao Qian |

## Repository Structure

```text
WID3010-JunoAssist/
├── backend/
│   ├── main.py
│   ├── requirements*.txt
│   ├── src/
│   │   ├── activation/          # wake and confirmation handling
│   │   ├── api/                 # FastAPI routes, WebSocket, dashboard bridge
│   │   ├── auth/                # user accounts, sessions, password hashing
│   │   ├── calendar_module/     # schedule/reminder SQLite service
│   │   ├── core/                # state, settings, Pydantic models
│   │   ├── nlp/                 # intent classification, phrase bank, responses
│   │   ├── productivity/        # timer, music, fitness, break recommendation
│   │   ├── robot/               # mock/Jupiter/ROS robot interfaces
│   │   ├── speech/              # backend speech helpers
│   │   ├── system/              # dashboard lifecycle and process cleanup
│   │   └── vision/              # camera emotion classification and fusion
│   └── tests/                   # pytest test suite
├── dashboard/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/          # dashboard panels and modals
│   │   └── lib/api.js           # API helper with auth token support
│   └── package.json
├── src/
│   ├── juno_bringup/            # ROS launch file
│   ├── language_pkg/            # ASR transcriber and TTS ROS nodes
│   └── perception_pkg/          # camera and microphone ROS nodes
├── docs/
├── .github/
└── README.md
```

## Runtime Architecture

```text
User
│
├── React Dashboard
│   ├── Auth screen and token storage
│   ├── Date/time panel with timezone selector
│   ├── Robot status and latest JUNO response
│   ├── Camera / Vision Module / emotion mode controls
│   ├── Schedule and reminder management
│   ├── Study timer controls
│   ├── Music and destressing game panels
│   └── WebSocket status updates
│
├── ROS Speech Pipeline
│   ├── Microphone node
│   ├── Whisper Tiny transcriber node
│   ├── /speech/transcript
│   ├── Backend intent processing
│   ├── /juno/tts
│   └── TTS node / robot speaker
│
├── ROS Vision Pipeline
│   ├── Jupiter camera node on /dev/video2
│   ├── /camera/image_raw
│   ├── Backend camera frame cache
│   ├── MJPEG dashboard stream
│   └── Optional facial emotion classifier
│
└── FastAPI Backend
    ├── Authentication and user isolation
    ├── Global robot state manager
    ├── SQLite persistence services
    ├── Intent classifier and phrase bank
    ├── Timer / music / fitness services
    ├── Vision emotion fusion and speech override
    ├── Dashboard lifecycle manager
    └── ROS robot bridge or mock robot adapter
```

## Core Feature Summary

### 1. Authentication and User Isolation

The dashboard begins with a login/sign-up screen. API calls use bearer tokens stored by the frontend and sent automatically through `dashboard/src/lib/api.js`.

Default prototype accounts are created on startup if missing:

| Username | Password |
|---|---|
| `mackwongyy@gmail.com` | `12345678` |
| `jonathansiew@hotmail.com` | `87654321` |

Passwords are stored as PBKDF2-HMAC hashes, not plaintext. User-facing data is scoped by user ID so one user cannot access another user’s schedules, reminders, fitness profile, or fitness sessions.

Relevant backend module:

```text
backend/src/auth/user_service.py
```

### 2. Clean Database Start

The backend supports a clean-start workflow for demos and testing. Runtime tables are cleared when the backend starts if enabled:

```env
JUNO_DATABASE_REFRESH_ON_START=true
```

The implementation removes dependence on old hardcoded sample datasets and avoids loading bundled dummy schedule/reminder records. Default user accounts remain available because they are part of the authentication setup.

### 3. Wake, Confirmation, Active, and Sleep Flow

The intended interaction flow is:

```text
Idle mode
→ user says "Hey, John" or "Hey, Juno"
→ JUNO asks for confirmation
→ user says "yes"
→ Active mode
→ dashboard opens or reuses existing page
→ user interacts through voice and dashboard
→ sleep/power-off closes dashboard or shows fallback overlay
```

Power lifecycle handling includes best-effort cleanup of JUNO runtime processes while excluding ROS Core-related processes.

Relevant backend module:

```text
backend/src/system/dashboard_lifecycle.py
```

### 4. Dashboard Date and Time Panel

The dashboard has a live current date/time window above Robot Status, Study Timer, and Most Recent Response. Users can select a timezone/location preset or use the device timezone. The selected timezone is saved in browser local storage, with location and timezone presets including UTC.

### 5. Camera Window and Vision Module

The dashboard includes an embedded Jupiter Camera View. The camera is off by default on first load, and the user can switch it on manually.

The camera and emotion model are separate, as follows.

| Mode | Behaviour |
|---|---|
| Camera off | Placeholder shown; no live image |
| Camera on, Vision off | Live camera monitor only |
| Camera on, Vision on | Live camera plus facial-emotion analysis |

The ROS camera node uses `/dev/video2` for the Jupiter RGB camera and refuses `/dev/video1`, which is reserved for camera metadata.

Relevant ROS script:

```text
src/perception_pkg/scripts/camera_node.py
```

### 6. Switchable JUNO/Ekman Emotion Modes

The vision system uses one internal Ekman evidence pipeline and lets the dashboard switch display modes without reloading the model.

#### Ekman Mode Display Labels

| Raw Ekman Value | Frontend Display Label |
|---|---|
| `anger` | Angry |
| `disgust` | Disgusted |
| `fear` | Scared |
| `happiness` | Happy |
| `sadness` | Sad |
| `surprise` | Surprised |
| `neutral` | Neutral |

The Jupiter Camera View also preserves the raw Ekman emotion separately.

#### JUNO Mode labels

```text
happy, sad, tired, frustrated, stressed, neutral
```

The mapping examples of raw Ekman emotion labels and the displayed emotion labels are as follows.

| Internal Evidence | JUNO Display |
|---|---|
| `happiness` | happy |
| `sadness` | sad |
| `fear` | stressed |
| `anger` or `disgust` | frustrated |
| speech says 'I am tired' | tired |
| `neutral` | neutral |

`tired` is not forced from face-only Ekman classification. It is used when speech content explicitly says the user is tired, sleepy, exhausted, drained, or fatigued.

The default vision settings are as follows.

```env
JUNO_VISION_BACKEND=face_expression
JUNO_VISION_MODEL_ID=mo-thecreator/vit-Facial-Expression-Recognition
JUNO_VISION_EMOTION_MODE_DEFAULT=juno
JUNO_VISION_DEVICE=auto
JUNO_VISION_REQUIRE_FACE=false
```

SmolVLM remains available as an experimental backend, with the configuration settings as follows.

```env
JUNO_VISION_BACKEND=smolvlm
JUNO_VISION_MODEL_ID=HuggingFaceTB/SmolVLM-256M-Instruct
```

### 7. Speech-Prioritised Emotion Handling

Vision is treated as an estimate, not the final truth. Explicit user speech is given priority.

Example:

```text
Camera: neutral, 0.62
User says: "I am stressed"
Internal Ekman: fear
JUNO Mode display: stressed
Source: speech override
```

Configuration:

```env
JUNO_SPEECH_EMOTION_OVERRIDE_SECONDS=45.0
```

### 8. Speech Recognition and TTS

The ROS speech path uses Whisper Tiny for lightweight automatic speech recognition, as follows.

```env
JUNO_ASR_MODEL_ID=openai/whisper-tiny
JUNO_ASR_TASK=translate
JUNO_ASR_SAMPLE_RATE=16000
```

TTS is handled through ROS topics. The TTS node supports a configurable non-default voice profile, as follows.

```env
JUNO_TTS_BACKEND=espeak
JUNO_TTS_VOICE=en-gb+f3
JUNO_TTS_RATE=148
JUNO_TTS_PITCH=55
JUNO_TTS_AMPLITUDE=135
JUNO_TTS_WORD_GAP=6
```

The dashboard and backend support immediate stop commands for speech/music, while preserving timer-specific stop behaviour.

### 9. Schedules and Reminders

Schedules and reminders are stored per user. They can be created from the dashboard or by voice.

The supported fields are as follows.

```text
title, date, time, type, priority
```

The parser supports flexible date/time expressions, such as the following prompts.

```text
25 May
25/05/2026
tomorrow
next Monday
nine pm
nine thirty
half past nine
quarter to six
```

### 10. Study Timer

The study timer supports both dashboard and voice control with dashboard controls as follows.

```text
Start Timer
Pause Timer
Resume Timer
Stop Timer
```

Supported spoken durations include the following prompts.

```text
25 minutes
twenty five minutes
1 minute 30 seconds
one minute thirty seconds
90 seconds
half an hour
quarter of an hour
one and a half hours
1h 30m
2:30
```

Timer setup can be cancelled with phrases, such as the following prompts.

```text
cancel
not now
skip
never mind
no timer
stop
```

Fuzzy timer-control commands while running include the following prompts.

```text
pause timer
resume timer
stop timer
end the countdown
cancel the focus session
reset timer
```

A bell sound plays on the dashboard when the timer completes.

### 11. Emotion-Aware Music

The dashboard includes a Spotify music panel. When music is requested, JUNO selects a playlist based on the current displayed emotion.

Emotion-specific playlist URLs are configurable in `.env.example`, as follows.

```env
JUNO_SPOTIFY_HAPPINESS_URL=...
JUNO_SPOTIFY_FEAR_URL=...
JUNO_SPOTIFY_ANGER_URL=...
JUNO_SPOTIFY_UNKNOWN_URL=...
```

### 12. Movement Break and Destressing Game Feature

The Movement Break panel includes a **Play Destressing Game** button. The game workflow prioritises opening `https://motions.games/` in a separate popup/window so the dashboard stays open. If the popup is blocked, the user can open the game in a new tab. `motions.games` hosts several camera-based motion games, not a single fixed "6-7" challenge, so the dashboard treats it as a generic camera-based movement break rather than a score-specific game.

The Movement Break panel positions the game as a short focus-reset and stress-relief activity. When the backend WebSocket state exposes `break_suggested: true`, the dashboard shows a highlighted prompt: **“JUNO recommends a movement break — try the destress game!”** The prompt button scrolls to the Movement Break panel.

Score/statistics saving (fitness profile, calorie estimate, one-off/cumulative session history) has been removed from the dashboard; the panel now only launches the game.

### 12.1 Prominent Emotion Indicator

The **Robot Status** panel now places the current emotion estimate in a large, centred badge for clearer video demonstration. The badge is colour-coded as follows.

- Red `#ef4444` for stress-class states such as stressed, fearful/scared, angry, frustrated, disgusted.
- Blue `#60a5fa` for low-energy states such as tired and sad.
- Green `#4ade80` for positive/focused states such as happy, calm, and focused.
- Grey `#94a3b8` for neutral and unknown.

Stress-class states add a pulse animation and set `break_suggested` in the status payload so the dashboard can recommend a movement break.

### 13. System Lifecycle and Duplicate Backend Prevention

When JUNO sleeps/powers off, the following events happen.

- the dashboard receives a close signal,
- the dashboard attempts to close itself,
- a powered-off overlay is shown if the browser blocks `window.close()`,
- camera and Vision Module are switched off,
- timer/music are stopped,
- configured auxiliary JUNO runtime processes are cleaned up,
- ROS Core is excluded.

When JUNO powers on again, the backend attempts to reuse or focus the same dashboard page before opening a new page.

If `rqt_graph` shows multiple `/juno_backend_bridge_*` nodes, it usually means multiple backend processes are running at the same time. Stop duplicate backend processes and keep only one `backend/main.py` instance connected to ROS.

## Main API Endpoints

### Authentication

```text
POST /api/auth/signup
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
```

### Robot and Status

```text
GET  /api/status
GET  /ws/status
POST /api/command
POST /api/robot/sleep
POST /api/robot/stop
POST /api/robot/speak
```

### Vision

```text
GET  /api/vision/status
POST /api/vision/camera/start
POST /api/vision/camera/stop
POST /api/vision/camera/refresh
POST /api/vision/model/start
POST /api/vision/model/stop
GET  /api/vision/mode
POST /api/vision/mode
POST /api/vision/analyse
GET  /api/vision/camera/frame.jpg
GET  /api/vision/camera/stream
```

### Schedule and Reminders

```text
GET    /api/schedule/today
POST   /api/schedule
DELETE /api/schedule/{item_id}
GET    /api/reminders
POST   /api/reminders
DELETE /api/reminders/{item_id}
GET    /api/deadlines
```

### Timer

```text
POST /api/timer/start
POST /api/timer/pause
POST /api/timer/resume
POST /api/timer/stop
POST /api/timer/delete
```

### Fitness

```text
GET  /api/fitness/profile
POST /api/fitness/profile
GET  /api/fitness/sessions
POST /api/fitness/sessions
GET  /api/fitness/stats?scope=latest
GET  /api/fitness/stats?scope=cumulative
GET  /api/fitness/game
```

### Music and Dashboard Lifecycle

```text
GET  /api/music/status
POST /api/music/play
POST /api/music/stop
POST /api/music/refresh
POST /api/dashboard/closed
POST /api/dashboard/open
```

## Quick Start: Backend

```bash
# From the repository root:
cd backend
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
playwright install chromium      # one-time, required for automated Spotify playback
# Optional, only when using the Vision Module:
# pip install -r requirements-vision.txt
python main.py
```

The backend runs on the following local host URL with port 8000.

```text
http://localhost:8000
```

## Quick Start: Dashboard

```bash
cd dashboard
npm install
npm run dev
```

The dashboard runs on the following local host URL with port 5173.

```text
http://localhost:5173
```

The default login accounts are as follows.

```text
mackwongyy@gmail.com / 12345678
jonathansiew@hotmail.com / 87654321
```

## Optional: ASR Dependencies

Install these ASR dependencies on the machine running the ROS transcriber node.

```bash
cd backend
pip install -r requirements-asr.txt
```

Alternatively, you may install these ASR dependencies from the ROS language package, as follows.

```bash
pip install -r src/language_pkg/requirements-asr.txt
```

The recommended ASR settings are as follows.

```bash
export JUNO_ASR_MODEL_ID=openai/whisper-tiny
export JUNO_ASR_TASK=translate
export JUNO_ASR_SAMPLE_RATE=16000
export JUNO_ASR_WINDOW_SECONDS=3.0
export JUNO_ASR_MIN_RMS=0.03
```

## Optional: Vision Dependencies

```bash
cd backend
pip install -r requirements-vision.txt
```

The recommended vision settings are as follows.

```bash
export JUNO_VISION_BACKEND=face_expression
export JUNO_VISION_MODEL_ID=mo-thecreator/vit-Facial-Expression-Recognition
export JUNO_VISION_EMOTION_MODE_DEFAULT=juno
export JUNO_VISION_DEVICE=auto
export JUNO_VISION_MIN_CONFIDENCE=0.30
export JUNO_VISION_NEUTRAL_UNCERTAIN_CONFIDENCE=0.45
export JUNO_VISION_FAST_SWITCH_CONFIDENCE=0.52
export JUNO_VISION_REQUIRE_FACE=false
```

For lightweight demos without the Hugging Face vision model, the backend connecting to the Juno vision module can be mocked, as follows.

```bash
export JUNO_VISION_BACKEND=mock
```

## ROS Robot Mode

The ROS workspace is rooted at this repository. Source ROS and build through catkin according to the ROS Noetic setup.

The typical robot launch flow is as follows.

```bash
# Terminal 1
roscore

# Terminal 2
roslaunch juno_bringup juno_robot.launch

# Terminal 3
cd backend
python main.py

# Terminal 4
cd dashboard
npm run dev
```

The important ROS topics are as follows.

| Topic | Direction | Purpose |
|---|---|---|
| `/camera/image_raw` | camera node → backend | Jupiter camera frames |
| `/microphone/audio` | microphone node → transcriber | audio stream |
| `/speech/transcript` | transcriber → backend | recognised user speech |
| `/juno/tts` | backend → TTS node | robot speech output |
| `/juno/tts_stop` | backend → TTS node | stop current speech |
| `/juno/tts_done` | TTS node → backend | speech completion signal |
| `/juno/led_state` | backend → robot bridge | optional LED state |

Camera Defaults:

```text
Jupiter RGB camera: /dev/video2
Reserved metadata device: /dev/video1
ROS image topic: /camera/image_raw
```

## Environment Configuration

Copy or reference `backend/.env.example` for the full list. Important values include the following settings.

```env
JUNO_DASHBOARD_URL=http://localhost:5173
JUNO_DATABASE_PATH=juno_assist.db
JUNO_DATABASE_REFRESH_ON_START=true
JUNO_USE_ROS_ROBOT=false
JUNO_CAMERA_TOPIC=/camera/image_raw
JUNO_CAMERA_ENABLED_DEFAULT=false
JUNO_VISION_MODEL_ENABLED_DEFAULT=false
JUNO_VISION_EMOTION_MODE_DEFAULT=juno
JUNO_MUSIC_PROVIDER=spotify
JUNO_POWERDOWN_CLEANUP_ENABLED=true
```

## Testing and Validation

The backend test suite can be run as follows.

```bash
cd backend
PYTHONPATH=. pytest -q
```

The frontend production build can be run as follows.

```bash
cd dashboard
npm install
npm run build
```

The current validation target for the code repository is as follows.

```text
Backend tests: 80 passed
Frontend build: Vite production build passed
```

## Known Limitations and Safety Notes

- Facial emotion recognition is an estimate, not a diagnosis or proof of the user’s internal state.
- The system prioritises explicit user speech over facial-expression inference.
- `tired` is not a direct Ekman facial class and is mainly inferred through speech content.
- `motions.games` may block iframe embedding or attempt to navigate the parent page, so the dashboard opens it in a separate popup/tab rather than embedding it directly.
- The default accounts and passwords are for prototype demonstration only and should be changed before any real deployment.
- The database refresh-on-start behaviour is useful for demos, but should be disabled if persistent production data is required.
- Power-off cleanup is pattern-based and intentionally excludes ROS Core and the backend so the robot can be powered on again in the same run.
- Hardware limitations from the robot impede more dynamic implementation of features in the speech and vision modules.

## Current Status

JUNO Assist currently integrates the following features within its system architecture.

- ROS-based perception and language packages,
- FastAPI backend and WebSocket status stream,
- React dashboard with authentication,
- user-scoped SQLite persistence,
- flexible speech-command handling,
- camera and dual-mode emotion display,
- study timer, schedule, reminders, music, destressing game, and power lifecycle management.

This README documents the current combined system state after the authentication, database refresh, power lifecycle, dual emotion mode, date/time panel, destressing game, and dashboard/robot interaction updates.


### Backend startup note

If your terminal prompt already ends with `backend %`, do not run `cd backend` again. Run the backend commands from the current folder. The base backend now starts with `requirements.txt` only; install `requirements-vision.txt` only when you want to use the camera Vision Module.
