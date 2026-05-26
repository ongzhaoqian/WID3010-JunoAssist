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

JUNO Assist is a prototype for a **Jupiter Robot-based personal daily assistant**. It supports wake-word activation, voice-confirmed start-up, a web dashboard, facial-emotion monitoring, live schedule and reminder management, voice-driven study timers with flexible duration parsing, timer-completion bell alerts, break recommendations, and simple natural-language commands.

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

- Wake command: `Hey, Juno` or `Hey, John`
- Voice confirmation before activation
- Web dashboard after activation
- Embedded dashboard camera window for the Jupiter webcam feed
- Switchable JUNO/Ekman facial emotion analysis using a lightweight Hugging Face image classifier (`mo-thecreator/vit-Facial-Expression-Recognition`), with mock fallback for lightweight demos
- Rule-based intent detection for course-level feasibility
- Lightweight Whisper Tiny speech recognition for robot microphone input
- SQLite-backed schedule and reminder storage
- Editable dashboard schedule items with live speech retrieval of newly added items
- Editable dashboard reminders using the same main fields as schedule items: `title`, `date`, `time`, `type`, and `priority`
- Voice commands for checking schedules, adding schedules, checking reminders, and adding reminders
- Speech-tolerant schedule/reminder date and time parsing, including `25 May`, `25/05/2026`, `tomorrow`, `next Monday`, `nine pm`, `nine thirty`, `half past nine`, and `quarter to six`
- Study timer with minute-and-second input, flexible speech duration parsing, cancellation support, and bell sound on completion
- Emotion-aware Spotify dashboard music window with voice-stop support
- 6-7 fitness game popup with score saving, one-off/cumulative statistics, and calorie estimates based on user-entered height and weight
- Immediate `stop` command to interrupt JUNO speech and stop dashboard music
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
│   ├── Ekman-7 Facial Emotion Classifier
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
| Vision | ROS `/camera/image_raw` frames streamed to the dashboard through FastAPI MJPEG; Hugging Face `mo-thecreator/vit-Facial-Expression-Recognition` as the core facial-expression model, with switchable JUNO/Ekman display modes and mock fallback |
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

### Optional: Enable Switchable JUNO/Ekman Vision Module

The core vision model now uses `mo-thecreator/vit-Facial-Expression-Recognition` by default through the `face_expression` backend. The model runs once and produces a canonical Ekman-style probability vector internally. The dashboard can then switch between two display modes during the same run without reloading the model.

Ekman mode shows user-facing display labels while preserving raw Ekman values in the Jupiter Camera View details:

```text
angry, disgusted, scared, happy, sad, surprised, neutral
```

The raw Ekman values remain available separately as:

```text
anger, disgust, fear, happiness, sadness, surprise, neutral
```

JUNO mode keeps the original robot-facing labels:

```text
happy, sad, tired, frustrated, stressed, neutral
```

`unknown` is still used when the frame is missing, too dark, has weak evidence, or the classifier is below the configured confidence threshold. Low-confidence neutral predictions are treated as `unknown`, which avoids the previous issue where the dashboard showed `neutral` at about 40% confidence for most frames. The `tired` label is not forced from facial expression alone; it is used when speech content explicitly says the user is tired, exhausted, or drained.

Install the optional vision dependencies before switching on the dashboard Vision Module:

```bash
cd backend
pip install -r requirements-vision.txt
```

Recommended settings:

```bash
export JUNO_VISION_BACKEND=face_expression
export JUNO_VISION_MODEL_ID=mo-thecreator/vit-Facial-Expression-Recognition
export JUNO_VISION_EMOTION_MODE_DEFAULT=juno   # juno or ekman
export JUNO_VISION_DEVICE=auto          # CUDA → Apple MPS → CPU
export JUNO_VISION_MIN_CONFIDENCE=0.30
export JUNO_VISION_NEUTRAL_UNCERTAIN_CONFIDENCE=0.45
export JUNO_VISION_FAST_SWITCH_CONFIDENCE=0.52
export JUNO_VISION_REQUIRE_FACE=false   # false keeps a centre-crop fallback for demo conditions
```

Experimental SmolVLM mode is still available, but it is no longer the default:

```bash
export JUNO_VISION_BACKEND=smolvlm
export JUNO_VISION_MODEL_ID=HuggingFaceTB/SmolVLM-256M-Instruct
```

Use this lightweight fallback when the demo machine should not load any Hugging Face vision model:

```bash
export JUNO_VISION_BACKEND=mock
```

#### Vision emotion troubleshooting

