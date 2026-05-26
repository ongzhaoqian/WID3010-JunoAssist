# ROS Integration Guide for JUNO Assist and Jupiter Robot

## Read This First

This document is the **runtime and integration guide**: how to run JUNO Assist with ROS, the backend, dashboard, ASR/TTS, camera, and vision pipeline.

Use this file when you need:

- terminal commands for the robot/demo setup
- ROS node and topic information
- `.venv` vs `.venv-vision` setup guidance
- camera, microphone, ASR, TTS, and dashboard integration details
- testing commands and troubleshooting steps

Most teammates should start at **Section 5: Virtual Environment Policy** and **Section 6: Running the Integrated System** during setup.

## Quick Navigation

| Need | Go to |
|---|---|
| Know which virtual environment to use | Section 5: Virtual Environment Policy |
| Run the live demo | Section 6: Running the Integrated System |
| Check ROS/audio/camera/TTS quickly | Section 7: Testing |
| Capture and explain the ROS graph | Section 8: RQT Graph Evidence |
| Find important source files | Section 9: Key Source Files |
| Follow the demo speech flow | Section 10: Demo Script |
| Read detailed preserved vision/robot notes | Appendix A onwards |

## Demo Rule of Thumb

For the live demo, use **4 terminals only**:

1. `roscore`
2. `roslaunch juno_bringup juno_robot.launch`
3. backend in ROS mode using `backend/.venv`
4. dashboard using `npm run dev`

Do **not** open a separate `.venv-vision` terminal during the demo unless you are debugging or running tests. `.venv-vision` is for vision tests/CNN experiments, not the normal runtime.

---

This guide explains how the FastAPI backend, React dashboard, and Jupiter Robot ROS nodes are integrated. Speech recognition uses `openai/whisper-tiny` as the primary ASR engine, with `moonshine/base` (via `moonshine-onnx`) as an automatic fallback if Whisper fails to load.

## 1. Current ROS Topics

| Node | Topic | Message Type | Purpose |
|---|---|---|---|
| `camera_node.py` | `/camera/image_raw` | `sensor_msgs/Image` | Publishes Jupiter/laptop camera frames. |
| `microphone_node.py` | `/audio/raw` | `std_msgs/Float32MultiArray` | Publishes mono float32 microphone samples at 16 kHz. |
| `transcriber.py` | `/speech/transcript` | `std_msgs/String` | Runs ASR (Whisper primary, Moonshine fallback) and publishes recognised text. |
| External ASR or `example_transcriptor.py` | `/speech/raw_transcript` | `std_msgs/String` | Manual/external transcript fallback; relayed to `/speech/transcript`. |
| `tts_node.py` | `/juno/tts` | `std_msgs/String` | Speaks backend responses using a British English voice where available. |
| `tts_node.py` | `/juno/tts_done` | `std_msgs/String` | Signals that TTS has finished so STT can resume. |
| Backend ROS bridge | `/juno/led_state` | `std_msgs/String` | Optional LED/status feedback. |
| FastAPI backend | `/api/vision/camera/stream` | MJPEG over HTTP | Streams `/camera/image_raw` to the dashboard camera window. |

## 2. Integration Flow

### Speech pipeline

```text
User speech
  ↓
microphone_node.py publishes /audio/raw
  ↓
transcriber.py — tries openai/whisper-tiny, falls back to moonshine/base if Whisper unavailable
  ↓
/speech/transcript
  ↓
FastAPI backend RosJupiterInterface subscribes /speech/transcript
  ↓
Backend runs the same command pipeline used by the dashboard
  ↓
Backend publishes British English response to /juno/tts
  ↓
tts_node.py speaks the response, then publishes /juno/tts_done
  ↓
transcriber.py resumes listening
```

### Manual fallback

```text
example_transcriptor.py or external ASR
  ↓
/speech/raw_transcript
  ↓
transcriber.py relays it directly to /speech/transcript
```

### Vision pipeline

```text
Jupiter camera
  ↓
camera_node.py publishes /camera/image_raw
  ↓
FastAPI backend RosJupiterInterface subscribes /camera/image_raw
  ↓
FastAPI exposes latest frames as /api/vision/camera/stream
  ↓
React dashboard shows the live feed inside the Jupiter Camera View panel
  ↓
EmotionDetector also receives the latest frame and updates current emotion via WebSocket
```

## 3. ASR Engine Strategy

| Engine | Package | Model | When used |
|---|---|---|---|
| Whisper Tiny | `transformers` (HuggingFace) | `openai/whisper-tiny` | Primary — always tried first |
| Moonshine Base | `moonshine-onnx` | `moonshine/base` | Fallback — used if Whisper fails to load (e.g. PyTorch/memory issue on robot) |

The transcriber logs which engine loaded:

```
JUNO transcriber ready. Primary: openai/whisper-tiny | Fallback: moonshine/base
```

Per-transcript output shows the active engine:

```
[TRANSCRIBED SPEECH] (Whisper) hey john what is my schedule today
[TRANSCRIBED SPEECH] (Moonshine) hey john what is my schedule today
```

Whisper is an ASR/speech-translation model, not a chatbot. It converts speech to text only. Backend intent classification and response generation remain deterministic.

## 4. Environment Variables

```bash
# ASR — primary (Whisper)
export JUNO_ASR_MODEL_ID=openai/whisper-tiny
export JUNO_ASR_TASK=transcribe
export JUNO_ASR_LANGUAGE=
export JUNO_ASR_SAMPLE_RATE=16000
export JUNO_ASR_WINDOW_SECONDS=3.0
export JUNO_ASR_MIN_RMS=0.035
export JUNO_ASR_DEVICE=-1
export JUNO_ASR_TTS_RESUME_DELAY=0.5

# ASR — fallback (Moonshine)
export JUNO_ASR_MOONSHINE_MODEL=moonshine/base

# Microphone — use name-based selection so index does not change on reboot
export JUNO_MIC_DEVICE_NAME="0x46d:0x825"   # substring of pyaudio device name; adjust if mic differs
export JUNO_MIC_SOURCE_RATE=48000
export JUNO_MIC_CHUNK_SIZE=1024
# export JUNO_MIC_DEVICE_INDEX=7             # fallback: use index only if JUNO_MIC_DEVICE_NAME is unset
```

Use `JUNO_ASR_TASK=translate` when you want non-English speech translated to English before intent classification. Use `JUNO_ASR_TASK=transcribe` to keep the transcript in the spoken language.

## 5. Virtual Environment Policy

Use **two separate Python virtual environments**:

| Environment | Used for | Do not use for |
|---|---|---|
| `backend/.venv` | FastAPI backend, ROS bridge, ASR/TTS runtime, normal robot demo | TensorFlow/CNN vision experiments |
| `backend/.venv-vision` | Vision tests, OpenCV/TensorFlow/CNN emotion recognition experiments | Running `python main.py` for the demo |

Reason: TensorFlow/OpenCV vision dependencies can conflict with backend dependencies such as FastAPI/Pydantic/`typing-extensions`.

For the live demo, run the backend/TTS/ROS path with:

```bash
cd backend
source .venv/bin/activate
python main.py
```

For vision tests or CNN setup, use:

```bash
cd backend
.venv-vision/bin/python3 -m pytest tests/test_emotion_smoothing.py -v
```

Do **not** merge the two environments unless all dependency conflicts have been tested and resolved.

## 6. Running the Integrated System

### Terminal 1: ROS Core

```bash
roscore
```

### Terminal 2: Catkin Workspace and ROS Nodes

From the project root:

```bash
catkin_make
source devel/setup.bash
pip install -r src/language_pkg/requirements-asr.txt
amixer -c 3 sset Mic cap on
amixer -c 3 sset Mic 16
roslaunch juno_bringup juno_robot.launch
```

This launches:

- `camera_node.py` — camera publisher for the dashboard stream
- `microphone_node.py` — microphone publisher (device resolved by `JUNO_MIC_DEVICE_NAME`, 48 kHz → 16 kHz)
- `transcriber.py` — Whisper primary / Moonshine fallback ASR
- `tts_node.py` — British English TTS with `/juno/tts_done` signal

The normal camera view is now the web dashboard panel. Do **not** launch `camera_listener_node.py` for normal operation because it is only a diagnostic listener. If you need the old OpenCV pop-up for debugging, run it explicitly with `_display_window:=true`.

### Terminal 3: Backend in ROS Mode

```bash
cd backend
source ../devel/setup.bash
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
export JUNO_ROBOT_INTERFACE=ros
export JUNO_DASHBOARD_URL=http://localhost:5173
python main.py
```

If the dashboard runs on a different machine from the backend:

```bash
export JUNO_DASHBOARD_URL=http://ROBOT_IP:5173
```

### Terminal 4: Dashboard

```bash
cd dashboard
npm install
npm run dev
```

If the dashboard runs on a different machine from the backend:

```bash
VITE_API_BASE=http://ROBOT_IP:8000 npm run dev
```


### Dashboard Camera Stream

After ROS, backend, and dashboard are running:

1. Open the dashboard.
2. The **Jupiter Camera View** panel appears as an inactive camera window.
3. Click **Switch On Camera** to show the raw webcam stream from `/camera/image_raw`.
4. Leave **Vision Module** off for camera-only monitoring, or switch it on to load/run emotion recognition.
5. Use **Refresh** to restart the browser MJPEG stream without restarting ROS.

Useful diagnostics:

```bash
rostopic hz /camera/image_raw
curl http://localhost:8000/api/vision/status
```

Camera and vision controls are intentionally separate:

```text
POST /api/vision/camera/start     # show camera feed in dashboard
POST /api/vision/camera/stop      # hide camera feed and stop model inference
POST /api/vision/camera/refresh   # refresh browser stream/status
POST /api/vision/model/start      # enable emotion recognition
POST /api/vision/model/stop       # disable emotion recognition
```

