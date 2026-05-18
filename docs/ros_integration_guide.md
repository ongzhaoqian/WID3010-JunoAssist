# ROS Integration Guide for JUNO Assist and Jupiter Robot Code

This guide explains how the FastAPI backend, React dashboard, and Jupiter Robot ROS code are integrated after replacing the Moonshine language path with Malaysian Llama + LoRA text normalisation.

## 1. Current ROS Topics

| Node | Topic | Message Type | Purpose |
|---|---|---|---|
| `camera_node.py` | `/camera/image_raw` | `sensor_msgs/Image` | Publishes Jupiter camera frames. |
| `microphone_node.py` | `/audio/raw` | `std_msgs/Float32MultiArray` | Publishes raw microphone samples for future ASR extensions. |
| External/Jupiter ASR or `example_transcriptor.py` | `/speech/raw_transcript` | `std_msgs/String` | Publishes candidate speech text. |
| `transcriber.py` | `/speech/transcript` | `std_msgs/String` | Publishes British-English normalised transcript text. |
| `tts_node.py` | `/juno/tts` | `std_msgs/String` | Speaks backend responses using a British English voice where available. |
| Backend ROS bridge | `/juno/led_state` | `std_msgs/String` | Optional LED/status feedback. |

## 2. Integration Flow

```text
User speech
  ↓
External/Jupiter ASR, Whisper/Vosk, or manual transcript publisher
  ↓
/speech/raw_transcript
  ↓
transcriber.py normalises Malaysian-context input into standard British English
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

## 3. Why `/audio/raw` Is Not Directly Transcribed by Malaysian Llama

`mesolitica/Malaysian-Llama-3.2-3B-Instruct` is a text model. It can understand and generate text, but it is not an audio ASR model. Therefore, the ROS language pipeline now expects candidate text from an upstream ASR source. For the course demo, the easiest options are:

- Jupiter's built-in ASR, if available;
- Whisper or Vosk publishing candidate text to `/speech/raw_transcript`;
- `rosrun language_pkg example_transcriptor.py` as a manual fallback.

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
roslaunch juno_bringup juno_robot.launch
```

This launches:

- camera publisher
- microphone publisher
- Malaysian Llama language normalisation node
- British-English TTS node

### Terminal 3: Backend in ROS Mode

```bash
cd backend
source ../devel/setup.bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-llm.txt

export JUNO_ROBOT_INTERFACE=ros
export JUNO_DASHBOARD_URL=http://localhost:5173
export JUNO_LLM_ENABLED=true
export JUNO_LLM_MODEL_ID=mesolitica/Malaysian-Llama-3.2-3B-Instruct
export JUNO_LLM_ADAPTER_ID=mackwongyy/malaysian-feedback-lora-5k-data
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
Apa jadual saya hari ini?
Saya rasa penat, apa patut saya buat?
```

## 5. Testing the ROS Bridge

Check camera topic:

```bash
rostopic list
rostopic echo /camera/image_raw/header
```

Check raw transcript input:

```bash
rostopic echo /speech/raw_transcript
```

Check normalised speech transcript topic:

```bash
rostopic echo /speech/transcript
```

Manually test a Malaysian-context command:

```bash
rostopic pub /speech/raw_transcript std_msgs/String "data: 'Apa jadual saya hari ini?'"
```

Manually test the backend speech path:

```bash
rostopic pub /speech/transcript std_msgs/String "data: 'Hey, Juno'"
rostopic pub /speech/transcript std_msgs/String "data: 'Yes'"
rostopic pub /speech/transcript std_msgs/String "data: 'What is my schedule today?'"
```

Check backend speech output:

```bash
rostopic echo /juno/tts
```

## 6. What Was Changed

### `backend/src/robot/ros_jupiter_interface.py`

Unchanged topic boundary. This file still subscribes to:

- `/speech/transcript`
- `/camera/image_raw`

It publishes to:

- `/juno/tts`
- `/juno/led_state`

### `backend/src/api/app.py`

The command processing remains centralised in `process_command_text()`. Before intent classification, the backend can normalise Malaysian-context utterances into British English through `MalaysianInputNormalizer` when the LLM is enabled.

### `backend/src/nlp/llm_client.py`

Loads:

- base model: `mesolitica/Malaysian-Llama-3.2-3B-Instruct`
- adapter: `mackwongyy/malaysian-feedback-lora-5k-data`

The model is lazy-loaded and remains inside the NLP boundary.

### `src/language_pkg/scripts/transcriber.py`

Replaced Moonshine usage. The node now normalises candidate text from `/speech/raw_transcript` and publishes `/speech/transcript`. It does not directly transcribe `/audio/raw` because Malaysian Llama is not an audio model.

### `src/language_pkg/scripts/tts_node.py`

Selects a British English voice in `pyttsx3` where possible and falls back to `espeak -v en-gb`.

### `src/juno_bringup/launch/juno_robot.launch`

Starts the same robot-facing ROS package structure while replacing the old language node role with the Malaysian Llama language normaliser.

## 7. Feasible Demo Script

1. Launch ROS nodes.
2. Start backend with `JUNO_ROBOT_INTERFACE=ros` and `JUNO_LLM_ENABLED=true`.
3. Start dashboard.
4. Publish or say through an ASR source:

```text
Hey, Juno
```

5. JUNO replies:

```text
Are you sure you would like to power Juno on? Answer yes if you do, else ignore.
```

6. Publish or say:

```text
Yes
```

7. JUNO opens the dashboard and enters active mode.
8. Try:

```text
Apa jadual saya hari ini?
Set a 25 minute timer.
Saya rasa blur hari ini, macam mana nak mula study?
Play relaxing music.
Juno, go to sleep.
```

## 8. Recommended Course Scope

For the undergraduate robotics course, keep the final integration scope to:

- ROS camera and microphone input
- Transcript topic using ASR/manual fallback
- Malaysian-context input normalisation
- Backend command reasoning
- British-English TTS output
- Dashboard status display
- Mock or simple emotion detector first

Avoid making navigation or robot movement the core feature unless required by your lecturer.