- If no face is detected, JUNO either uses a centre-crop fallback or reports `unknown`, depending on `JUNO_VISION_REQUIRE_FACE`.
- Low-confidence neutral predictions are shown as `unknown` unless the classifier gives sufficiently clear neutral evidence.
- Clear non-neutral states such as `anger`, `fear`, `sadness`, `happiness`, `disgust`, or `surprise` can update the dashboard immediately.
- The dashboard now displays the selected emotion mode, display label, raw Ekman label, JUNO label, confidence, source, classifier description, and model error message when available.
- Explicit spoken emotion still has priority. For example, if the transcript says `I am stressed`, speech emotion is mapped to Ekman `fear` and remains trusted over the webcam estimate for the configured override window.


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
export JUNO_TTS_TOPIC=/juno/tts
export JUNO_TTS_STOP_TOPIC=/juno/tts_stop
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
rostopic echo /juno/tts_stop
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

On first dashboard load, the camera is **off by default**. To gain consent from the user for live image use, the camera window remains visible as a placeholder with a **Switch On Camera** button, so the operator decides when the live `/dev/video2` feed should appear. The **Vision Module** toggle is separate: switch it on only when you want to load/run the facial-emotion model. The **JUNO/Ekman mode** control changes the displayed emotion vocabulary at any time without reloading the model. If the camera is on but the Vision Module is off, the panel works as a normal camera monitor only.

Useful endpoints:

```text
GET  http://localhost:8000/api/vision/status
POST http://localhost:8000/api/vision/camera/start
POST http://localhost:8000/api/vision/camera/stop
POST http://localhost:8000/api/vision/camera/refresh
POST http://localhost:8000/api/vision/model/start
POST http://localhost:8000/api/vision/model/stop
POST http://localhost:8000/api/vision/analyse       # one-shot analysis of the latest camera frame
```

`/api/vision/status` now reports the active vision backend, model ID, whether the model has loaded, the latest visual-emotion confidence, and the latest classifier description/error if available.

For normal operation, do not launch `camera_listener_node.py`; it no longer opens a pop-up by default. For debugging only:

```bash
rosrun perception_pkg camera_listener_node.py _display_window:=true
```



### Current Date, Time, and Timezone Window

The dashboard now includes a **Current System Date & Time** card above Robot Status, Study Timer, and Most Recent Response from JUNO. It shows a live clock and date based on the device system time, formatted using the selected location or timezone.

The user can choose from common location presets such as Kuala Lumpur, Singapore, Tokyo, London, New York, San Francisco, Sydney, and UTC, or select an IANA timezone directly. The selected timezone and location label are saved in browser local storage so the dashboard remembers the user's choice after refresh.

Implementation file:

```text
dashboard/src/components/DateTimePanel.jsx
```

## Dashboard Music, Schedule, Reminder, and Study Timer Updates

### Emotion-aware music window

The dashboard now includes an **Emotion-Aware Music** card. When the user asks JUNO to play music, the backend checks the latest displayed/current emotion value and selects a matching Spotify playlist for the dashboard player. If the Vision Module is off or the emotion state is unknown, JUNO falls back to a neutral deep-focus playlist.

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
POST http://localhost:8000/api/robot/stop
```

If the user says `stop`, `stop speaking`, `stop talking`, `stop music`, `pause music`, `be quiet`, or `silence`, the backend now sends an interrupt request to the ROS TTS node through `/juno/tts_stop` and stops the dashboard music state. The command does not speak another acknowledgement, so it can be used while JUNO is already speaking.

### Editable schedule panel and live schedule retrieval

The **Upcoming Schedule** panel lets the user add and remove schedule items from the dashboard. Added items are stored in the SQLite `schedule_items` table and are read directly by the schedule and deadline response logic. This means a schedule item added on the dashboard can be retrieved later through speech commands such as:

```text
What do I have today?
Show my schedule.
List my meetings.
```

Schedule items use the following fields:

| Field | Purpose |
|---|---|
| `title` | Main schedule item name, such as `Deep Learning revision` |
| `date` | Optional stored ISO date, such as `2026-05-20`. Voice input may also say `25 May`, `25/05/2026`, `tomorrow`, `day after tomorrow`, or `next Monday`. |
| `time` | Optional stored 24-hour time, such as `15:30`. Voice input may also say `nine pm`, `nine thirty`, `half past nine`, `quarter to six`, `noon`, `midnight`, `morning`, `afternoon`, or `evening`. |
| `type` | Category, such as `class`, `meeting`, `study`, `assignment`, `test`, or `quiz` |
| `priority` | Priority label, such as `low`, `medium`, `high`, or `urgent` |

Useful endpoints:

```text
GET    http://localhost:8000/api/schedule/today
POST   http://localhost:8000/api/schedule
DELETE http://localhost:8000/api/schedule/{item_id}
```

Example schedule body:

```json
{
  "title": "Deep Learning revision",
  "date": "2026-05-20",
  "time": "15:30",
  "type": "study",
  "priority": "high"
}
```

### Editable reminder panel and live reminder retrieval

The **Reminders** panel now uses the same main columns as schedule items: `title`, `date`, `time`, `type`, and `priority`. Reminders also store a `completed` flag internally so completed reminders can be filtered later. Older `due_date` and `due_time` values are still accepted and are automatically mapped to `date` and `time` for backwards compatibility.

Reminder records added through the dashboard are stored in the SQLite `reminders` table and are read directly when the user asks about reminders through speech. Supported reminder-checking commands include:

```text
What are my reminders?
List my reminders.
Do I have any reminders?
```

Useful endpoints:

```text
GET    http://localhost:8000/api/reminders
POST   http://localhost:8000/api/reminders
DELETE http://localhost:8000/api/reminders/{item_id}
```

Example reminder body:

```json
{
  "title": "Submit robotics report",
  "date": "2026-05-22",
  "time": "21:00",
  "type": "reminder",
  "priority": "high"
}
```

### Voice-driven study timer flow

When the user says a generic timer request, such as `start study timer`, JUNO now asks:

```text
How long do you want to have the study timer for? Answer in minutes and seconds.
```

The next user response can be a flexible duration such as:

```text
25 minutes
start twenty five minutes
one minute thirty seconds
one minute thirty
1 30
2:30
90 seconds
half an hour
quarter of an hour
one and a half hours
1h 30m
```

The robot no longer requires the user to repeat the word `timer` after it has already asked for the duration. If the user does not want to continue setting the timer, they can say `cancel`, `not now`, `no timer`, `skip`, `never mind`, or another active command such as `play music`. If JUNO receives repeated unclear duration answers, it exits timer setup instead of asking forever.

When the countdown reaches zero seconds, the backend emits a one-time timer-completion state update. The dashboard listens for `timer_completed_counter` changes through the WebSocket status stream and plays a short bell sound using the browser Web Audio API. The backend also updates the robot response, speaks a completion message, and sets the LED state to `timer_complete` when available.

Useful timer endpoints:

```text
POST http://localhost:8000/api/timer/start
Body: { "minutes": 1, "seconds": 30 }

