# ROS Integration Guide for JUNO Assist and Jupiter Robot

This guide explains how the FastAPI backend, React dashboard, and Jupiter Robot ROS nodes are integrated. Speech recognition uses `openai/whisper-tiny` as the primary ASR engine, with `moonshine/base` (via `moonshine-onnx`) as an automatic fallback if Whisper fails to load.

## 1. Current ROS Topics

| Node | Topic | Message Type | Purpose |
|---|---|---|---|
| `camera_node.py` | `/camera/image_raw` | `sensor_msgs/Image` | Publishes Jupiter/laptop camera frames. |
| `microphone_node.py` | `/audio/raw` | `std_msgs/Float32MultiArray` | Publishes mono float32 microphone samples at 16 kHz. |
| `transcriber.py` | `/speech/transcript` | `std_msgs/String` | Runs ASR (Whisper primary, Moonshine fallback) and publishes recognised text. |
| External ASR or `example_transcriptor.py` | `/speech/raw_transcript` | `std_msgs/String` | Manual/external transcript fallback; relayed to `/speech/transcript`. |
| `tts_node.py` | `/juno/tts` | `std_msgs/String` | Speaks backend responses using British English voice where available. |
| `tts_node.py` | `/juno/tts_done` | `std_msgs/String` | Published after TTS finishes; transcriber resumes listening. |
| Backend ROS bridge | `/juno/led_state` | `std_msgs/String` | Optional LED/status feedback. |

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
EmotionDetector receives latest frame
  ↓
Dashboard updates current emotion via WebSocket
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

## 5. Running the Integrated System

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

- `camera_node.py` — camera publisher
- `microphone_node.py` — microphone publisher (device resolved by `JUNO_MIC_DEVICE_NAME`, 48 kHz → 16 kHz)
- `transcriber.py` — Whisper primary / Moonshine fallback ASR
- `tts_node.py` — British English TTS with `/juno/tts_done` signal

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

## 6. Testing

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

Check backend ASR/AI status:

```bash
curl http://localhost:8000/api/ai/status
```

## 7. Key Source Files

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

## 8. Demo Script

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

## 9. Recommended Scope for Course Demo

- ROS camera and microphone input
- Whisper Tiny ASR with Moonshine fallback
- Manual transcript fallback via `example_transcriptor.py`
- Backend deterministic intent handling
- Dashboard visual feedback
- British English TTS output
- Lightweight emotion estimate

Avoid depending on a large cloud or local LLM during the live robot demo.