If the dashboard is on a separate laptop, set the frontend API base to the robot/backend IP:

```bash
VITE_API_BASE=http://ROBOT_IP:8000 npm run dev
```

The old ROS pop-up camera window is disabled by default in `camera_listener_node.py`. To intentionally open it for debugging only:

```bash
rosrun perception_pkg camera_listener_node.py _display_window:=true
```

### Terminal 5: Manual Speech Input Fallback

```bash
source devel/setup.bash
rosrun language_pkg example_transcriptor.py
```

Then type commands:

```text
Hey, John
Yes
What is my schedule today?
I feel tired, what should I do?
```

## 7. Testing

Check audio is being published:

```bash
rostopic echo /audio/raw
```

Check recognised transcripts:

```bash
rostopic echo /speech/transcript
```

Manually inject transcript (bypasses ASR):

```bash
rostopic pub /speech/raw_transcript std_msgs/String "data: 'Hey, John'"
rostopic pub /speech/raw_transcript std_msgs/String "data: 'Yes'"
rostopic pub /speech/raw_transcript std_msgs/String "data: 'What is my schedule today?'"
```

Check TTS output and done signal:

```bash
rostopic echo /juno/tts
rostopic echo /juno/tts_done
```

Directly test the ROS TTS node without involving the backend:

```bash
rosrun language_pkg tts_test_publisher.py "Hello, I am JUNO and my speech node is working."
```

Directly test the backend-to-ROS TTS publisher without involving STT or intent classification:

```bash
curl -X POST http://localhost:8000/api/robot/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, I am JUNO and my backend speech path is working."}'
```

When `/speech/transcript` works but the robot is silent, isolate the issue as follows:

1. If `rostopic echo /juno/tts` shows no text after the `curl` command, the backend is not running in ROS mode. Check `export JUNO_ROBOT_INTERFACE=ros` before `python main.py`.
2. If `/juno/tts` receives text but there is no audio, check the `juno_tts_node` terminal output and ensure `espeak-ng` or `espeak` is installed.
3. If the first response is sometimes missed, keep `JUNO_TTS_PUBLISHER_WAIT_SECONDS=2.0`; the backend waits for the TTS subscriber and retries the publish.

Check backend ASR/AI status:

```bash
curl http://localhost:8000/api/ai/status
```

## 8. RQT Graph Evidence

Use this section for the Q4 report evidence. Run it after ROS nodes and the backend are active.

### Start the system first

Terminal 1:

```bash
source /opt/ros/noetic/setup.bash
roscore
```

Terminal 2:

```bash
cd ~/WID3010-JunoAssist
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch juno_bringup juno_robot.launch
```

Terminal 3:

```bash
cd ~/WID3010-JunoAssist/backend
source ../devel/setup.bash
source .venv/bin/activate
export JUNO_ROBOT_INTERFACE=ros
python main.py
```

### Open RQT graph

Terminal 4:

```bash
source /opt/ros/noetic/setup.bash
source ~/WID3010-JunoAssist/devel/setup.bash
rqt_graph
```

In the graph window, refresh after all nodes are running. The main graph should show the relationships between these nodes/topics where available:

```text
/camera_node → /camera/image_raw
/microphone_node → /audio/raw
/whisper_tiny_transcriber subscribes /audio/raw
/whisper_tiny_transcriber → /speech/transcript
/juno_backend_bridge subscribes /speech/transcript and /camera/image_raw, if visible
/juno_backend_bridge → /juno/tts, if visible
/juno_tts_node subscribes /juno/tts
/juno_tts_node → /juno/tts_done
/whisper_tiny_transcriber subscribes /juno/tts_done
```

### Supporting commands

Use these commands to support the graph screenshot and verify publishers/subscribers:

```bash
rosnode list
rostopic list
rostopic info /camera/image_raw
rostopic info /audio/raw
rostopic info /speech/transcript
rostopic info /juno/tts
rostopic info /juno/tts_done
```

### Report explanation template

```text
The RQT graph shows the communication structure of JUNO Assist. The camera_node publishes image frames to /camera/image_raw, and the microphone_node publishes raw audio to /audio/raw. The whisper_tiny_transcriber subscribes to /audio/raw, converts speech to text, and publishes recognised commands to /speech/transcript. The backend ROS bridge subscribes to /speech/transcript and /camera/image_raw, allowing the backend to process user commands and camera frames for decision-making. The backend publishes response text to /juno/tts. The juno_tts_node subscribes to /juno/tts, speaks the response, and publishes /juno/tts_done once speech output is complete. The transcriber subscribes to /juno/tts_done so it can resume listening after the robot finishes speaking.
```

If the backend node does not appear clearly in the graph, include the following note and support it with `rostopic info` screenshots:

```text
The backend ROS bridge is embedded inside the FastAPI backend process, so it may not always appear clearly in rqt_graph depending on graph refresh timing. Its publisher/subscriber connections were verified using rostopic info and rostopic echo for /speech/transcript, /camera/image_raw, /juno/tts, and /juno/tts_done.
```

## 9. Key Source Files

| File | Purpose |
|---|---|
| `src/language_pkg/scripts/transcriber.py` | ASR node — Whisper primary, Moonshine fallback, TTS mute/resume, manual relay. |
| `src/language_pkg/scripts/tts_node.py` | TTS node — British English voice, publishes `/juno/tts_done`. |
| `src/language_pkg/scripts/helper.py` | Pre-downloads Whisper model assets into local cache. |
| `src/language_pkg/scripts/example_transcriptor.py` | Manual text input that publishes to `/speech/raw_transcript`. |
| `src/juno_bringup/launch/juno_robot.launch` | Launches all robot-side ROS nodes. |
| `src/perception_pkg/scripts/microphone_node.py` | Captures mic audio, downsamples 48 kHz → 16 kHz, publishes `/audio/raw`. |
| `backend/src/robot/ros_jupiter_interface.py` | Backend ROS bridge — subscribes `/speech/transcript`, `/camera/image_raw`; publishes `/juno/tts`, `/juno/led_state`. |
| `backend/src/api/app.py` | Centralised `process_command_text()` pipeline shared by dashboard and ROS. |
| `backend/src/activation/wake_word_detector.py` | Fuzzy wake word detection with `difflib` — handles ASR mishearing of "Hey, John". |
| `backend/src/core/config.py` | All `JUNO_ASR_*` and robot settings. |
| `backend/src/speech/speech_to_text.py` | Lazy-loaded Whisper utility for non-ROS/test paths. |
| `src/language_pkg/requirements-asr.txt` | ASR dependencies (Whisper + Moonshine). |

## 10. Demo Script

1. Launch ROS nodes (Terminal 2).
2. Start backend with `JUNO_ROBOT_INTERFACE=ros` (Terminal 3).
3. Start dashboard (Terminal 4).
4. Say or publish:

```text
Hey, John
```

5. JUNO replies:

```text
Are you sure you would like to power Juno on? Answer yes if you do, else ignore.
```

6. Say or publish:

```text
Yes
```

7. JUNO enters active mode and opens the dashboard.
8. Try:

```text
What is my schedule today?
Set a 25 minute timer.
I feel tired today, how should I start studying?
Play relaxing music.
Juno, go to sleep.
```

## 11. Recommended Scope for Course Demo

- ROS camera and microphone input
- Whisper Tiny ASR with Moonshine fallback
- Manual transcript fallback via `example_transcriptor.py`
- Backend deterministic intent handling
- Dashboard visual feedback
- British English TTS output
- Lightweight emotion estimate

Avoid depending on a large cloud or local LLM during the live robot demo.

## 12. Voice Schedule Capture

The ROS speech path can now send structured schedule commands to the backend. After Whisper publishes a transcript to `/speech/transcript`, the backend can detect schedule creation requests and extract the following fields:

```text
date: YYYY-MM-DD
time: HH:MM or spoken AM/PM format
purpose: schedule title / task purpose
priority: low, medium, high, urgent, or important
```

Example command:

```text
add schedule date 2026-05-20 time 15:30 purpose project discussion priority high
```

The backend stores the date as `2026-05-20` but returns the dashboard-friendly format `20 May, 2026` through the `formatted_date` field. This allows the dashboard to remain readable while retaining a standard machine-readable date internally.

## 13. Phrase Bank Responses

Robot phrasing is centralised in `backend/src/nlp/phrase_bank.py`. This avoids scattering one fixed sentence across each scenario and lets JUNO vary its spoken responses naturally for wake confirmation, timer setup, schedule creation, reminders, music, and fallback responses.

---

# Appendix A: Preserved Detailed ROS, Robot Setup, Vision, and Verification Notes


## Appendix A1: Preserved from `docs/vanness/README.md`

## Vanness — Vision and Emotion Integration

**Primary role:** Backend-Vision layer owner  
**Secondary support:** Break recommender verification, emotion smoothing tests  
**Rubric coverage:** Vision Integration, HRI emotion-aware response

---

### File Ownership

#### Owned by Vanness (strict Backend-Vision boundary)

| File | Status | Required Action |
|---|---|---|
| `backend/src/vision/emotion_detector.py` | Implemented — mock weighted predictor | Upgrade: swap `EmotionSmoother` for `EMAFusion + HysteresisStateMachine` |
| `backend/src/vision/emotion_smoothing.py` | Implemented — majority-vote smoother | Keep as-is (used by existing tests); replaced by `emotion_fusion.py` in new code |
| `backend/src/vision/emotion_fusion.py` | Not yet created | **Create this file** — EMA + Hysteresis smoother |
| `backend/tests/test_emotion_smoothing.py` | 1 test (majority vote only) | **Extend** with EMA + Hysteresis tests |

> Do not touch files outside `backend/src/vision/` and `backend/tests/`. Changes to `app.py`, `ros_jupiter_interface.py`, `break_recommender.py`, or ROS nodes require coordination with Jon or Anas first.

#### Read-only / Coordinate with Owner

