# WID3010-JunoAssist

## WID3010: Autonomous Robots
Universiti Malaya, Academic Year 2025/2026, Semester 2

Group 5
- Wong Yoong Yee
- Jonathan Siew Zunxian
- Ong Zhao Qian
- Vanness Liu Chuen Wei
- Anas Abdurahman Mohammad

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
- Optional Malaysian Llama + LoRA input normalisation and response generation with standard British English output
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
    ├── Today's Schedule
    ├── Reminders
    ├── Study Timer
    └── Command Panel
```

## Repository Structure

```text
WID3010-JunoAssist/
├── backend/       # FastAPI assistant logic, NLP, productivity, vision, robot interface
├── dashboard/     # React/Vite user dashboard
├── src/           # ROS catkin packages: perception_pkg, language_pkg, juno_bringup
├── docs/          # Manuals, requirements, integration notes, task distribution
├── .github/       # Pull request template
└── README.md
```

## Recommended Technology Stack

| Layer | Technology |
|---|---|
| Robot platform | Jupiter Robot / laptop mock mode |
| Backend | Python, FastAPI, Uvicorn |
| Real-time updates | WebSocket |
| Storage | SQLite |
| Vision | OpenCV-ready module, mock emotion detector by default |
| Speech | ROS transcript input; upstream ASR/manual text source normalised through Malaysian Llama + LoRA |
| NLP | Rule-based intent classifier + optional Hugging Face Malaysian Llama base model with LoRA adapter |
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

### Optional: Enable Malaysian Llama + LoRA

The backend supports `mesolitica/Malaysian-Llama-3.2-3B-Instruct` with the LoRA adapter `mackwongyy/malaysian-feedback-lora-5k-data`. It is used for Malaysian-context input normalisation and open-ended replies while keeping robot actions behind deterministic backend logic.

Install the optional model dependencies:

```bash
cd backend
pip install -r requirements-llm.txt
```

Enable the model before starting the backend:

```bash
export JUNO_LLM_ENABLED=true
export JUNO_LLM_MODEL_ID=mesolitica/Malaysian-Llama-3.2-3B-Instruct
export JUNO_LLM_ADAPTER_ID=mackwongyy/malaysian-feedback-lora-5k-data
export JUNO_LLM_DEVICE_MAP=auto
export JUNO_LLM_TORCH_DTYPE=auto
python main.py
```

Check the active AI configuration at:

```text
http://localhost:8000/api/ai/status
```

The LLM is lazy-loaded. It normalises Malaysian-context utterances into standard British English before intent classification and answers open-ended prompts in British English. Robot-state actions such as wake, confirmation, sleep, timer, schedule, music, and reminders still use deterministic backend logic. See `docs/malaysian_llama_integration.md` for details.

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
