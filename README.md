# WID3010-JunoAssist

## WID3010: Autonomous Robots
Universiti Malaya, Academic Year 2025/2026, Semester 2

Group 5
- Wong Yoong Yee
- Jonathan Siew Zunxian
- Ong Zhao Qian
- Vanness Liu Chuan Wei
- Anas Abdulrahman Mohamad

# JUNO Assist: Personal Daily Assistant Robot

JUNO Assist is a prototype for a **Jupiter Robot-based personal daily assistant**. It supports wake-word activation, voice-confirmed start-up, a web dashboard, facial-emotion monitoring, schedule reminders, study timers, break recommendations, and simple natural-language commands.

The system is designed to run in two modes:

1. **Mock / Laptop Mode** — runs without the Jupiter Robot using simulated robot hardware, suitable for development and demonstration.
2. **Jupiter Integration Mode** — replaces the mock adapters with Jupiter Robot camera, microphone, speaker, and optional movement APIs.

## Project Scenario

Students often face many assignments, tests, classes, and deadlines during the semester. JUNO Assist helps them stay organised by checking schedules, setting timers, recommending breaks, and adjusting its responses based on estimated visible emotional state.

## Main Features

- Wake command: `Hey, Juno`
- Voice confirmation before activation
- Web dashboard after activation
- Facial emotion monitoring using a mockable vision module
- Rule-based intent detection for course-level feasibility
- Calendar and reminder storage using SQLite
- Study timer and productivity recommendations
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
│   ├── Speech-to-Text
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
    ├── Today's Schedule
    ├── Reminders
    ├── Study Timer
    └── Command Panel
```

## Repository Structure

```text
juno-assist-jupiter/
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── data/
│   │   └── sample_schedule.json
│   ├── src/
│   │   ├── activation/
│   │   ├── api/
│   │   ├── calendar_module/
│   │   ├── core/
│   │   ├── nlp/
│   │   ├── productivity/
│   │   ├── robot/
│   │   ├── speech/
│   │   └── vision/
│   └── tests/
│
├── dashboard/
│   ├── package.json
│   ├── index.html
│   └── src/
│
└── docs/
    ├── implementation_plan.md
    └── jupiter_integration_notes.md
```

## Recommended Technology Stack

| Layer | Technology |
|---|---|
| Robot platform | Jupiter Robot / laptop mock mode |
| Backend | Python, FastAPI, Uvicorn |
| Real-time updates | WebSocket |
| Storage | SQLite |
| Vision | OpenCV-ready module, mock emotion detector by default |
| Speech | Mock text input by default, replaceable with Whisper / Vosk / Jupiter speech |
| NLP | Rule-based intent classifier |
| Dashboard | React, Vite, Tailwind CSS |
| Testing | Pytest |

## Activation Flow

```text
1. Robot stays in Idle Mode.
2. User says: "Hey, Juno".
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

The backend will run at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

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

## Troubleshooting Guide

If the backend could not be run, ensure the Python version on the local machine is updated to at least 3.12.0.

```bash
cd /tmp
wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz
tar xvf Python-3.12.0.tgz
cd Python-3.12.0

./configure --enable-optimizations --prefix=/usr/local
make -j $(nproc)
sudo make altinstall
```

Check the current Python version and ensure it is at least 3.12.0.

```bash
/usr/local/bin/python3.12 --version
```

Remove the old virtual environment and create a new venv with Python 3.12. 

```bash
rm -rf .venv
python3.12 -m venv .venv
```

Activate the newly created virtual environment and upgrade the pip version to the latest one.

```bash
source .venv/bin/activate
pip install --upgrade pip
```

Install dependencies and double-check the Python version is at least 3.12.0.

```bash
pip install -r requirements.txt
python --version
```

## Demo Steps

1. Start the backend.
2. Start the dashboard.
3. In the dashboard command box, type:

```text
Hey, Juno
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

## Feasibility for Undergraduate Robotics Course

This project is intentionally scoped to be achievable:

- No complex autonomous navigation is required.
- Robot motion is optional.
- Emotion detection can be demonstrated through a mock model first.
- Speech can be tested using dashboard text commands.
- Calendar data can use SQLite or sample JSON before API integration.
- The system demonstrates robotics integration through perception, interaction, decision-making, and user-facing feedback.

## Ethical Note

The facial emotion module estimates visible expressions only. It must not be presented as a medical or psychological diagnosis. JUNO should use careful language such as:

> "You seem a little tired. Would you like to take a short break?"

not:

> "You are definitely stressed."