| File | Owner | What Vanness verifies |
|---|---|---|
| `src/perception_pkg/scripts/camera_node.py` | Anas | `/camera/image_raw` topic publishes at 30 Hz |
| `backend/src/robot/ros_jupiter_interface.py` | Anas | `_camera_callback` stores latest frame correctly |
| `backend/src/api/app.py` | Jon | `_emotion_monitor_loop` calls `predict_from_frame()` every 3 s |
| `backend/src/productivity/break_recommender.py` | Jon (support) | Tired/Stressed/Frustrated trigger correct break responses |

---

### Task Checklist (Priority Order)

#### Must — Required for demo
- [ ] Confirm mock `EmotionDetector` runs without errors in mock mode (no hardware needed)
- [ ] Confirm dashboard `current_emotion` field updates via `/ws/status` during active mode
- [ ] Verify tired/stressed/frustrated emotion triggers break recommendation (`REQUEST_BREAK` and `ASK_STATUS` intents)
- [ ] Prepare dashboard screenshot showing emotion state in active mode
- [ ] Work with Anas to verify `/camera/image_raw` publishes at 30 Hz during robot lab session
- [ ] Capture camera/emotion evidence screenshot or terminal output for the report

#### Should — Complete if core demo is stable
- [ ] Create `backend/src/vision/emotion_fusion.py` with `EMAFusion` and `HysteresisStateMachine`
- [ ] Update `backend/src/vision/emotion_detector.py` to use `EMAFusion + HysteresisStateMachine`
- [ ] Extend `backend/tests/test_emotion_smoothing.py` with EMA + Hysteresis unit tests
- [ ] Run all tests: `cd backend && python -m pytest tests/ -v`

#### Optional — Only if core items are all stable
- [ ] Add OpenCV DNN face detection in `emotion_detector.py`
- [ ] Integrate Mini-Xception CNN for real emotion classification

---

### Deliverables

| Deliverable | Where to put it |
|---|---|
| Report subsection: Vision Integration and Emotion-Aware Behaviour | See `03_report_section_draft.md` for a ready-to-submit draft |
| Dashboard emotion screenshot (active mode) | Capture during demo rehearsal |
| Camera/emotion evidence (terminal or dashboard) | Capture during robot lab session with Anas |
| Limitation paragraph (mock vs. real, ethical disclaimer) | Included in `03_report_section_draft.md` |

---

### Document Index

| File | Purpose |
|---|---|
| `01_vision_emotion_pipeline.md` | Full technical implementation: camera path, emotion pipeline, all Python code |
| `02_testing_verification.md` | Unit tests, ROS verification commands, dashboard checks, evaluation criteria |
| `03_report_section_draft.md` | Complete report section ready to submit |
| `04_robot_setup.md` | Step-by-step Ubuntu VS Code setup guide for the robot machine |

---

### Architecture Summary (Vanness's slice)

```
camera_node ──/camera/image_raw──► RosJupiterInterface._camera_callback
                                           │ (stores self.latest_frame)
                                           ▼
                              robot.get_camera_frame()
                                           │ (called every 3 s by _emotion_monitor_loop)
                                           ▼
                              EmotionDetector.predict_from_frame(frame)
                                           │
                              ┌────────────┴────────────┐
                              │ Mock path (MVP)          │ Real path (optional)
                              │ random.choice(weights)   │ face detect → CNN infer
                              └────────────┬────────────┘
                                           │ P_juno (5-class vector)
                                           ▼
                              EMAFusion.update(P_juno)      ← emotion_fusion.py
                                           │ P_t (smoothed distribution)
                                           ▼
                              HysteresisStateMachine.update(P_t) → EmotionState
                                           │
                              robot_state.set_emotion(emotion)
                                           │
                              /ws/status WebSocket broadcast
                                           │
                              Dashboard: current_emotion display
                                           │
                              ResponseGenerator.generate(intent, emotion, text)
                                           │
                              BreakRecommender.recommend(emotion)
```


## Appendix A2: Preserved from `docs/vanness/01_vision_emotion_pipeline.md`

## Vision and Emotion Pipeline — Technical Implementation

> Companion to `docs/technical_requirements_emotion.md` and `docs/product_requirements.md § F4`.  
> **Layer boundary:** All code in this document lives in `backend/src/vision/` and `backend/tests/`.  
> Do not modify files outside this boundary without coordinating with the owner listed in `README.md`.

---

### 0. Pre-Integration Checklist (Run Before Anything Else)

Before touching any vision code, verify these pass:

```bash
## From project root
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

Both existing tests must pass before you start:
```
tests/test_emotion_smoothing.py::test_emotion_smoother_returns_majority   PASSED
tests/test_intent_classifier.py::...                                       PASSED
```

If either fails, **stop and report the failure** — do not proceed with changes.

---

### 1. Camera Integration Path (ROS → Backend)

Vanness verifies this path works. The implementation is owned by Anas (`ros_jupiter_interface.py`) and the perception_pkg (`camera_node.py`).

#### Data flow

```
src/perception_pkg/scripts/camera_node.py
    Publishes: sensor_msgs/Image on /camera/image_raw at 30 Hz
    Source: cv2.VideoCapture("/dev/video2")
    Shebang: #!/usr/bin/env python3  ✓
    Execute permission: -rwxr-xr-x   ✓  (already set — no chmod needed)
         │
         ▼  ROS topic: /camera/image_raw
         │
backend/src/robot/ros_jupiter_interface.py → RosJupiterInterface._camera_callback
    Converts: sensor_msgs/Image → OpenCV BGR via cv_bridge
    Stores:   self.latest_frame (overwritten on every frame arrival)
         │
         ▼
robot.get_camera_frame()  → returns self.latest_frame (None if no frame yet)
         │
         ▼
backend/src/api/app.py → _emotion_monitor_loop (asyncio task, runs every 3 s)
    frame = robot.get_camera_frame()
    emotion = emotion_detector.predict_from_frame(frame)
    robot_state.set_emotion(emotion)
         │
         ▼
/ws/status WebSocket broadcast  →  dashboard current_emotion field
```

#### Key contract points

- `_emotion_monitor_loop` in `app.py` only runs when `robot_state.snapshot()["mode"] == RobotMode.ACTIVE`. The emotion field stays at its last value when Juno is idle or in confirmation mode.
- In **mock mode** (`JUNO_ROBOT_INTERFACE` not set), `robot.get_camera_frame()` returns `None`. `EmotionDetector.predict_from_frame(None)` handles `None` safely via the mock path.
- `_camera_callback` runs on a ROS subscriber thread; `get_camera_frame()` is called on the asyncio thread. `self.latest_frame` is not protected by a lock, but this is acceptable for demo purposes — a stale frame produces a valid (if slightly delayed) emotion estimate.

#### ROS catkin workspace — what is already set up

| Item | Location | Status |
|---|---|---|
| Camera node | `src/perception_pkg/scripts/camera_node.py` | Exists, executable |
| Microphone node | `src/perception_pkg/scripts/microphone_node.py` | Exists, executable |
| Transcriber | `src/language_pkg/scripts/transcriber.py` | Exists, executable |
| TTS node | `src/language_pkg/scripts/tts_node.py` | Exists, executable |
| Launch file | `src/juno_bringup/launch/juno_robot.launch` | Exists |
| Package manifests | `src/*/package.xml` | Exists with correct dependencies |
| CMakeLists.txt | `src/*/CMakeLists.txt` | Exists |
| ROS bridge | `backend/src/robot/ros_jupiter_interface.py` | Exists |

**Vanness does NOT modify any file in `src/` or `backend/src/robot/`.** All these are already implemented and owned by Anas/Jon.

#### Build and run sequence (ROS machine only)

```bash
## From project root — only needs to be done once per session
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash

## Terminal 1: roscore
roscore

## Terminal 2: launch perception + language nodes
roslaunch juno_bringup juno_robot.launch

## Terminal 3: backend in ROS mode
unset PYTHONPATH
source /opt/ros/noetic/setup.bash
source devel/setup.bash
cd backend
source .venv/bin/activate
export PYTHONPATH=/opt/ros/noetic/lib/python3/dist-packages:$PYTHONPATH
export JUNO_ROBOT_INTERFACE=ros
python3 main.py

## Terminal 4: dashboard
cd dashboard
npm run dev
```

> `rospkg` must be installed in the venv (`pip install rospkg`). `unset PYTHONPATH` before sourcing prevents stale paths from a previous session causing protobuf version conflicts.

---

### 2. Current MVP Implementation

These files run **without hardware**. Verify they work first. Do not modify them until confirmed passing.

#### `backend/src/vision/emotion_smoothing.py` (existing — keep as-is)

```python
from collections import deque, Counter
from src.core.models import EmotionState


class EmotionSmoother:
    def __init__(self, window_size: int = 10) -> None:
        self.window_size = window_size
        self._window: deque[EmotionState] = deque(maxlen=window_size)

    def add(self, emotion: EmotionState) -> EmotionState:
        self._window.append(emotion)
        return self.current()

    def current(self) -> EmotionState:
        if not self._window:
            return EmotionState.UNKNOWN
        counts = Counter(self._window)
        return counts.most_common(1)[0][0]
```

**Do not delete this file.** The existing test file imports from it. It stays alongside `emotion_fusion.py`.

#### `backend/src/vision/emotion_detector.py` (existing MVP)

```python
import random
from src.core.models import EmotionState
from .emotion_smoothing import EmotionSmoother


class EmotionDetector:
    def __init__(self) -> None:
        self.smoother = EmotionSmoother(window_size=8)
        self.weighted_emotions = [
            EmotionState.NEUTRAL,
            EmotionState.NEUTRAL,
            EmotionState.NEUTRAL,
            EmotionState.TIRED,
            EmotionState.STRESSED,
            EmotionState.HAPPY,
            EmotionState.FRUSTRATED,
        ]

    def predict_from_frame(self, frame=None) -> EmotionState:
        predicted = random.choice(self.weighted_emotions)
        return self.smoother.add(predicted)
