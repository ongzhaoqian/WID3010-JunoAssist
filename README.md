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

# JUNO Assist: Personal Daily Assistant Robot

JUNO Assist is a prototype for a **Jupiter Robot-based personal daily assistant**. It supports wake-word activation, voice-confirmed start-up, a web dashboard, facial-emotion monitoring, schedule reminders, study timers, break recommendations, and simple natural-language commands.

The system is designed to run in two modes:

1. **Mock / Laptop Mode**: Runs without the Jupiter Robot using simulated robot hardware, suitable for development and demonstration.
2. **Jupiter Integration Mode**: Replaces the mock adapters with Jupiter Robot camera, microphone, and speaker APIs.

## Documentation Guide

| File | Purpose | Read this when you need to... |
|---|---|---|
| `docs/product_requirements.md` | System requirements and technical design | Understand what JUNO Assist is supposed to do, feature scope, APIs, components, and design decisions. |
| `docs/ros_integration_guide.md` | ROS setup, runtime commands, robot integration, testing, and troubleshooting | Run the robot/demo terminals, configure `.venv` vs `.venv-vision`, debug ROS topics, ASR/TTS, camera, or vision. |
| `docs/project_manual_scaled_demo.md` | Demo plan, rubric mapping, team responsibilities, and submission checklist | Prepare the final presentation/report, assign work, collect evidence, and follow the course marking requirements. |

For normal robot setup, start with `docs/ros_integration_guide.md`.

## Assessment Mapping

This repository is organised around the WID3010 Autonomous Robots alternative assessment requirements:

| Question | Repository support |
|---|---|
| Q1 — robotics application, objectives, scope, AI techniques, experimental setup, testing scenarios | Project overview, architecture, technology stack, and documentation in `docs/product_requirements.md` and `docs/final_submission_checklist.md` |
| Q2 — ROS workspace and catkin setup | `src/` catkin workspace with `perception_pkg`, `language_pkg`, `juno_bringup`, and `src/CMakeLists.txt` |
| Q3 — ROS application, packages, APIs, publishers/subscribers, and unit testing | ROS nodes, launch file, backend ROS bridge, GitHub software checks, and robot-side `rostopic` testing guide |
| Q4 — `rqt_graph` visualisation and node-topic explanation | RQT graph instructions in `docs/ros_integration_guide.md` and `docs/final_submission_checklist.md` |
| Q5 — manual on how to run/launch the robot application | Four-terminal launch guide in `docs/ros_integration_guide.md` |
| Q6 — max 5-minute robot demo video | Demo flow and recording checklist in `docs/final_submission_checklist.md` |

## Project Scenario

Students often face many assignments, tests, classes, and deadlines during the semester. JUNO Assist helps them stay organised by checking schedules, setting timers, recommending breaks, and adjusting its responses based on estimated visible emotional state.

## Main Features

- Wake command: `Hey, John`
- Voice confirmation before activation
- Web dashboard after activation
- Embedded dashboard camera window for the Jupiter webcam feed
- Facial emotion monitoring using a mockable vision module
- Rule-based intent detection for course-level feasibility
- Lightweight Whisper Tiny speech recognition for robot microphone input
- Calendar and reminder storage using SQLite
- Study timer and productivity recommendations, including minute-and-second input
- Emotion-aware Spotify dashboard music window
- Editable dashboard schedule items
- REST API and WebSocket updates using FastAPI
- React dashboard using Vite and Tailwind CSS
- Jupiter-ready hardware abstraction layer

## System Architecture

```text
User
│
├── Voice Input
│   ├── Wake Word Detection
│   ├── Confirmation Handler
│   ├── Transcript Normalisation
│   └── Intent Classifier
│
├── Vision Input
│   ├── Camera Adapter
│   ├── Face / Emotion Detector
│   └── Emotion Smoothing
│
├── JUNO Backend
│   ├── FastAPI REST API
│   ├── WebSocket Status Stream
│   ├── Calendar Service
│   ├── Reminder Service
│   ├── Study Timer Service
│   ├── Break Recommender
│   └── Response Generator
│
├── Jupiter Robot Interface
│   ├── Camera
│   ├── Microphone
│   ├── Speaker
│   └── Optional Motion / LED Feedback
│
└── React Web Dashboard
    ├── Robot Status
    ├── Current Emotion
    ├── Live Camera Window
    ├── Today's Schedule
    ├── Reminders
    ├── Study Timer
    ├── Emotion-Aware Music Window
    └── Command Panel
```

