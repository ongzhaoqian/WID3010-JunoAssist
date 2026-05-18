# Juno Project Component Specifications

This document details the planned/final components of the Juno codebase, a Jupiter JUNO powered Personal Assistant Robot. On documentation-only branches, some implementation folders may not be present until the relevant integration branches are merged.

## 1. Backend (Python / FastAPI)
Located in `/backend`, this serves as the central brain of the system, handling business logic, data persistence, and orchestration.

### Core Components
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

### Testing
- **Backend Tests (`tests/`)**: Includes unit tests for `emotion_smoothing` and `intent_classifier` to ensure logic correctness.

---

## 2. Dashboard (React / Vite / Tailwind CSS)
Located in `/dashboard`, this provides a visual interface for the user to monitor Juno's status and manage their schedule.

### Key Features
- **Status Panel**: Displays Juno's current mode (Idle, Active, Confirmation) and real-time emotion detection results.
- **Schedule Panel**: Lists the user's classes and meetings for the day.
- **Reminder Panel**: Shows upcoming deadlines and custom reminders.
- **Timer Panel**: Provides a visual countdown and controls for study sessions.
- **Command Panel**: Allows manual text input for users who prefer typing over voice commands.
- **WebSocket Integration**: Listens to `/ws/status` for instantaneous updates from the backend.

---

## 3. Catkin Workspace (ROS Noetic / Python)
Located in `/src`, these packages handle low-level hardware interaction and sensor processing.

### Packages
- **`perception_pkg`**:
    - **Camera Node**: Captures and publishes video streams from the Jupiter robot's camera.
    - **Microphone Node**: Captures audio data for speech recognition.
- **`language_pkg`**:
    - **Malaysian Llama Language Normaliser**: Normalises candidate speech text from an upstream ASR/manual transcript source into standard British English using Malaysian Llama + LoRA.
    - **TTS Node**: Subscribes to text messages and performs voice synthesis (using `pyttsx3` or `espeak`).
- **`juno_bringup`**:
    - **Centralized Launch (`launch/juno_robot.launch`)**: Initializes the camera, microphone, transcriber, and TTS nodes in a single command.

---

## 4. Documentation
Located in `/docs`, providing guidance on system architecture and integration.

- **Implementation Plan**: Roadmap for features like emotion recognition and productivity tools.
- **ROS Integration Guide**: Instructions for setting up the ROS environment on the Jupiter robot.
- **Jupiter Integration Notes**: Specifics on interfacing with the Jupiter hardware (LEDs, movement, sensors).
- **Project Component Specifications**: (This document) Detailed breakdown of the system architecture.

---

## 5. Functional Overview
| Feature | Implementation | Component |
| :--- | :--- | :--- |
| **Emotion Recognition** | OpenCV + CNN (Mocked in current version) | `backend/src/vision` |
| **Speech text normalisation** | Malaysian Llama + LoRA text normalisation | `src/language_pkg` |
| **Text-to-Speech (TTS)** | ROS TTS Node / `pyttsx3` | `src/language_pkg` |
| **Schedule Management** | SQLite + Calendar Service | `backend/src/calendar_module` |
| **Affirmations** | NLP Response Generator | `backend/src/nlp` |
| **Study Support** | Timer Service + Music Service | `backend/src/productivity` |
