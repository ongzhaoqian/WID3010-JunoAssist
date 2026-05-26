# Q3: Develop the Robotics Application on the ROS Workspace

## Overview

JUNO Assist is developed on a ROS Noetic workspace. The application connects physical sensor input (camera and microphone) through a speech-to-text pipeline and text-to-speech output, with a FastAPI backend handling intent classification, schedule management, and timer control. The following documents the ROS packages, APIs, and physical unit testing evidence collected on the Jupiter robot.

---

## ROS Packages

### `perception_pkg`

Handles physical sensor input from the robot.

| Node | Script | Purpose |
|---|---|---|
| `camera_node` | `camera_node.py` | Captures frames from USB camera and publishes to `/camera/image_raw` |
| `microphone_node` | `microphone_node.py` | Captures audio from USB microphone, resamples from 48 kHz to 16 kHz, publishes to `/audio/raw` |

### `language_pkg`

Handles speech-to-text transcription and text-to-speech output.

| Node | Script | Purpose |
|---|---|---|
| `whisper_tiny_transcriber` | `transcriber.py` | Subscribes to `/audio/raw`, runs Whisper Tiny ASR, publishes recognised commands to `/speech/transcript`. Also accepts manual text via `/speech/raw_transcript`. Mutes listening while TTS is active. |
| `juno_tts_node` | `tts_node.py` | Subscribes to `/juno/tts`, speaks response text using espeak in British English, publishes `/juno/tts_done` when speech finishes |

### `juno_bringup`

Contains the `juno_robot.launch` launch file that starts all four robot-side nodes with configured parameters.

---

## ROS API Design

### Topics, Publishers, and Subscribers

| Topic | Message Type | Publisher | Subscriber | Purpose |
|---|---|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | `camera_node` | `juno_backend_bridge` (backend) | Camera frames for dashboard stream and backend vision processing |
| `/audio/raw` | `std_msgs/Float32MultiArray` | `microphone_node` | `whisper_tiny_transcriber` | Raw microphone audio samples for ASR processing |
| `/speech/raw_transcript` | `std_msgs/String` | Manual / external tool | `whisper_tiny_transcriber` | Fallback text injection for testing without microphone input |
| `/speech/transcript` | `std_msgs/String` | `whisper_tiny_transcriber` | `juno_backend_bridge` (backend) | Recognised command text forwarded to backend decision pipeline |
| `/juno/tts` | `std_msgs/String` | `juno_backend_bridge` (backend) | `juno_tts_node` | Backend response text to be spoken by the robot |
| `/juno/tts_done` | `std_msgs/String` | `juno_tts_node` | `whisper_tiny_transcriber` | Signals that speech has finished so transcriber resumes listening |
| `/juno/tts_stop` | `std_msgs/String` | `juno_backend_bridge` (backend) | `juno_tts_node` | Interrupts ongoing TTS speech |
| `/juno/led_state` | `std_msgs/String` | `juno_backend_bridge` (backend) | Robot LED adapter | Optional robot state feedback via LED |

### Sensor-to-Response Pipeline

```
[Microphone] --> /audio/raw --> [whisper_tiny_transcriber] --> /speech/transcript --> [juno_backend_bridge]
                                        ^                                                       |
                               /juno/tts_done                                             /juno/tts
                                        |                                                       |
                               [juno_tts_node] <----------------------------------------------|

[Camera] --> /camera/image_raw --> [juno_backend_bridge] --> (vision processing + dashboard stream)

[Manual input] --> /speech/raw_transcript --> [whisper_tiny_transcriber] --> /speech/transcript
```

---

## Unit Testing: ROS APIs on Physical Robot

All tests were executed on the Jupiter robot (Ubuntu, ROS Noetic 1.16.0). Evidence collected via terminal output.

### Step 1: Launch ROS Master and All Nodes

**Command:**
```bash
source /opt/ros/noetic/setup.bash
roscore
```

```bash
cd ~/Desktop/WID3010-JunoAssist
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch juno_bringup juno_robot.launch
```

**Output:**
```
NODES
  /
    camera_node (perception_pkg/camera_node.py)
    juno_tts_node (language_pkg/tts_node.py)
    microphone_node (perception_pkg/microphone_node.py)
    whisper_tiny_transcriber (language_pkg/transcriber.py)

process[camera_node-1]: started with pid [13767]
process[microphone_node-2]: started with pid [13768]
process[whisper_tiny_transcriber-3]: started with pid [13769]
process[juno_tts_node-4]: started with pid [13770]
[INFO]: JUNO TTS node subscribed to /juno/tts, stop topic=/juno/tts_stop, done topic=/juno/tts_done, backend=espeak, rate=165
[INFO]: JUNO transcriber ready. Primary: openai/whisper-tiny | Fallback: moonshine/base
[INFO]: Audio input topic: /audio/raw
[INFO]: Output transcript topic: /speech/transcript
[INFO]: Manual/external transcript input topic: /speech/raw_transcript
[INFO]: TTS mute topics: /juno/tts -> /juno/tts_done
[INFO]: Mic node publishing FLOAT32 audio to /audio/raw from device 0 (USB Device 0x46d:0x825: Audio (hw:0,0)), 48000 Hz -> ~16000 Hz
[INFO]: Camera node started. device=/dev/video2 topic=/camera/image_raw requested=640x480@30.0fps
[INFO]: Whisper ASR loaded successfully.
```