POST http://localhost:8000/api/timer/pause
POST http://localhost:8000/api/timer/resume
POST http://localhost:8000/api/timer/stop
```

The dashboard Study Timer card now includes explicit **Pause Timer** and **Stop Timer** buttons. While the countdown is running, JUNO also accepts fuzzy spoken timer-control commands such as `pause timer`, `resume timer`, `stop timer`, `end the countdown`, `cancel the focus session`, or a short bare `stop` command. Speech-only commands such as `stop speaking` still interrupt speech/audio without deleting the timer.


### Speech-prioritised emotion handling

The dashboard Vision Module still estimates emotion from the camera, but speech now has priority when the user explicitly states how they feel. For example, if the camera reads the user as neutral but the transcript says `I am stressed`, JUNO records the current emotion as Ekman `fear` with source `speech` and temporarily prevents visual inference from overriding it. The override window is configured with `JUNO_SPEECH_EMOTION_OVERRIDE_SECONDS`.

This keeps break recommendations and emotion-aware music aligned with the user's stated feelings rather than relying only on visible facial expression.


## Dashboard Power Lifecycle

When JUNO powers on after confirmation, the backend now calls the dashboard lifecycle manager instead of blindly opening another browser tab. It first tries to focus an existing dashboard window using `wmctrl`; only if no matching window is found does it open `JUNO_DASHBOARD_URL`.

When JUNO powers off or enters sleep mode, the backend:

1. switches the robot state back to `idle`,
2. disables the camera and Vision Module,
3. sends the dashboard a `dashboard_should_close=true` state flag,
4. tries to close the browser window using `wmctrl`, and
5. runs best-effort process cleanup for configured JUNO runtime processes while excluding `roscore`, `rosmaster`, `rosout`, and the current backend process.

The dashboard also attempts `window.close()` when it receives the close flag. If the browser blocks automatic closing, it shows a powered-off overlay and the same page is reused when JUNO powers on again.

Useful settings:

```text
JUNO_DASHBOARD_REUSE_EXISTING=true
JUNO_DASHBOARD_CLOSE_ON_SLEEP=true
JUNO_POWERDOWN_CLEANUP_ENABLED=true
JUNO_POWERDOWN_CLEANUP_DELAY_SECONDS=2.0
JUNO_POWERDOWN_CLEANUP_PATTERNS=npm\s+run\s+dev|vite|roslaunch\s+juno_bringup|camera_node\.py|microphone_node\.py|tts_node\.py|transcriber\.py
JUNO_POWERDOWN_CLEANUP_EXCLUDE_PATTERNS=roscore|rosmaster|rosout|backend/main\.py|uvicorn.*backend|pytest
```

Useful endpoints:

```text
POST /api/robot/sleep
POST /api/dashboard/closed
POST /api/dashboard/open
```

## Fitness Game Dashboard Feature

The Quick Actions card includes a **Play Fitness Game** button. It opens the 67 Speed game page in an embedded game window with a popup fallback. After one round, the dashboard can save the user's 6-7 count and show it in the **Fitness Game Statistics** window.

Because `https://67speed.com/` is a third-party page, automatic score extraction is implemented as a best-effort browser `postMessage` listener. If the external game does not expose its score to the parent page, the user can enter the final 6-7 count manually after the round. This avoids fragile cross-origin scraping and keeps the feature reliable during demos.