## Repository Structure

```text
WID3010-JunoAssist/
├── backend/       # FastAPI assistant logic, NLP, productivity, vision, robot interface
├── dashboard/     # React/Vite user dashboard
├── src/           # ROS catkin packages: perception_pkg, language_pkg, juno_bringup
├── docs/          # Requirements, ROS integration guide, manual/demo checklist, submission checklist
├── .github/       # Pull request template and GitHub Actions software checks
└── README.md
```

## Technology Stack

| Layer | Technology |
|---|---|
| Robot platform | Jupiter Robot mode |
| Backend | Python, FastAPI, Uvicorn |
| Real-time updates | WebSocket |
| Storage | SQLite |
| Vision | ROS `/camera/image_raw` frames streamed to the dashboard through FastAPI MJPEG; OpenCV-ready emotion module |
| Speech | ROS microphone input transcribed by Hugging Face `openai/whisper-tiny`; manual transcript fallback retained |
| NLP | Rule-based intent classifier with deterministic backend responses; optional text LLM boundary disabled by default |
| Dashboard | React, Vite, Tailwind CSS |
| Music playback | Spotify dashboard embeds with configurable emotion-to-playlist URLs |
| Testing | Pytest |

## Activation Flow

```text
1. Robot stays in Idle Mode.
2. User says: "Hey, John".
3. JUNO replies:
   "Are you sure you would like to power Juno on? Answer yes if you do, else ignore."
4. User says: "Yes".
5. JUNO enters Active Mode.
6. Dashboard opens.
7. Facial monitoring and command handling begin.
```