All four nodes started successfully. Camera connected at `/dev/video2`, microphone connected as USB Device `0x46d:0x825`.

---

### Step 2: Verify All Nodes Running

**Command:**
```bash
rosnode list
```

**Output:**
```
/camera_node
/juno_tts_node
/microphone_node
/rosout
/whisper_tiny_transcriber
```

All four application nodes are active: `camera_node`, `microphone_node`, `whisper_tiny_transcriber`, and `juno_tts_node`.

---

### Step 3: Verify All Topics Available

**Command:**
```bash
rostopic list
```

**Output:**
```
/audio/raw
/camera/image_raw
/juno/tts
/juno/tts_done
/juno/tts_stop
/rosout
/rosout_agg
/speech/raw_transcript
/speech/transcript
```

All eight JUNO application topics are present and available.

---

### Step 4: Unit Test — Camera API (`/camera/image_raw`)

**Command:**
```bash
rostopic hz /camera/image_raw
```

**Output:**
```
average rate: 23.102
average rate: 23.610
average rate: 23.776
average rate: 23.855
average rate: 23.924
average rate: 23.945
average rate: 23.951
    min: 0.037s max: 0.086s std dev: 0.00408s window: 173
```

**Result:** `camera_node` publishes at ~24 Hz (configured at 30 fps; actual rate limited by USB camera hardware). Topic is publishing sensor data continuously.

**Example input/output:**
- Input: USB camera at `/dev/video2`, 640×480 resolution
- Output: `sensor_msgs/Image` frames published to `/camera/image_raw` at ~24 Hz

---

### Step 5: Unit Test — Microphone API (`/audio/raw`)

**Command:**
```bash
rostopic hz /audio/raw
```

**Output:**
```
average rate: 45.641
average rate: 44.428
average rate: 44.538
average rate: 44.509
average rate: 44.121
average rate: 44.310
    min: 0.000s max: 0.072s std dev: 0.01872s window: 276
```

**Result:** `microphone_node` publishes at ~44 Hz. Topic is continuously streaming audio samples.

**Example input/output:**
- Input: USB microphone `0x46d:0x825`, captured at 48 kHz, downsampled to 16 kHz
- Output: `std_msgs/Float32MultiArray` audio frames published to `/audio/raw` at ~44 Hz

---

### Step 6: Unit Test — Speech Transcription API (`/speech/transcript`)

#### 6a: Verify live ASR transcription

With `rostopic echo /speech/transcript` running, speech near the microphone was transcribed and published in real time:

```
data: "Hello test test"
data: "test test"
data: "I'm speaking and speaking."
data: "and speaking and speaking."
```

**Result:** `whisper_tiny_transcriber` is consuming `/audio/raw`, running Whisper Tiny ASR, and publishing recognised text to `/speech/transcript`.

#### 6b: Unit test with manual transcript injection (`/speech/raw_transcript`)

Commands injected via `rostopic pub`:
```bash
rostopic pub -1 /speech/raw_transcript std_msgs/String "data: 'Hey, John'"
rostopic pub -1 /speech/raw_transcript std_msgs/String "data: 'Yes'"
rostopic pub -1 /speech/raw_transcript std_msgs/String "data: 'What is my schedule today?'"
rostopic pub -1 /speech/raw_transcript std_msgs/String "data: 'Set a 25 minute timer'"
```

These injected messages appeared on `/speech/transcript` and were received by the backend:

```
data: "Hey, John"
data: "Yes"
data: "What is my schedule today?"
data: "Set a 25 minute timer"
```

**Result:** `/speech/raw_transcript` manual fallback correctly routes text into the transcription pipeline without requiring microphone input. This is used for testing and as a recovery mechanism when ASR is unavailable.

**Example input/output:**
- Input: text published to `/speech/raw_transcript` or audio captured on `/audio/raw`
- Output: recognised command string published to `/speech/transcript`

#### 6c: End-to-end flow — transcript → backend decision → `/juno/tts` response

With the backend running in ROS mode, the same three commands were injected. The full pipeline was verified by monitoring `/juno/tts` simultaneously:

**Injected via `rostopic pub`:**
```
"Hey, John"   →   "Yes"   →   "What is my schedule today?"
```

**Observed on `/juno/tts` (backend response output):**
```
data: "Wake command received. Would you like me to come online? Say yes to confirm."
---
data: "JUNO Assist is now online. Opening your dashboard."
---
data: "What can I help you with?"
---
data: "Your current scheduled items are: Robotics assignment submission (assignment,
  high priority) on 12 May, 2026 at 23:59; AI quiz revision (study, medium priority)
  on 13 May, 2026 at 20:00; Group project discussion (meeting, medium priority)
  on 14 May, 2026 at 14:00; Vanness (study, medium priority) on 28 May, 2026 at
  09:09; omg (study, medium priority) on 28 May, 2026 at 09:09."
```

**Result:** Complete end-to-end sensor-to-decision pipeline verified on the physical robot:
1. `"Hey, John"` → backend detects wake word → publishes confirmation prompt to `/juno/tts` → robot speaks
2. `"Yes"` → backend confirms activation → publishes online confirmation + opens dashboard
3. `"What is my schedule today?"` → backend retrieves calendar data → publishes full schedule response to `/juno/tts` → robot speaks schedule aloud

The backend decision pipeline (wake word detection → intent classification → schedule retrieval → TTS response) is fully connected to the ROS topic layer.

---

### Step 7: Unit Test — TTS API (`/juno/tts` and `/juno/tts_done`)

**Command:**
```bash
rosrun language_pkg tts_test_publisher.py "Hello, I am JUNO and my speech node is working."
```

**Node output:**
```
[INFO]: Published test TTS to /juno/tts: Hello, I am JUNO and my speech node is working.
```

**`/juno/tts` topic received:**
```
data: "Hello, I am JUNO and my speech node is working."
```

**TTS node log:**
```
[INFO]: Queued JUNO speech from /juno/tts: Hello, I am JUNO and my speech node is working.
[INFO]: TTS started — transcription muted, audio buffer cleared.
[INFO]: JUNO says in British English: Hello, I am JUNO and my speech node is working.
[INFO]: Trying TTS command: espeak-ng -v en-gb
[INFO]: Published /juno/tts_done after TTS attempt
```

**`/juno/tts_done` topic received:**
```
data: "done"
```

**Result:** `juno_tts_node` received the message on `/juno/tts`, muted the transcriber, spoke the text aloud using espeak British English, and published `"done"` to `/juno/tts_done` to resume listening. The full TTS cycle completed successfully.

**Example input/output:**
- Input: text string published to `/juno/tts`
- Output: robot speaks text; `"done"` published to `/juno/tts_done` after speech ends

---

### Step 8: Unit Test — Backend ROS Bridge (`juno_backend_bridge`)

**Command:**
```bash
cd ~/Desktop/WID3010-JunoAssist/backend
source ../devel/setup.bash
source .venv/bin/activate
export JUNO_ROBOT_INTERFACE=ros
export JUNO_DASHBOARD_URL=http://localhost:5173
python main.py
```

**Output:**
```
[INFO]: JUNO backend ROS bridge is ready. Camera topic=/camera/image_raw, TTS topic=/juno/tts, TTS stop topic=/juno/tts_stop, LED topic=/juno/led_state
INFO:     Started server process [14710]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
[INFO]: Backend received transcript: You're so good.
[INFO]: Backend received transcript: Let's go!
[INFO]: Backend received transcript: Okay, here we go.
...
```

**Result:** Backend started in ROS mode (`JUNO_ROBOT_INTERFACE=ros`). The `juno_backend_bridge` node initialised, subscribed to `/speech/transcript` and `/camera/image_raw`, and started receiving transcripts from the transcriber. FastAPI server listening on port 8000.

**Example input/output:**
- Input: transcript received on `/speech/transcript`
- Output: backend processes intent, publishes response to `/juno/tts`; LED state optionally published to `/juno/led_state`

---

### Step 9: Dashboard

**Command:**
```bash
cd ~/Desktop/WID3010-JunoAssist/dashboard
npm install
npm run dev
```

**Output:**
```
> juno-assist-dashboard@0.1.0 dev
> vite --host 0.0.0.0

  VITE v6.4.2  ready in 463 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.199.58:5173/
```

**Result:** Dashboard running and accessible at `http://localhost:5173/`. Network accessible at `http://192.168.199.58:5173/`.

---

### Step 10: Verify Publisher/Subscriber Connections (`rostopic info`)

Run with both `roslaunch` and backend active to show all connections.

**`/camera/image_raw`:**
```
Type: sensor_msgs/Image

Publishers:
 * /camera_node (http://jupiter:36061/)

Subscribers:
 * /juno_backend_bridge_26442_1779765961831 (http://jupiter:32817/)
```