Fitness APIs:

```text
GET  /api/fitness/profile
POST /api/fitness/profile        # { "height_m": 1.70, "weight_kg": 60 }
GET  /api/fitness/sessions
POST /api/fitness/sessions       # { "score_67": 67, "duration_seconds": 60 }
GET  /api/fitness/stats?scope=latest
GET  /api/fitness/stats?scope=cumulative
GET  /api/fitness/game
```

Calories are estimates only, using the standard MET formula with a default MET value of 4.0 for a light fitness game movement estimate. The dashboard supports **One-off Stats** for the latest game and **Cumulative Stats** for all saved sessions.

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

## Voice Schedule and Reminder Capture

JUNO can add schedule items and reminders from transcribed commands that include fields such as `date`, `time`, `purpose` or `title`, and `priority`.

Example schedule commands:

```text
add schedule date 2026-05-20 time 15:30 purpose deep learning revision priority high
add schedule on 25 May at nine pm purpose project discussion priority high
add schedule next Monday at half past nine purpose consultation
add schedule tomorrow morning purpose study session
```

Example reminder commands:

```text
add reminder date 2026-05-22 time 21:00 title submit robotics report priority high
Remind me to submit the robotics report on twenty fifth of May at nine pm priority high.
Remind me tomorrow at nine thirty to submit the project report.
```

The backend stores the original ISO-style date for consistency, but also returns a display date for the dashboard and speech response:

```text
2026-05-20 → 20 May, 2026
```

The relevant implementation is in:

```text
backend/src/nlp/intent_classifier.py           # ADD_SCHEDULE, CHECK_SCHEDULE, ADD_REMINDER, CHECK_REMINDERS, STOP, speech-tolerant date/time parsing, and flexible timer parsing
backend/src/calendar_module/calendar_service.py # SQLite schema, reminder migration, formatted_date generation, schedule/reminder listing
backend/src/core/models.py                     # ScheduleItemRequest, ReminderRequest, TimerRequest, RobotStatus, STOP intent
backend/src/core/config.py                     # ROS TTS and TTS-stop topic settings
backend/src/core/state.py                      # timer duration state and one-time timer completion counter
backend/src/api/app.py                         # voice command handling, live schedule/reminder retrieval, timer completion loop, output stop route
backend/src/robot/ros_jupiter_interface.py     # publishes speech and speech-stop messages to ROS
src/language_pkg/scripts/tts_node.py           # subscribes to /juno/tts and /juno/tts_stop, interrupts pyttsx3/espeak speech
src/language_pkg/scripts/transcriber.py        # listens for a narrow stop override while TTS is muted
dashboard/src/components/SchedulePanel.jsx     # displays newly added schedule items
dashboard/src/components/ReminderPanel.jsx     # displays newly added reminders using schedule-like fields
dashboard/src/components/TimerPanel.jsx        # minute/second input and completion bell sound
```


## Implementation Notes for Recent Productivity Fixes

- Dashboard schedules and reminders are no longer treated as separate demo-only lists. Both are stored in SQLite and fetched live whenever the user asks through speech or the dashboard refreshes.
- Reminder migration is automatic. Existing reminder rows that used `due_date` and `due_time` are mapped into the newer `date` and `time` fields.
- `CHECK_REMINDERS` and `ADD_REMINDER` are separate intents so asking about reminders no longer accidentally behaves like adding a reminder.
- While JUNO is waiting for a timer duration, the next speech input is interpreted as a duration first. The user does not need to say `timer` repeatedly.
- The timer completion bell is generated in the dashboard with Web Audio API, so no external audio file is required.
- Schedule and reminder voice capture now accepts common Malaysian/UK-style date formats and spoken time formats, then normalises them to ISO date and 24-hour time for storage.
- `stop` is a narrow interruption intent: it stops current TTS output, clears queued robot speech, and stops dashboard music, while avoiding false positives such as `stop by the office`.


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
Add schedule date 2026-05-20 time 15:30 purpose deep learning revision priority high.
What are my reminders?
Add reminder date 2026-05-22 time 21:00 title submit robotics report priority high.
Set a 25 minute timer.
Start one minute thirty.
Cancel.
What should I do now?
Play relaxing music.
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