```

**How to verify it runs without a robot (mock mode):**

```bash
cd backend
source .venv/bin/activate

## Start backend in mock mode (no ROS needed)
python main.py
## Expected: "Application startup complete." — no errors

## In another terminal, verify emotion is in the status response
curl -s http://localhost:8000/api/status | python3 -m json.tool
## Look for "current_emotion": — it will be "unknown" until ACTIVE mode

## Activate JUNO then check emotion changes
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "Hey, John"}'

curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "Yes"}'

## Now check status — current_emotion should be a valid state (not "unknown")
curl -s http://localhost:8000/api/status | python3 -m json.tool
```

---

### 3. Upgraded Emotion Pipeline — EMA + Hysteresis (Should)

The upgrade replaces `EmotionSmoother` (majority vote) with `EMAFusion + HysteresisStateMachine`.  
**The public interface `predict_from_frame(frame=None) -> EmotionState` is unchanged — `app.py` needs zero modification.**

#### 3.1 Step 0: Install vision deps in `.venv-vision`

Vision dependencies (`numpy`, `opencv`, `tensorflow`) conflict with the backend's `typing-extensions` requirement — tensorflow 2.13 requires `<4.6.0` while fastapi/pydantic require `>=4.8.0`. They live in a separate venv.

```bash
cd backend
python3 -m venv .venv-vision
.venv-vision/bin/pip install --upgrade pip
.venv-vision/bin/pip install -r requirements-vision.txt
```

`requirements-vision.txt` contains:
```
numpy>=1.24,<1.25
opencv-python-headless>=4.8
tensorflow>=2.13,<2.14
```

Verify:

```bash
.venv-vision/bin/python3 -c "import numpy; import cv2; import tensorflow as tf; print('numpy', numpy.__version__); print('cv2', cv2.__version__); print('tf', tf.__version__)"
```

All three must print a version number. Numpy must be `1.24.x`, TensorFlow `2.13.x`.

> **Important:** The backend (`python main.py`) still uses `.venv`, not `.venv-vision`. Vision tests and any TensorFlow inference must use `.venv-vision/bin/python3`. The two venvs are kept separate — do not merge them.

#### 3.2 Create `backend/src/vision/emotion_fusion.py` (new file)

Create this file at exactly `backend/src/vision/emotion_fusion.py`. It has no dependencies outside `numpy` and `src.core.models`.

```python
import numpy as np

from src.core.models import EmotionState

ALPHA: float = 0.30
DWELL_FRAMES: int = 45

## Ordered labels — index must match probability vector positions used throughout this module
_LABELS = [
    EmotionState.HAPPY,       # index 0
    EmotionState.NEUTRAL,     # index 1
    EmotionState.TIRED,       # index 2
    EmotionState.STRESSED,    # index 3
    EmotionState.FRUSTRATED,  # index 4
]


