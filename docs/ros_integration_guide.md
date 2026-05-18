# ROS Integration Guide for JUNO Assist and Jupiter Robot Code

This guide explains how the FastAPI backend, React dashboard, and Jupiter Robot ROS code are integrated.

## 1. Current ROS Topics

The attached Jupiter Robot code provides these robot-side streams:

| Node | Topic | Message Type | Purpose |
|---|---|---|---|
| `camera_node.py` | `/camera/image_raw` | `sensor_msgs/Image` | Publishes Jupiter camera frames. |
| `microphone_node.py` | `/audio/raw` | `std_msgs/Float32MultiArray` | Publishes microphone audio samples. |
| `transcriber.py` | `/speech/transcript` | `std_msgs/String` | Publishes recognised speech text. |
| `tts_node.py` | `/juno/tts` | `std_msgs/String` | Speaks backend responses. |
| Backend ROS bridge | `/juno/led_state` | `std_msgs/String` | Optional LED/status feedback. |

## 2. Integration Flow

```text
User speech
  ↓
microphone_node.py publishes /audio/raw
  ↓
transcriber.py subscribes /audio/raw
  ↓
transcriber.py publishes /speech/transcript
  ↓
FastAPI backend RosJupiterInterface subscribes /speech/transcript
  ↓
Backend runs the same command pipeline used by the dashboard
  ↓
Backend publishes response to /juno/tts
  ↓
tts_node.py speaks the response
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

## 3. Running the Integrated System

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
- Moonshine speech transcriber
- JUNO TTS node

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

## 4. Testing the ROS Bridge

Check camera topic:

```bash
rostopic list
rostopic echo /camera/image_raw/header
```

Check audio topic:

```bash
rostopic echo /audio/raw
```

Check speech transcript topic:

```bash
rostopic echo /speech/transcript
```

Manually test speech command without microphone:

```bash
rostopic pub /speech/transcript std_msgs/String "data: 'Hey, Juno'"
rostopic pub /speech/transcript std_msgs/String "data: 'Yes'"
rostopic pub /speech/transcript std_msgs/String "data: 'What do I have today?'"
```

Check backend speech output:

```bash
rostopic echo /juno/tts
```

## 5. What Was Changed

### `backend/src/robot/ros_jupiter_interface.py`

This file subscribes to:

- `/speech/transcript`
- `/camera/image_raw`

It publishes to:

- `/juno/tts`
- `/juno/led_state`

### `backend/src/api/app.py`

The command processing was centralised into `process_command_text()` so both dashboard commands and ROS speech commands use the same logic.

### `src/language_pkg/scripts/transcriber.py`

Modified so that recognised speech is not only printed, but also published to `/speech/transcript`.

### `src/language_pkg/scripts/tts_node.py`

This file subscribes to `/juno/tts` and speaks backend responses.

### `src/juno_bringup/launch/juno_robot.launch`

This launch file starts the robot-facing ROS nodes.

## 6. Feasible Demo Script

1. Launch ROS nodes.
2. Start backend with `JUNO_ROBOT_INTERFACE=ros`.
3. Start dashboard.
4. Say:

```text
Hey, Juno
```

5. JUNO replies:

```text
Are you sure you would like to power Juno on? Answer yes if you do, else ignore.
```

6. Say:

```text
Yes
```

7. JUNO opens the dashboard and enters active mode.
8. Try:

```text
What do I have today?
Set a 25 minute timer.
What should I do now?
Play relaxing music.
Juno, go to sleep.
```

## 7. Recommended Course Scope

For the undergraduate robotics course, keep the final integration scope to:

- ROS camera and microphone input
- Speech transcript topic
- Backend command reasoning
- Dashboard status display
- TTS response output
- Mock or simple emotion detector first

Avoid making navigation or robot movement the core feature unless required by your lecturer.