**`/audio/raw`:**
```
Type: std_msgs/Float32MultiArray

Publishers:
 * /microphone_node (http://jupiter:34525/)

Subscribers:
 * /whisper_tiny_transcriber (http://jupiter:37309/)
```

**`/speech/transcript`:**
```
Type: std_msgs/String

Publishers:
 * /whisper_tiny_transcriber (http://jupiter:37309/)

Subscribers:
 * /juno_backend_bridge_26442_1779765961831 (http://jupiter:32817/)
```

**`/juno/tts`:**
```
Type: std_msgs/String

Publishers:
 * /juno_backend_bridge_26442_1779765961831 (http://jupiter:32817/)

Subscribers:
 * /juno_tts_node (http://jupiter:43231/)
 * /whisper_tiny_transcriber (http://jupiter:37309/)
```

**`/juno/tts_done`:**
```
Type: std_msgs/String

Publishers:
 * /juno_tts_node (http://jupiter:43231/)

Subscribers:
 * /whisper_tiny_transcriber (http://jupiter:37309/)
```

**Result:** All publisher/subscriber connections verified. `whisper_tiny_transcriber` subscribes to `/juno/tts` to mute listening during speech, and to `/juno/tts_done` to resume after speech ends — confirming the TTS feedback loop is correctly wired.

---

### Step 11: Verify Backend Status API

```bash
curl http://localhost:8000/api/status
```

**Output:**
```json
{
  "mode": "idle",
  "current_emotion": "sadness",
  "last_response": "I am currently in sleep mode. Wake me by saying Hey, John.",
  "timer_remaining_seconds": 0,
  "active_timer_label": null,
  "awaiting_timer_duration": false,
  "emotion_source": "speech",
  "emotion_confidence": 0.93,
  "camera_enabled": false,
  "vision_model_enabled": false,
  "music": {"status": "stopped", "provider": "spotify"}
}
```

**Result:** FastAPI backend responding on port 8000. Status shows `mode: idle` (sleep mode), emotion tracking active with 93% confidence, timer and camera subsystems ready. Backend is fully operational.

---

## Summary of ROS API Unit Testing Results

| API / Topic | Test Method | Result |
|---|---|---|
| `/camera/image_raw` | `rostopic hz` | PASS — ~24 Hz, continuous frames |
| `/audio/raw` | `rostopic hz` | PASS — ~44 Hz, continuous audio |
| `/speech/transcript` (live ASR) | `rostopic echo` with speech near mic | PASS — Whisper Tiny transcribing in real time |
| `/speech/raw_transcript` (manual fallback) | `rostopic pub` injection | PASS — injected text routed to `/speech/transcript` |
| `/juno/tts` | `tts_test_publisher.py` + `rostopic echo` | PASS — message received, robot spoke aloud |
| `/juno/tts_done` | `rostopic echo` after TTS | PASS — `"done"` published after speech finished |
| `juno_backend_bridge` | backend in ROS mode | PASS — bridge ready, transcripts received, server on port 8000 |
| End-to-end pipeline | `rostopic pub` → `rostopic echo /juno/tts` with backend live | PASS — wake word, confirmation, and schedule query all produced correct backend responses on `/juno/tts` |
| Publisher/subscriber connections | `rostopic info` for all 5 main topics | PASS — all publishers and subscribers correctly wired |
| Backend status API | `curl http://localhost:8000/api/status` | PASS — JSON response with mode, emotion, timer, and music state |
| Dashboard | `npm run dev` | PASS — running on localhost:5173 |

---

## Conclusion

The three ROS packages work together as a complete sensor-to-response pipeline. `perception_pkg` provides `camera_node` and `microphone_node`, which publish raw sensor data to `/camera/image_raw` and `/audio/raw` respectively. `language_pkg` provides `whisper_tiny_transcriber`, which consumes `/audio/raw`, performs Whisper Tiny ASR, and publishes recognised commands to `/speech/transcript`. The `/speech/raw_transcript` topic provides a manual fallback for testing without microphone input. `juno_tts_node` subscribes to `/juno/tts`, speaks the response using espeak British English, and publishes `/juno/tts_done` to signal the transcriber to resume listening — preventing the robot from transcribing its own speech. The backend ROS bridge (`juno_backend_bridge`) connects the robot-side ROS topics to the FastAPI decision pipeline: it subscribes to `/speech/transcript` and `/camera/image_raw`, processes input through wake-word detection, intent classification, and schedule/timer logic, then publishes the response back to `/juno/tts`. Each ROS API was verified on the physical Jupiter robot using `rostopic hz`, `rostopic echo`, `rosnode list`, `rostopic list`, manual transcript injection via `rostopic pub`, and a TTS test command.