## Quick Start: Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
python main.py
```

### Optional: Enable Whisper Tiny ASR for the Robot

The robot-facing speech path now uses Hugging Face `openai/whisper-tiny` for automatic speech recognition, while the backend continues to use deterministic intent classification and response logic.

Install the optional ASR dependencies on the machine that runs the ROS transcriber node:

```bash
cd backend
pip install -r requirements-asr.txt
```

For ROS usage, the language package also includes the same dependency list:

```bash
pip install -r src/language_pkg/requirements-asr.txt
```

Recommended ASR environment settings:

```bash
export JUNO_ASR_MODEL_ID=openai/whisper-tiny
export JUNO_ASR_TASK=translate      # translate non-English speech to English
export JUNO_ASR_SAMPLE_RATE=16000
export JUNO_MIC_DEVICE_NAME=0x46d:0x825  # preferred: substring match on USB device name
export JUNO_MIC_DEVICE_INDEX=7            # fallback if JUNO_MIC_DEVICE_NAME is unset
export JUNO_ASR_WINDOW_SECONDS=3.0
export JUNO_ASR_MIN_RMS=0.03
export JUNO_ASR_DEVICE=-1                 # CPU; use 0 for first CUDA GPU if available
export JUNO_ASR_TTS_RESUME_DELAY=0.5
export JUNO_TTS_PUBLISHER_WAIT_SECONDS=2.0
export JUNO_TTS_PUBLISH_RETRIES=1
```

Check the active AI/ASR configuration at:

```text
http://localhost:8000/api/ai/status
```

To test speech output independently from speech-to-text and intent classification, start ROS and the backend in ROS mode, then run either command:

```bash
rosrun language_pkg tts_test_publisher.py "Hello, I am JUNO and my speech output is working."
# or, through the backend publisher:
curl -X POST http://localhost:8000/api/robot/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, I am JUNO and my backend speech path is working."}'
```

If `/speech/transcript` works but the robot is silent, check that `/juno/tts` receives text and that `juno_tts_node` is running:

```bash
rostopic echo /juno/tts
rostopic echo /juno/tts_done
rosnode list | grep tts
```

The backend no longer requires the Malaysian Llama base model or LoRA adapter for the robot demo. Manual or external transcript fallback remains available through `/speech/raw_transcript`, and the backend still consumes `/speech/transcript`.

The backend will run at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

## Dashboard Camera Window

The Jupiter webcam feed is shown inside the dashboard instead of a separate ROS OpenCV pop-up window. The path is:

```text
camera_node.py → /camera/image_raw → FastAPI ROS bridge → /api/vision/camera/stream → React CameraPanel
```

On first dashboard load, the camera is **off by default**. To gain consent from the user for live image use, the camera window remains visible as a placeholder with a **Switch On Camera** button, so the operator decides when the live `/dev/video2` feed should appear. The **Vision Module** toggle is separate: switch it on only when you want to load/run the emotion-recognition model. If the camera is on but the Vision Module is off, the panel works as a normal camera monitor only.

Useful endpoints:

```text
GET  http://localhost:8000/api/vision/status
POST http://localhost:8000/api/vision/camera/start
POST http://localhost:8000/api/vision/camera/stop
POST http://localhost:8000/api/vision/camera/refresh
POST http://localhost:8000/api/vision/model/start
POST http://localhost:8000/api/vision/model/stop
```

For normal operation, do not launch `camera_listener_node.py`; it no longer opens a pop-up by default. For debugging only:

```bash
rosrun perception_pkg camera_listener_node.py _display_window:=true
```


## Dashboard Music, Schedule, and Study Timer Updates

### Emotion-aware music window

The dashboard now includes an **Emotion-Aware Music** card. When the user asks JUNO to play music, the backend checks the latest `current_emotion` value and selects a matching Spotify playlist for the dashboard player. If the Vision Module is off or the emotion state is unknown, JUNO falls back to a neutral deep-focus playlist.

The current implementation uses Spotify embed URLs instead of storing Spotify API secrets in the repository. This is safer for a student demo and still allows the dashboard to display a Spotify player. The default emotion mapping can be changed in `backend/.env.example` or a local `.env` file:

```text
JUNO_SPOTIFY_HAPPY_URL=...
JUNO_SPOTIFY_NEUTRAL_URL=...
JUNO_SPOTIFY_TIRED_URL=...
JUNO_SPOTIFY_STRESSED_URL=...
JUNO_SPOTIFY_FRUSTRATED_URL=...
JUNO_SPOTIFY_UNKNOWN_URL=...
```

Useful endpoints:

```text
GET  http://localhost:8000/api/music/status
POST http://localhost:8000/api/music/play
POST http://localhost:8000/api/music/stop
POST http://localhost:8000/api/music/refresh
```

### Editable schedule panel

The **Upcoming Schedule** panel now lets the user add and remove schedule items from the dashboard. Added items are stored in the same SQLite `schedule_items` table used by the schedule and deadline response logic.

Useful endpoints:

```text
GET    http://localhost:8000/api/schedule/today
POST   http://localhost:8000/api/schedule
DELETE http://localhost:8000/api/schedule/{item_id}
```

### Voice-driven study timer flow

When the user says a generic timer request, such as `start study timer`, JUNO now asks:

```text
How long do you want to have the study timer for? Answer in minutes and seconds.
```

The next user response can be a duration such as `25 minutes`, `twenty five minutes`, `1 minute 30 seconds`, `one minute thirty seconds`, `90 seconds`, `half an hour`, `one and a half hours`, `1h 30m`, or `2:30`. The dashboard timer also has separate minute and second fields.

If the user does not want to continue setting the timer, they can say `cancel`, `not now`, `no timer`, `skip`, or `never mind`. If JUNO receives repeated unclear duration answers, it exits timer setup instead of asking forever.

Useful endpoint:

```text
POST http://localhost:8000/api/timer/start
Body: { "minutes": 1, "seconds": 30 }
```


### Speech-prioritised emotion handling

The dashboard Vision Module still estimates emotion from the camera, but speech now has priority when the user explicitly states how they feel. For example, if the camera reads the user as neutral but the transcript says `I am stressed`, JUNO records the current emotion as `stressed` with source `speech` and temporarily prevents visual inference from overriding it. The override window is configured with `JUNO_SPEECH_EMOTION_OVERRIDE_SECONDS`.

This keeps break recommendations and emotion-aware music aligned with the user's stated feelings rather than relying only on visible facial expression.

## Quick Start: Dashboard

Open a second terminal:

```bash
cd dashboard
npm install
npm run dev
```

The dashboard will run at:

```text
http://localhost:5173
```

## Dashboard Visuals and Natural Response Layer

The dashboard is styled with a gradient background, glass-morphism cards, soft neon accents, and a more polished operator layout inspired by the UMHackathon-style visual direction (https://umhackathon.org), which is implemented mainly in `dashboard/src/index.css`, `dashboard/src/App.jsx`, and shared card/form components.

Robot responses are now centralised through `backend/src/nlp/phrase_bank.py`. Instead of hard-coding a single sentence in every invocation path, intent handlers now request phrasing from the phrase bank, which gives JUNO more natural response variation while keeping the behaviour deterministic enough for a course prototype.

## Voice Schedule Capture

JUNO can now add schedule items from a transcribed command that includes `date`, `time`, `purpose`, and `priority`.

Example voice/text command:

```text
add schedule date 2026-05-20 time 15:30 purpose deep learning revision priority high
```

The backend stores the original ISO-style date for consistency, but also returns a display date for the dashboard and speech response:

```text
2026-05-20 → 20 May, 2026
```

The relevant implementation is in:

```text
backend/src/nlp/intent_classifier.py      # ADD_SCHEDULE intent + structured field parsing
backend/src/calendar_module/calendar_service.py  # formatted_date generation
backend/src/api/app.py                    # voice command handling and schedule creation
dashboard/src/components/SchedulePanel.jsx # displays formatted_date when available
```


## Troubleshooting Guide

Recommended Python version for the backend is **Python 3.10+**. This aligns with ROS Noetic compatibility and the documented project requirements. If dependency installation fails, first check the Python version:

```bash
python --version
```

Then recreate the virtual environment and reinstall dependencies:

```bash
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If the lab machine has an older Python version, install Python through the operating system package manager, `pyenv`, or your lab's approved setup method. Building Python from source should only be used as a last resort on machines where you have permission to do so.