class EMAFusion:
    """Exponential Moving Average over the 5-class Juno emotion probability distribution.

    Retains uncertainty across frames. α=0.30 weights recent frames ~1.4× more than
    older ones while providing smooth output. Initialises to Neutral.
    """

    def __init__(self, alpha: float = ALPHA) -> None:
        self.alpha = alpha
        # P_t[1] = Neutral = 1.0 on start
        self.P_t = np.array([0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    def update(self, P_juno: np.ndarray) -> np.ndarray:
        """Blend new Juno-5 probability vector into the running estimate."""
        self.P_t = self.alpha * P_juno + (1.0 - self.alpha) * self.P_t
        return self.P_t.copy()

    def skip(self) -> np.ndarray:
        """Call when face detection fails — distribution held, not updated."""
        return self.P_t.copy()

    def reset(self) -> None:
        self.P_t = np.array([0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)


class HysteresisStateMachine:
    """Commits a new emotion only after it leads argmax for DWELL_FRAMES consecutive frames.

    Prevents the displayed emotion from flickering between adjacent states (e.g.
    Neutral ↔ Tired) due to momentary changes in a single frame.
    """

    def __init__(self, dwell_frames: int = DWELL_FRAMES) -> None:
        self.dwell_frames = dwell_frames
        self.current_state: EmotionState = EmotionState.NEUTRAL
        self.candidate: EmotionState = EmotionState.NEUTRAL
        self.dwell_count: int = 0

    def update(self, P_t: np.ndarray) -> EmotionState:
        new_candidate = _LABELS[int(np.argmax(P_t))]

        if new_candidate == self.candidate:
            self.dwell_count += 1
        else:
            self.candidate = new_candidate
            self.dwell_count = 1

        if (self.dwell_count >= self.dwell_frames
                and new_candidate != self.current_state):
            self.current_state = new_candidate
            self.dwell_count = 0

        return self.current_state
```

#### 3.3 Replace `backend/src/vision/emotion_detector.py`

The only changes from the MVP version are:
- Import `EMAFusion` and `HysteresisStateMachine` instead of `EmotionSmoother`
- Convert the randomly chosen emotion to a one-hot probability vector before feeding it to EMA
- Return type `EmotionState` is **unchanged** — `app.py` is untouched

```python
import random
from typing import Any

import numpy as np

from src.core.models import EmotionState
from .emotion_fusion import EMAFusion, HysteresisStateMachine

_MOCK_WEIGHTS = [
    EmotionState.NEUTRAL,
    EmotionState.NEUTRAL,
    EmotionState.NEUTRAL,
    EmotionState.TIRED,
    EmotionState.STRESSED,
    EmotionState.HAPPY,
    EmotionState.FRUSTRATED,
]

## One-hot Juno-5 vectors — index order must match emotion_fusion._LABELS exactly:
## [Happy=0, Neutral=1, Tired=2, Stressed=3, Frustrated=4]
_JUNO_ONE_HOT: dict = {
    EmotionState.HAPPY:      np.array([1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32),
    EmotionState.NEUTRAL:    np.array([0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32),
    EmotionState.TIRED:      np.array([0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32),
    EmotionState.STRESSED:   np.array([0.0, 0.0, 0.0, 1.0, 0.0], dtype=np.float32),
    EmotionState.FRUSTRATED: np.array([0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32),
}


class EmotionDetector:
    """Emotion detector: mock-first, upgradeable to real CNN.

    Phase 1 (MVP): weighted mock predictor  → EMA + Hysteresis smoother.
    Phase 2 (opt): face detection + CNN     → EMA + Hysteresis smoother.

    Public interface unchanged from MVP — app.py requires no modification.
    """

    def __init__(self) -> None:
        self.ema = EMAFusion()
        self.hsm = HysteresisStateMachine()

    def predict_from_frame(self, frame: Any = None) -> EmotionState:
        P_juno = self._mock_predict()
        P_t = self.ema.update(P_juno)
        return self.hsm.update(P_t)

    def _mock_predict(self) -> np.ndarray:
        mock_emotion = random.choice(_MOCK_WEIGHTS)
        return _JUNO_ONE_HOT[mock_emotion].copy()
```

#### 3.4 Migration steps (in order)

```
Step 0: Create .venv-vision and install requirements-vision.txt (§ 3.1)
Step 1: Create backend/src/vision/emotion_fusion.py  (new file, § 3.2)
Step 2: Replace backend/src/vision/emotion_detector.py  (§ 3.3)
        DO NOT delete emotion_smoothing.py
Step 3: Run tests with .venv-vision:
          cd backend && .venv-vision/bin/pip install pytest pydantic
          .venv-vision/bin/python3 -m pytest tests/test_emotion_smoothing.py -v
        All tests must pass before committing
Step 4: Verify backend starts with .venv (not .venv-vision):
          source .venv/bin/activate && python main.py  (no import errors)
Step 5: Extend test file with EMA + Hysteresis tests  (see 02_testing_verification.md)
```

#### 3.5 Verify the upgrade is working

```bash
cd backend
source .venv/bin/activate
python -c "
from src.vision.emotion_detector import EmotionDetector
from src.core.models import EmotionState

d = EmotionDetector()
for i in range(5):
    result = d.predict_from_frame()
    print(f'Call {i+1}: {result}')
    assert result in [EmotionState.HAPPY, EmotionState.NEUTRAL, EmotionState.TIRED,
                      EmotionState.STRESSED, EmotionState.FRUSTRATED], f'Invalid: {result}'
print('All calls returned valid EmotionState — upgrade OK')
"
```

---

### 4. Optional: Real CNN Extension

> Complete only after Must checklist and Should (EMA upgrade) are both done and stable.

#### 4.1 Class remapping: FER-7 → Juno-5

Standard CNN models (Mini-Xception/FER2013) output 7 classes that do not include `Tired`, `Stressed`, or `Frustrated`. A projection matrix maps them to the 5 Juno labels.

```python
## Add to emotion_detector.py if implementing the real CNN path
## Rows = Juno-5 [Happy, Neutral, Tired, Stressed, Frustrated]
## Cols = FER-7  [Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral]
MAPPING_MATRIX = np.array([
    [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],  # Happy     ← Happy (1:1)
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.8],  # Neutral   ← Neutral(0.8) + Surprise(0.2)
    [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],  # Tired     ← Sad (low-arousal negative affect)
    [0.3, 0.1, 0.6, 0.0, 0.0, 0.0, 0.0],  # Stressed  ← Fear(0.6)+Angry(0.3)+Disgust(0.1)
    [0.7, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0],  # Frustrated← Angry(0.7)+Disgust(0.3)
], dtype=np.float32)


def _remap(P_raw: np.ndarray) -> np.ndarray:
    """Project 7-class FER softmax onto 5 Juno emotion classes."""
    P_juno = MAPPING_MATRIX @ P_raw
    total = P_juno.sum()
    if total > 0:
        P_juno /= total
    return P_juno
```

#### 4.2 Face detection (OpenCV DNN)

Model files (download, do not commit — add to `.gitignore`):
- `models/deploy.prototxt`
- `models/res10_300x300_ssd_iter_140000.caffemodel`

```python
import cv2
import numpy as np


def detect_face(frame: np.ndarray, net) -> tuple:
    """Returns (face_roi, confidence) or (None, 0.0).

    Rejection: confidence < 0.70 or area < 1000 px² → reject frame.
    """
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104, 177, 123))
    net.setInput(blob)
    detections = net.forward()

    best_conf, best_roi = 0.0, None
    for i in range(detections.shape[2]):
        conf = float(detections[0, 0, i, 2])
        if conf < 0.70:
            continue
        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
        x1, y1, x2, y2 = box.astype(int)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if (x2 - x1) * (y2 - y1) < 1000:
            continue
        if conf > best_conf:
            best_conf = conf
            best_roi = frame[y1:y2, x1:x2]
    return best_roi, best_conf
```

#### 4.3 Mini-Xception preprocessing

Input: 64×64 grayscale. Output: 7-class softmax.

```python
def preprocess_face(face_roi: np.ndarray) -> np.ndarray:
    face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    face_resized = cv2.resize(face_gray, (64, 64))
    face_norm = face_resized.astype("float32") / 255.0
    return np.expand_dims(np.expand_dims(face_norm, -1), 0)  # shape (1, 64, 64, 1)
```

#### 4.4 Extended `EmotionDetector` with real CNN path

Add `use_real` flag — when `False` (default), mock path runs unchanged. No existing callers break.

```python
class EmotionDetector:
    def __init__(self, use_real: bool = False) -> None:
        self.ema = EMAFusion()
        self.hsm = HysteresisStateMachine()
        self.use_real = use_real
        self._face_net = None
        self._cnn_model = None
        if use_real:
            self._load_models()

    def _load_models(self) -> None:
        try:
            import cv2
            from tensorflow.keras.models import load_model
            import os
            proto = "models/deploy.prototxt"
            caffe = "models/res10_300x300_ssd_iter_140000.caffemodel"
            model_path = os.getenv("EMOTION_MODEL_PATH", "models/emotion_model.h5")
            if os.path.exists(proto) and os.path.exists(caffe):
                self._face_net = cv2.dnn.readNetFromCaffe(proto, caffe)
            if os.path.exists(model_path):
                self._cnn_model = load_model(model_path, compile=False)
        except Exception as exc:
            print(f"[EmotionDetector] Model load failed: {exc}. Falling back to mock.")
            self.use_real = False

    def predict_from_frame(self, frame: Any = None) -> EmotionState:
        if (self.use_real
                and frame is not None
                and self._face_net is not None
                and self._cnn_model is not None):
            face_roi, _ = detect_face(frame, self._face_net)
            if face_roi is not None:
                tensor = preprocess_face(face_roi)
                P_raw = self._cnn_model.predict(tensor, verbose=0)[0]
                P_juno = _remap(P_raw)
                P_t = self.ema.update(P_juno)
            else:
                P_t = self.ema.skip()
        else:
            P_juno = self._mock_predict()
            P_t = self.ema.update(P_juno)
        return self.hsm.update(P_t)

    def _mock_predict(self) -> np.ndarray:
        mock_emotion = random.choice(_MOCK_WEIGHTS)
        return _JUNO_ONE_HOT[mock_emotion].copy()
```

---

### 5. Break Recommender Integration

Vanness **verifies** — the `BreakRecommender` is already implemented. Do not modify `break_recommender.py`.

#### Full emotion → response chain

```
robot_state.set_emotion(emotion)
    set by: _emotion_monitor_loop in app.py (every JUNO_EMOTION_UPDATE_SECONDS)
    reads:  emotion_detector.predict_from_frame(frame)
         │
robot_state.snapshot()["current_emotion"]
    read by: process_command_text() when handling commands
         │
ResponseGenerator.generate(intent, emotion, user_text)
    intent == REQUEST_BREAK → BreakRecommender.recommend(emotion)
    intent == ASK_STATUS    → BreakRecommender.recommend(emotion) + deadline context
         │
tts.speak(response)         → published to /juno/tts → juno_tts_node speaks it
robot_state.set_response()  → broadcast via /ws/status → dashboard last_response field
```

#### `BreakRecommender.recommend()` output by emotion state

| EmotionState | Response |
|---|---|
| `TIRED` | "You seem a little tired. I recommend a 5-minute break before continuing." |
| `STRESSED` | "You seem a bit stressed. Let us prioritise the nearest deadline and start with a short study session." |
| `FRUSTRATED` | "You seem frustrated. Try pausing briefly, then break the task into smaller steps." |
| `HAPPY` | "You seem to be doing well. This is a good time to continue your current task." |
| `NEUTRAL` | "You seem neutral. I can help you check your schedule, set a timer, or plan your next task." |

---

### 6. Dependency Reference

#### Backend `requirements.txt` (backend venv — no vision deps)

```
fastapi==0.115.6
uvicorn[standard]==0.33.0
pydantic==2.10.4
python-multipart==0.0.20
pytest==8.3.4
```

#### Vision `requirements-vision.txt` (`.venv-vision` only)

```
numpy>=1.24,<1.25
opencv-python-headless>=4.8
tensorflow>=2.13,<2.14
```

Vision deps are intentionally separated from backend deps — tensorflow 2.13 requires `typing-extensions<4.6.0` which conflicts with fastapi/pydantic's `>=4.8.0` requirement.

Do not install `deepface` — it adds ~200 MB and runs at ~80 ms/frame vs ~15 ms for Mini-Xception.

#### ROS-side dependencies (already declared in package.xml — no changes needed)

| Package | Declared in |
|---|---|
| `rospy`, `sensor_msgs`, `std_msgs` | Both perception_pkg and language_pkg package.xml |
| `cv_bridge` | perception_pkg package.xml (build_depend) |
| `pyaudio`, `moonshine_onnx` | Python packages, must be pip-installed on robot OS |
| `pyttsx3` or `espeak` | tts_node.py runtime dependency, must be present on robot |

These are Anas's responsibility. Vanness only needs to confirm `/camera/image_raw` is publishing.


## Appendix A3: Preserved from `docs/vanness/02_testing_verification.md`

## Testing and Verification — Vision and Emotion

> **Run all test commands from `backend/`** — not from project root.  
> `src/` is a Python package relative to `backend/`; running pytest from the project root will cause `ModuleNotFoundError`.

---

### 1. Environment Setup

Vision tests require `.venv-vision` (not `.venv`). Two separate venvs are used to avoid a `typing-extensions` conflict between tensorflow and fastapi/pydantic.

**Backend venv** (for running `main.py`):
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Vision venv** (for tests that import numpy/tensorflow):
```bash
cd backend
python3 -m venv .venv-vision
.venv-vision/bin/pip install --upgrade pip
.venv-vision/bin/pip install -r requirements-vision.txt
.venv-vision/bin/pip install pytest pydantic

## Confirm numpy is installed
.venv-vision/bin/python3 -c "import numpy; print('numpy', numpy.__version__)"

## Confirm pytest is available
.venv-vision/bin/python3 -m pytest --version
```

---

### 2. Baseline Test (Run Before Any Changes)

```bash
.venv-vision/bin/python3 -m pytest tests/ -v
```

Expected output before making any modifications:
```
tests/test_emotion_smoothing.py::test_emotion_smoother_returns_majority   PASSED
tests/test_intent_classifier.py::test_classify_schedule                   PASSED
tests/test_intent_classifier.py::test_classify_timer                      PASSED
...
```

If any test fails before you change anything, stop and investigate — do not proceed.

---

### 3. Full Test File: `backend/tests/test_emotion_smoothing.py`

Replace the contents of this file after creating `emotion_fusion.py`.  
**Style:** standalone functions, matching the existing codebase (`test_intent_classifier.py` uses the same pattern).

```python
"""
Tests for vision/emotion_smoothing.py (legacy smoother) and
vision/emotion_fusion.py (upgraded EMA + Hysteresis smoother).

Run from backend/: python -m pytest tests/test_emotion_smoothing.py -v
"""
import numpy as np
import pytest

from src.core.models import EmotionState


## ── Legacy EmotionSmoother (keep — still imported by emotion_smoothing.py) ───

def test_emotion_smoother_returns_majority():
    from src.vision.emotion_smoothing import EmotionSmoother
    smoother = EmotionSmoother(window_size=5)
    smoother.add(EmotionState.TIRED)
    smoother.add(EmotionState.NEUTRAL)
    smoother.add(EmotionState.NEUTRAL)
    assert smoother.current() == EmotionState.NEUTRAL


def test_emotion_smoother_empty_returns_unknown():
    from src.vision.emotion_smoothing import EmotionSmoother
    smoother = EmotionSmoother(window_size=5)
    assert smoother.current() == EmotionState.UNKNOWN


## ── EMAFusion ─────────────────────────────────────────────────────────────────

def test_ema_initialises_to_neutral():
    from src.vision.emotion_fusion import EMAFusion
    ema = EMAFusion()
    # Index 1 = Neutral; must be 1.0 on init
    assert ema.P_t[1] == pytest.approx(1.0)
    assert ema.P_t.sum() == pytest.approx(1.0)


def test_ema_skip_does_not_change_distribution():
    from src.vision.emotion_fusion import EMAFusion
    ema = EMAFusion()
    before = ema.P_t.copy()
    result = ema.skip()
    assert np.allclose(result, before)
    assert np.allclose(ema.P_t, before)  # internal state also unchanged


def test_ema_update_moves_toward_input():
    from src.vision.emotion_fusion import EMAFusion
    ema = EMAFusion(alpha=0.30)
    P_tired = np.array([0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    tired_before = float(ema.P_t[2])  # index 2 = Tired, initially 0.0
    ema.update(P_tired)
    assert ema.P_t[2] > tired_before


def test_ema_update_correct_weighted_blend():
    from src.vision.emotion_fusion import EMAFusion
    ema = EMAFusion(alpha=0.30)
    # Initial P_t = [0, 1, 0, 0, 0]  (Neutral)
    # Input       = [0, 0, 1, 0, 0]  (Tired)
    # Expected    = 0.3*[0,0,1,0,0] + 0.7*[0,1,0,0,0] = [0, 0.7, 0.3, 0, 0]
    P_tired = np.array([0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    result = ema.update(P_tired)
    expected = np.array([0.0, 0.7, 0.3, 0.0, 0.0], dtype=np.float32)
    assert np.allclose(result, expected, atol=1e-5)


def test_ema_update_returns_copy_not_reference():
    from src.vision.emotion_fusion import EMAFusion
    ema = EMAFusion()
    P_input = np.array([0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    result = ema.update(P_input)
    result[0] = 99.0   # mutate the returned array
    assert ema.P_t[0] != 99.0  # internal state must be unaffected


def test_ema_reset_restores_neutral():
    from src.vision.emotion_fusion import EMAFusion
    ema = EMAFusion()
    ema.update(np.array([1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32))  # push toward Happy
    ema.reset()
    assert ema.P_t[1] == pytest.approx(1.0)  # back to Neutral


## ── HysteresisStateMachine ────────────────────────────────────────────────────

def test_hysteresis_starts_neutral():
    from src.vision.emotion_fusion import HysteresisStateMachine
    hsm = HysteresisStateMachine()
    assert hsm.current_state == EmotionState.NEUTRAL


def test_hysteresis_no_transition_before_dwell():
    from src.vision.emotion_fusion import HysteresisStateMachine, DWELL_FRAMES
    hsm = HysteresisStateMachine()
    P_tired = np.array([0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    for _ in range(DWELL_FRAMES - 1):
        hsm.update(P_tired)
    # 44 frames of Tired — state must still be Neutral
    assert hsm.current_state == EmotionState.NEUTRAL
    assert hsm.dwell_count == DWELL_FRAMES - 1


def test_hysteresis_transitions_at_dwell():
    from src.vision.emotion_fusion import HysteresisStateMachine, DWELL_FRAMES
    hsm = HysteresisStateMachine()
    P_tired = np.array([0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    for _ in range(DWELL_FRAMES):
        hsm.update(P_tired)
    # Exactly DWELL_FRAMES frames of Tired — must have transitioned
    assert hsm.current_state == EmotionState.TIRED


def test_hysteresis_resets_dwell_on_candidate_change():
    from src.vision.emotion_fusion import HysteresisStateMachine, DWELL_FRAMES
    hsm = HysteresisStateMachine()
    P_tired = np.array([0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    P_neutral = np.array([0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    for _ in range(DWELL_FRAMES - 1):
        hsm.update(P_tired)
    assert hsm.dwell_count == DWELL_FRAMES - 1
    assert hsm.candidate == EmotionState.TIRED

    # Switch candidate to Neutral — dwell count must reset to 1
    hsm.update(P_neutral)
    assert hsm.dwell_count == 1
    assert hsm.candidate == EmotionState.NEUTRAL
    assert hsm.current_state == EmotionState.NEUTRAL  # no transition happened


def test_hysteresis_dwell_resets_after_commit():
    from src.vision.emotion_fusion import HysteresisStateMachine, DWELL_FRAMES
    hsm = HysteresisStateMachine()
    P_tired = np.array([0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    for _ in range(DWELL_FRAMES):
        hsm.update(P_tired)
    assert hsm.current_state == EmotionState.TIRED
    # dwell_count must be 0 after a committed transition
    assert hsm.dwell_count == 0


def test_hysteresis_committed_state_does_not_flicker():
    from src.vision.emotion_fusion import HysteresisStateMachine, DWELL_FRAMES
    hsm = HysteresisStateMachine()
    P_tired = np.array([0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32)

    # Commit Tired
    for _ in range(DWELL_FRAMES):
        hsm.update(P_tired)
    assert hsm.current_state == EmotionState.TIRED

    # Feed 100 more Tired frames — state must remain Tired
    for _ in range(100):
        state = hsm.update(P_tired)
    assert state == EmotionState.TIRED


## ── EmotionDetector integration (mock path) ───────────────────────────────────

_VALID_STATES = {
    EmotionState.HAPPY,
    EmotionState.NEUTRAL,
    EmotionState.TIRED,
    EmotionState.STRESSED,
    EmotionState.FRUSTRATED,
}


def test_mock_detector_returns_valid_emotion():
    from src.vision.emotion_detector import EmotionDetector
    detector = EmotionDetector()
    result = detector.predict_from_frame(frame=None)
    assert isinstance(result, EmotionState)
    assert result in _VALID_STATES


def test_mock_detector_never_returns_unknown():
    from src.vision.emotion_detector import EmotionDetector
    detector = EmotionDetector()
    for _ in range(20):
        result = detector.predict_from_frame(frame=None)
        assert result != EmotionState.UNKNOWN


def test_mock_detector_accepts_none_frame():
    """predict_from_frame must not raise when called with None (mock mode, no camera)."""
    from src.vision.emotion_detector import EmotionDetector
    detector = EmotionDetector()
    try:
        detector.predict_from_frame(frame=None)
    except Exception as exc:
        pytest.fail(f"predict_from_frame(None) raised: {exc}")


def test_mock_detector_hsm_prevents_rapid_state_change():
    """After committing a state via direct EMA and HSM drive, fewer than DWELL_FRAMES
    calls to predict_from_frame cannot change it — because the new candidate's dwell
    count starts at 0 and needs DWELL_FRAMES more frames to commit a different state.
    This test is deterministic (bypasses random mock) to avoid flakiness.

    Why DWELL_FRAMES + 1 iterations:
      EMA iteration 0: Neutral still leads (P_t[Neutral]=0.70 > P_t[Tired]=0.30).
      HSM candidate stays Neutral for 1 iteration, then switches to Tired at iteration 1.
      So the HSM only counts DWELL_FRAMES consecutive Tired frames from iteration 1,
      requiring DWELL_FRAMES + 1 total iterations to commit the transition.
    """
    from src.vision.emotion_fusion import DWELL_FRAMES
    from src.vision.emotion_detector import EmotionDetector

    detector = EmotionDetector()

    P_tired = np.array([0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    for _ in range(DWELL_FRAMES + 1):
        detector.ema.update(P_tired)
        committed = detector.hsm.update(detector.ema.P_t)
    assert committed == EmotionState.TIRED

    # The HSM is now committed to Tired with dwell_count=0.
    # Making 3 predict_from_frame calls (with random inputs) cannot change current_state
    # because any new candidate would need DWELL_FRAMES=45 consecutive frames to commit.
    for _ in range(3):
        result = detector.predict_from_frame(frame=None)
        assert result in _VALID_STATES  # valid output, no crash
```

Run after creating `emotion_fusion.py`:

```bash
.venv-vision/bin/python3 -m pytest tests/test_emotion_smoothing.py -v
```

Expected output:
```
tests/test_emotion_smoothing.py::test_emotion_smoother_returns_majority            PASSED
tests/test_emotion_smoothing.py::test_emotion_smoother_empty_returns_unknown       PASSED
tests/test_emotion_smoothing.py::test_ema_initialises_to_neutral                  PASSED
tests/test_emotion_smoothing.py::test_ema_skip_does_not_change_distribution       PASSED
tests/test_emotion_smoothing.py::test_ema_update_moves_toward_input               PASSED
tests/test_emotion_smoothing.py::test_ema_update_correct_weighted_blend           PASSED
tests/test_emotion_smoothing.py::test_ema_update_returns_copy_not_reference       PASSED
tests/test_emotion_smoothing.py::test_ema_reset_restores_neutral                  PASSED
tests/test_emotion_smoothing.py::test_hysteresis_starts_neutral                   PASSED
tests/test_emotion_smoothing.py::test_hysteresis_no_transition_before_dwell       PASSED
tests/test_emotion_smoothing.py::test_hysteresis_transitions_at_dwell             PASSED
tests/test_emotion_smoothing.py::test_hysteresis_resets_dwell_on_candidate_change PASSED
tests/test_emotion_smoothing.py::test_hysteresis_dwell_resets_after_commit        PASSED
tests/test_emotion_smoothing.py::test_hysteresis_committed_state_does_not_flicker PASSED
tests/test_emotion_smoothing.py::test_mock_detector_returns_valid_emotion          PASSED
tests/test_emotion_smoothing.py::test_mock_detector_never_returns_unknown          PASSED
tests/test_emotion_smoothing.py::test_mock_detector_accepts_none_frame             PASSED
tests/test_emotion_smoothing.py::test_mock_detector_hsm_prevents_rapid_state_change PASSED

18 passed
```

#### Failure triage

| Failing test | Most likely cause | Fix |
|---|---|---|
| `test_ema_initialises_to_neutral` | `EMAFusion.__init__` not setting P_t[1]=1.0 | Check `np.array([0.0, 1.0, ...]` init |
| `test_ema_update_correct_weighted_blend` | Alpha constant differs | Confirm `ALPHA = 0.30` in `emotion_fusion.py` |
| `test_hysteresis_transitions_at_dwell` | `DWELL_FRAMES` differs between test import and module | Both import from `src.vision.emotion_fusion` — check constant value |
| `test_ema_*` | `ModuleNotFoundError: numpy` | Add `numpy>=1.24` to `requirements.txt` and reinstall |
| `test_ema_*` or `test_hysteresis_*` | `ModuleNotFoundError: emotion_fusion` | Create `backend/src/vision/emotion_fusion.py` first |
| `test_mock_detector_*` | `ImportError` from `emotion_detector.py` | Check that `emotion_detector.py` imports from `.emotion_fusion` not `.emotion_smoothing` |

---

### 4. Backend Mock Mode Verification (No ROS Required)

```bash
## Terminal 1 — Start backend in mock mode (use .venv, NOT .venv-vision)
cd backend
source .venv/bin/activate
python main.py
## Expected: "Application startup complete." with no import errors

## Terminal 2 — Verify emotion appears in status
## First wake JUNO
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "Hey, John"}' | python3 -m json.tool

## Confirm
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "Yes"}' | python3 -m json.tool

## Check status — current_emotion should be a valid state
curl -s http://localhost:8000/api/status | python3 -m json.tool
## Expected: "current_emotion": "neutral"  (or tired/stressed/happy/frustrated)
## NOT "unknown" — that would mean _emotion_monitor_loop is not running

## Wait 3 seconds and check again — emotion should change (mock is random)
sleep 4
curl -s http://localhost:8000/api/status | python3 -m json.tool
```

---

### 5. Break Recommender Verification

JUNO must be in ACTIVE mode first (run the wake+confirm commands from § 4 above).

```bash
## Test REQUEST_BREAK intent
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "I need a break"}' | python3 -m json.tool
## "response" field should match BreakRecommender output for the current emotion

## Test ASK_STATUS intent (also emotion-aware)
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "What should I do now?"}' | python3 -m json.tool
## "response" field should include emotion context + deadline info
```

Since the mock detector cycles randomly, run the request several times to see different emotion-driven responses. Check that the `intent` field in the JSON response is `"request_break"` or `"ask_status"` — not `"unknown"`.

---

### 6. ROS Camera Topic Verification (Robot Lab Session — with Anas)

Run these during the robot lab session. Record terminal output as report evidence.

```bash
## After roslaunch juno_bringup juno_robot.launch

## Confirm camera topic is active
rostopic hz /camera/image_raw
## Expected: average rate: 30.000 (±5 Hz acceptable)

## Confirm topic exists
rostopic list | grep camera
## Expected: /camera/image_raw

## Confirm node is registered
rosnode list
## Expected: /camera_node in the list

## Confirm frames have valid headers
rostopic echo /camera/image_raw/header --noarr
## Expected: seq incrementing, stamp is recent
```

If camera topic is at wrong rate or absent:

```bash
## Check camera_node is running
rosnode info /camera_node

## Check for errors in the launch terminal
## Common issue: /dev/video2 not found → change camera_device param in launch file
roslaunch juno_bringup juno_robot.launch camera_device:=/dev/video0
```

After backend starts in ROS mode with camera running:

```bash
## Backend in ROS mode (separate terminal, after sourcing catkin devel)
export JUNO_ROBOT_INTERFACE=ros
python main.py

## Confirm backend started cleanly
## Expected log: "JUNO backend ROS bridge is ready."

## With JUNO in ACTIVE mode, check emotion is NOT "unknown"
curl -s http://localhost:8000/api/status | python3 -m json.tool
## "current_emotion" should be one of: happy/neutral/tired/stressed/frustrated
```

---

### 7. WebSocket Emotion Verification (Dashboard)

```bash
## Option A: Browser DevTools
## 1. Open http://localhost:5173
## 2. DevTools → Network → WS tab
## 3. Find /ws/status connection
## 4. Watch the JSON messages — "current_emotion" must update every ~1 s

## Option B: wscat command line
npm install -g wscat
wscat -c ws://localhost:8000/ws/status
## Watch the stream — should see JSON with current_emotion changing over time
```

Expected WebSocket payload:
```json
{
  "mode": "active",
  "current_emotion": "neutral",
  "last_response": "JUNO Assist is now online. Opening your dashboard.",
  "timer_remaining_seconds": 0,
  "active_timer_label": null
}
```

---

### 8. Evaluation Criteria Table

Fill in the "Result" column during testing. Bring this to the demo session.

| # | Criterion | Pass Condition | Test Method | Result |
|---|---|---|---|---|
| 1 | Camera topic active | `rostopic hz /camera/image_raw` ≈ 30 Hz | ROS terminal | — |
| 2 | Camera node in node list | `/camera_node` appears in `rosnode list` | ROS terminal | — |
| 3 | Backend receives frames | `current_emotion` ≠ `unknown` in ROS mode | `curl /api/status` | — |
| 4 | Mock detector valid output | Returns one of 5 valid states | Unit test 15 | — |
| 5 | Mock detector no UNKNOWN | Never returns `unknown` | Unit test 16 | — |
| 6 | Mock handles `None` frame | No crash on `predict_from_frame(None)` | Unit test 17 | — |
| 7 | EMA init correct | `P_t[1] == 1.0` on fresh instance | Unit test 3 | — |
| 8 | EMA skip no-op | Distribution unchanged after `skip()` | Unit test 4 | — |
| 9 | EMA blend correct | `0.3*Tired + 0.7*Neutral` matches exactly | Unit test 6 | — |
| 10 | HSM no early transition | State unchanged after 44 frames | Unit test 10 | — |
| 11 | HSM transitions at 45 | State commits after 45 frames | Unit test 11 | — |
| 12 | HSM dwell resets | Candidate change resets dwell_count to 1 | Unit test 12 | — |
| 13 | Dashboard emotion visible | `current_emotion` field shown in Status Panel | Browser | — |
| 14 | Dashboard updates live | Emotion updates without page reload | DevTools WS | — |
| 15 | Break recommendation (tired) | `REQUEST_BREAK` with tired emotion → break text | `curl /api/command` | — |
| 16 | Break recommendation (stressed) | `REQUEST_BREAK` with stressed emotion → study text | `curl /api/command` | — |
| 17 | All unit tests pass | `pytest tests/ -v` → 0 failures | pytest output | — |

---

### 9. Screenshot Checklist

Capture all of these before the final demo:

- [ ] `pytest tests/ -v` terminal output — all 18 tests passing
- [ ] `curl /api/status` JSON output — `current_emotion` showing a valid state
- [ ] Dashboard Status Panel — `current_emotion` visible in active mode
- [ ] Dashboard Command Panel — emotion-aware break suggestion in response field
- [ ] `rostopic hz /camera/image_raw` — showing ~30 Hz (robot lab session)
- [ ] `rosnode list` — showing `/camera_node` (robot lab session)


## Appendix A4: Preserved from `docs/vanness/04_robot_setup.md`

## Robot Setup Guide — Ubuntu VS Code (Vision Layer)

> **Who this is for:** Vanness (Backend-Vision layer), running on the Jupiter robot's Ubuntu machine in VS Code.  
> **Scope:** Everything needed to install, configure, and verify the vision/emotion pipeline on the robot.  
> **Do not run these steps on your dev laptop** — some commands assume ROS Noetic and `/dev/video2` are present.

---

### 0. Prerequisites

Confirm these before starting:

| Requirement | Check command | Expected |
|---|---|---|
| Ubuntu 20.04 | `lsb_release -a` | `Ubuntu 20.04.x LTS` |
| ROS Noetic | `rosversion -d` | `noetic` |
| Python 3.8 exactly | `python3 --version` | `Python 3.8.x` — ROS Noetic requires 3.8 |
| Git | `git --version` | any version |
| Camera device | `ls /dev/video*` | `/dev/video2` present |

If ROS Noetic is not installed, stop — it must be installed by the lab administrator before proceeding.

---

### 1. Pull Latest Code

The repository is already open in VS Code. Before running anything, pull the latest changes from `main`:

```bash
git fetch origin
git checkout main
git pull origin main
```

> If you are still on a feature branch before the merge, switch to `main` first — all vision/emotion code has been merged in.

---

### 2. Build the ROS Catkin Workspace

> Run this once per session (or whenever ROS package files change).

```bash
## From project root
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash
```

Verify build succeeded — no red errors in the output. The last line should be:
```
[100%] Built target <package>
```

---

### 3. Create the Python Virtual Environments

Two venvs are required. Vision deps (`numpy`, `opencv`, `tensorflow`) conflict with the backend's `typing-extensions` — they use separate venvs.

```bash
## Backend venv (for running main.py)
cd backend
python3 -m venv .venv

## Bootstrap a fresh pip — the bundled pip on this machine is broken due to a system OpenSSL issue
wget -O /tmp/get-pip.py https://bootstrap.pypa.io/pip/3.8/get-pip.py
.venv/bin/python3 /tmp/get-pip.py

source .venv/bin/activate
```

Your prompt should now show `(.venv)`.

```bash
## Vision venv (for tests and TensorFlow inference) — separate terminal
cd backend
python3 -m venv .venv-vision
```

---

### 4. Install Python Dependencies

#### Backend venv (`.venv`)

```bash
## Confirm you are inside backend/ with (.venv) active
pip install --upgrade pip
pip install -r requirements.txt

## rospkg is not bundled with ROS Noetic — install it in the venv:
pip install rospkg
```

This installs the backend/runtime dependencies for FastAPI, ROS bridge, ASR/TTS integration, and tests. Keep TensorFlow/OpenCV vision dependencies in `.venv-vision` unless you intentionally want to test a combined environment.

#### Vision venv (`.venv-vision`)

```bash
.venv-vision/bin/pip install --upgrade pip
.venv-vision/bin/pip install -r requirements-vision.txt
.venv-vision/bin/pip install pytest pydantic
```

`requirements-vision.txt` installs:
- `numpy>=1.24,<1.25` — EMA probability smoothing (numpy 1.25 dropped Python 3.8)
- `opencv-python-headless>=4.8` — face detection, headless avoids conflict with ROS system `python3-opencv`
- `tensorflow>=2.13,<2.14` — Mini-Xception emotion CNN (TF 2.14 dropped Python 3.8)

> **Note:** `tensorflow` is ~500 MB. This step will take several minutes on first install.

Verify vision venv after install:

```bash
.venv-vision/bin/python3 -c "import numpy; import cv2; import tensorflow as tf; print('numpy', numpy.__version__); print('cv2', cv2.__version__); print('tf', tf.__version__)"
```

All three must print a version number. Numpy must be `1.24.x`, TensorFlow `2.13.x`.

---

### 5. Run the Unit Tests

```bash
## From backend/ — use .venv-vision (tests import numpy via emotion_fusion)
.venv-vision/bin/python3 -m pytest tests/ -v
```

Expected: **18 passed, 0 failed**.

If any test fails, stop and fix it before proceeding — a failing test means the emotion pipeline has a bug.

---

### 6. Download CNN Model Files (Phase 2 — Real Emotion Detection)

> Skip this section if running mock mode only for the demo.

Place all model files in `backend/models/`. This directory is gitignored — files must be downloaded manually on each machine.

```bash
mkdir -p backend/models
```

#### 6a. OpenCV DNN Face Detector (ResNet-SSD)

```bash
cd backend/models

## Prototxt (network architecture)
wget https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt

## Caffemodel (pre-trained weights, ~10 MB)
wget https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel
```

#### 6b. Mini-Xception Emotion CNN

The model is `fer2013_mini_XCEPTION.102-0.66.hdf5` from the `oarriaga/face_classification` repository — the standard FER2013-trained Mini-Xception model (~580 KB). It outputs 7 emotion classes (Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral), which our `MAPPING_MATRIX` in `emotion_detector.py` remaps to the 5 Juno states.

```bash
cd backend/models

## Download the model (~580 KB)
wget https://github.com/oarriaga/face_classification/raw/master/trained_models/emotion_models/fer2013_mini_XCEPTION.102-0.66.hdf5

## Rename to the expected filename
mv fer2013_mini_XCEPTION.102-0.66.hdf5 emotion_model.h5
```

> `.hdf5` and `.h5` are the same file format — the rename is just for consistency with the default `EMOTION_MODEL_PATH`.  
> If `wget` is slow, download the file in a browser and `scp` it to the robot at `backend/models/emotion_model.h5`.

Verify all three files are present:

```bash
ls -lh backend/models/
## Expected:
## deploy.prototxt                          (~28 KB)
## res10_300x300_ssd_iter_140000.caffemodel (~10 MB)
## emotion_model.h5                         (~580 KB)
```

---

### 7. Enable Real CNN in the Backend

By default `app.py` instantiates `EmotionDetector()` with `use_real=False` (mock mode).  
To switch to real CNN inference, coordinate with **Jon** to update `app.py` line 46:

```python
## Current (mock mode — default)
emotion_detector = EmotionDetector()

## Change to (real CNN mode — requires model files from §6)
emotion_detector = EmotionDetector(use_real=True)
```

The model path defaults to `models/emotion_model.h5`. To override:

```bash
export EMOTION_MODEL_PATH=/path/to/your/emotion_model.h5
```

If model files are missing or fail to load, `EmotionDetector` falls back to mock automatically and logs:
```
[EmotionDetector] Model load failed: ... Falling back to mock.
```

---

### 8. Run the Full System

Open **four terminals** in VS Code (use the split terminal feature). Source order matters in each terminal.

#### Terminal 1 — roscore

```bash
source /opt/ros/noetic/setup.bash
roscore
```

Leave running. Do not close.

#### Terminal 2 — ROS Nodes (camera, microphone, TTS)

```bash
source /opt/ros/noetic/setup.bash
cd /path/to/WID3010-JunoAssist
source devel/setup.bash
roslaunch juno_bringup juno_robot.launch
```

Confirm camera node started:
```bash
## In a separate terminal
source /opt/ros/noetic/setup.bash
rostopic hz /camera/image_raw
## Expected: ~30 Hz
```

#### Terminal 3 — FastAPI Backend (ROS mode)

```bash
source /opt/ros/noetic/setup.bash
cd /path/to/WID3010-JunoAssist
source devel/setup.bash
cd backend
source .venv/bin/activate
## Expose ROS Python packages to the venv (rospy, cv_bridge, sensor_msgs, etc.)
unset PYTHONPATH
source /opt/ros/noetic/setup.bash
source devel/setup.bash
export PYTHONPATH=/opt/ros/noetic/lib/python3/dist-packages:$PYTHONPATH
export JUNO_ROBOT_INTERFACE=ros
python3 main.py
```

Expected log output:
```
INFO:     Application startup complete.
```

The `[EmotionDetector] Model load failed` warning is normal if model files are not downloaded — falls back to mock automatically. TF-TRT and CUDA warnings are also safe to ignore (CPU-only machine).

#### Terminal 4 — Dashboard

```bash
cd /path/to/WID3010-JunoAssist/dashboard
npm run dev
```

Open `http://localhost:5173` in the browser.

---

### 9. Verification Checklist

Run through this before each demo session.

```bash
## 1. Camera topic is live at 30 Hz
rostopic hz /camera/image_raw

## 2. Camera node is registered
rosnode list | grep camera_node

## 3. Backend started cleanly
curl -s http://localhost:8000/api/status | python3 -m json.tool
## Look for: "current_emotion": (any value — not an error)

## 4. Wake JUNO and confirm active mode
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "Hey, John"}'

curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "Yes"}'

## 5. Emotion field is not "unknown" in active mode
curl -s http://localhost:8000/api/status | python3 -m json.tool
## "current_emotion" must be one of: happy / neutral / tired / stressed / frustrated

## 6. Break recommendation responds with emotion-aware text
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "I need a break"}'
```

---

### 10. Common Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: rospy` | PYTHONPATH missing ROS noetic path | `unset PYTHONPATH && source /opt/ros/noetic/setup.bash && source devel/setup.bash && export PYTHONPATH=/opt/ros/noetic/lib/python3/dist-packages:$PYTHONPATH` |
| `ModuleNotFoundError: rospkg` | rospkg not installed in venv | `pip install rospkg` |
| `ModuleNotFoundError: cv_bridge` | PYTHONPATH not set | Same fix |
| `ImportError: cannot import name 'TypeIs' from 'typing_extensions'` | tensorflow install downgraded typing-extensions | `pip install "typing-extensions>=4.12.2"` |
| `ModuleNotFoundError: numpy` | running tests with `.venv` instead of `.venv-vision` | Use `.venv-vision/bin/python3 -m pytest` |
| `ModuleNotFoundError: cv2` | opencv not in vision venv | `.venv-vision/bin/pip install -r requirements-vision.txt` |
| `pip._vendor` crash with OpenSSL error | system pip bundled with broken OpenSSL | Bootstrap fresh pip: `wget -O /tmp/get-pip.py https://bootstrap.pypa.io/pip/3.8/get-pip.py && .venv/bin/python3 /tmp/get-pip.py` |
| `current_emotion: unknown` | Backend not in ACTIVE mode | Send wake phrase + confirmation first |
| `rostopic hz` shows 0 Hz | Camera node not running | Check Terminal 2 for errors; try `camera_device:=/dev/video0` |
| `/dev/video2 not found` | Wrong camera device index | `roslaunch juno_bringup juno_robot.launch camera_device:=/dev/video0` |
| `[EmotionDetector] Model load failed` | Model files missing from `backend/models/` | Follow §6 to download model files |
| `18 passed` but backend crashes | Import error outside test scope | Run `python3 main.py` and read the full traceback |

---

### 11. Environment Variable Reference

| Variable | Default | Purpose |
|---|---|---|
| `JUNO_ROBOT_INTERFACE` | `mock` | Set to `ros` on robot to enable ROS bridge |
| `JUNO_EMOTION_UPDATE_SECONDS` | `3.0` | How often the emotion monitor loop polls the camera (seconds) |
| `EMOTION_MODEL_PATH` | `models/emotion_model.h5` | Path to Mini-Xception `.h5` model file |
| `JUNO_DASHBOARD_URL` | `http://localhost:5173` | Dashboard URL opened by JUNO on activation |
| `JUNO_WAKE_PHRASE` | `hey john` | Wake phrase that activates JUNO |


### Timer cancellation and speech-prioritised emotion update

The timer duration prompt now accepts flexible formats such as `twenty five minutes`, `1h 30m`, `half an hour`, and `2:30`. The user may exit the timer flow by saying `cancel`, `not now`, `skip`, or `never mind`; repeated unclear responses also cancel the pending timer setup. The dashboard Study Timer card provides Pause/Resume and Stop controls, and the active speech flow understands fuzzy timer-control commands such as `pause timer`, `resume timer`, `stop timer`, `end the countdown`, and `cancel the focus session`.

When the user's transcript explicitly states an emotion, such as `I am stressed` or `I feel tired`, the backend treats the speech cue as higher priority than the visual emotion estimate for a short configurable window (`JUNO_SPEECH_EMOTION_OVERRIDE_SECONDS`).

## Switchable JUNO/Ekman Vision Module Update

The dashboard Vision Module now uses the `face_expression` backend by default with `mo-thecreator/vit-Facial-Expression-Recognition`, replacing SmolVLM as the normal emotion classifier. The classifier produces canonical Ekman evidence internally, while the dashboard can switch between JUNO mode (`happy`, `sad`, `tired`, `frustrated`, `stressed`, `neutral`) and Ekman mode display labels (`angry`, `disgusted`, `scared`, `happy`, `sad`, `surprised`, `neutral`) while preserving raw Ekman values (`anger`, `disgust`, `fear`, `happiness`, `sadness`, `surprise`, `neutral`) at any time during the same run. `unknown` is used when the frame or confidence is insufficient. Spoken emotion cues still override camera inference; for example, “I am stressed” is mapped to Ekman `fear` and shown as `stressed` in JUNO mode.

Recommended environment settings:

```bash
JUNO_VISION_BACKEND=face_expression
JUNO_VISION_MODEL_ID=mo-thecreator/vit-Facial-Expression-Recognition
JUNO_VISION_EMOTION_MODE_DEFAULT=juno
JUNO_VISION_REQUIRE_FACE=false
JUNO_VISION_NEUTRAL_UNCERTAIN_CONFIDENCE=0.45
```

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
