# ROS Integration Guide for JUNO Assist and Jupiter Robot Code

This guide explains how the FastAPI backend, React dashboard, and Jupiter Robot ROS code are integrated after replacing the previous heavy language-model path with Whisper Tiny ASR.

## 1. Current ROS Topics

| Node | Topic | Message Type | Purpose |
|---|---|---|---|
| `camera_node.py` | `/camera/image_raw` | `sensor_msgs/Image` | Publishes Jupiter/laptop camera frames. |
| `microphone_node.py` | `/audio/raw` | `std_msgs/Float32MultiArray` | Publishes mono float microphone samples. |
| `transcriber.py` | `/speech/transcript` | `std_msgs/String` | Runs `openai/whisper-tiny` ASR and publishes recognised text. |
| External ASR or `example_transcriptor.py` | `/speech/raw_transcript` | `std_msgs/String` | Manual/external transcript fallback; relayed to `/speech/transcript`. |
| `tts_node.py` | `/juno/tts` | `std_msgs/String` | Speaks backend responses using a British English voice where available. |
| `tts_node.py` | `/juno/tts_done` | `std_msgs/String` | Signals that TTS has finished so STT can resume. |
| Backend ROS bridge | `/juno/led_state` | `std_msgs/String` | Optional LED/status feedback. |

## 2. Integration Flow

```text
User speech
  ↓
microphone_node.py publishes /audio/raw
  ↓
transcriber.py uses openai/whisper-tiny
  ↓
/speech/transcript
  ↓
FastAPI backend RosJupiterInterface subscribes /speech/transcript
  ↓
Backend runs the same command pipeline used by the dashboard
  ↓
Backend publishes British English response to /juno/tts
  ↓
tts_node.py speaks the response using en_GB/UK voice where available
```

Vision flow:

```text
Jupiter camera
  ↓
camera_node.py publishes /camera/image_raw
  ↓
FastAPI backend RosJupiterInterface subscribes /camera/image_raw
  ↓
EmotionDetector receives latest frame
  ↓
Dashboard updates current emotion via WebSocket
```

## 3. Why Whisper Tiny Replaces the Heavy Local Model

The previous Malaysian Llama + LoRA path was too large for the local machine connected to the robot. Whisper Tiny is used only for speech-to-text or speech translation. It does not replace backend intent logic or response generation.

The architecture stays intact because `/speech/transcript` remains the backend-facing topic.

## 4. Running the Integrated System

### Terminal 1: ROS Core

```bash
roscore
```

### Terminal 2: Catkin Workspace

From the project root:

```bash
catkin_make
source devel/setup.bash
pip install -r src/language_pkg/requirements-asr.txt
roslaunch juno_bringup juno_robot.launch
```

This launches:

- camera publisher
- microphone publisher
- Whisper Tiny transcriber node
- British-English TTS node

### Terminal 3: Backend in ROS Mode

```bash
cd backend
source ../devel/setup.bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export JUNO_ROBOT_INTERFACE=ros
export JUNO_DASHBOARD_URL=http://localhost:5173
python main.py
```

If the dashboard is opened from another laptop, replace `localhost` with the robot IP:

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

### Terminal 5: Manual Speech Input Fallback

```bash
source devel/setup.bash
rosrun language_pkg example_transcriptor.py
```

Then type commands such as:

```text
Hey, Juno
Yes
What is my schedule today?
I feel tired, what should I do?
```

## 5. Testing the ROS Bridge

Check camera topic:

```bash
rostopic list
rostopic echo /camera/image_raw/header
```

Check raw audio topic:

```bash
rostopic echo /audio/raw
```

Check recognised speech transcript topic:

```bash
rostopic echo /speech/transcript
```

Manually test the fallback transcript path:

```bash
rostopic pub /speech/raw_transcript std_msgs/String "data: 'Hey, Juno'"
rostopic pub /speech/raw_transcript std_msgs/String "data: 'Yes'"
rostopic pub /speech/raw_transcript std_msgs/String "data: 'What is my schedule today?'"
```

Check backend speech output:

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
2. If `/juno/tts` receives text but there is no audio, check the `juno_tts_node` terminal output and ensure either `pyttsx3`, `espeak-ng`, or `espeak` is installed.
3. If the first response is sometimes missed, keep `JUNO_TTS_PUBLISHER_WAIT_SECONDS=2.0`; the backend now waits for the TTS subscriber and retries the publish.

## 6. What Was Changed

### `backend/src/robot/ros_jupiter_interface.py`

Keeps the same topic boundary but now uses a latched `/juno/tts` publisher, waits briefly for the TTS subscriber, retries publishing, and logs each speech message. This fixes the case where STT reaches the backend but the backend response is dropped before `tts_node.py` connects. This file still subscribes to:

- `/speech/transcript`
- `/camera/image_raw`

It publishes to:

- `/juno/tts`
- `/juno/led_state`

### `backend/src/api/app.py`

The command processing remains centralised in `process_command_text()`. Whisper Tiny transcribes speech before it reaches this backend, and the backend continues to use deterministic intent classification and response handling.

### `backend/src/core/config.py`

Adds `JUNO_ASR_*` settings for the robot-friendly ASR path. Text LLM settings remain available but are disabled and blank by default.

### `src/language_pkg/scripts/transcriber.py`

Runs Hugging Face `openai/whisper-tiny` on `/audio/raw` windows and publishes recognised text to `/speech/transcript`. It now mirrors the working `anas` branch logic: buffered audio windows, RMS/VAD filtering, TTS mute on `/juno/tts`, resume on `/juno/tts_done`, and manual `/speech/raw_transcript` fallback.

### `src/language_pkg/scripts/tts_node.py`

Selects a British English voice in `pyttsx3` where possible, falls back to `espeak-ng`/`espeak`, speaks on a single worker thread, and publishes `/juno/tts_done` once speech output finishes. It also publishes `/juno/tts_done` after failed speech attempts so the STT node is not left muted.

### `src/language_pkg/scripts/tts_test_publisher.py`

A one-command diagnostic publisher for `/juno/tts`, useful for testing robot speech without starting the backend command pipeline.

### `src/juno_bringup/launch/juno_robot.launch`

Starts the same robot-facing ROS package structure while replacing the old language normaliser with `whisper_tiny_transcriber`.

## 7. Feasible Demo Script

1. Launch ROS nodes.
2. Start backend with `JUNO_ROBOT_INTERFACE=ros`.
3. Start dashboard.
4. Say or publish:

```text
Hey, Juno
```

5. JUNO replies:

```text
Are you sure you would like to power Juno on? Answer yes if you do, else ignore.
```

6. Say or publish:

```text
Yes
```

7. JUNO opens the dashboard and enters active mode.
8. Try:

```text
What is my schedule today?
Set a 25 minute timer.
I feel tired today, how should I start studying?
Play relaxing music.
Juno, go to sleep.
```

## 8. Recommended Course Scope

For the undergraduate robotics course, keep the final integration scope to:

- ROS camera and microphone input
- Whisper Tiny or manual transcript fallback
- backend command handling
- dashboard visual feedback
- British-English TTS output
- mock or lightweight emotion estimate

Avoid depending on a large cloud or local LLM during the live robot demo.