## Demo Steps

1. Start the backend.
2. Start the dashboard.
3. In the dashboard command box, type:

```text
Hey, John
```

4. Then type:

```text
Yes
```

5. JUNO becomes active.
6. Try commands such as:

```text
What do I have today?
Set a 25 minute timer.
What should I do now?
Play relaxing music.
Add reminder revise robotics at 8 pm.
Juno, go to sleep.
```

## Notes for Jupiter Robot Integration

The current implementation uses `MockJupiterInterface`. To connect to the actual Jupiter Robot, update:

```text
backend/src/robot/jupiter_interface.py
```

Replace the methods in `MockJupiterInterface` with Jupiter-specific SDK, ROS topic, or hardware API calls.

The expected interface methods are:

```python
speak(text: str) -> None
listen() -> str
get_camera_frame()
open_dashboard(url: str) -> None
set_led_state(state: str) -> None
```

## Scope Evaluation

This project is intentionally scoped to be achievable:

- No complex autonomous navigation is required.
- Robot motion is optional.
- Emotion detection can be demonstrated through a mock model first.
- Speech can be tested using dashboard text commands.
- Calendar data can use SQLite or sample JSON before API integration.
- The system demonstrates robotics integration through perception, interaction, decision-making, and user-facing feedback.

## Ethical Note

The facial emotion module estimates visible expressions only. It must not be presented as a medical or psychological diagnosis. JUNO should use careful language, such as:

> "You seem a little tired. Would you like to take a short break?"

not:

> "You are definitely stressed."
