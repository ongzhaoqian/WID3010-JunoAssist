# Robot Setup Guide — Ubuntu VS Code (Vision Layer)

> **Who this is for:** Vanness (Backend-Vision layer), running on the Jupiter robot's Ubuntu machine in VS Code.  
> **Scope:** Everything needed to install, configure, and verify the vision/emotion pipeline on the robot.  
> **Do not run these steps on your dev laptop** — some commands assume ROS Noetic and `/dev/video2` are present.

---

## 0. Prerequisites

Confirm these before starting:

| Requirement | Check command | Expected |
|---|---|---|
| Ubuntu 20.04 | `lsb_release -a` | `Ubuntu 20.04.x LTS` |
| ROS Noetic | `rosversion -d` | `noetic` |
| Python 3.8+ | `python3 --version` | `Python 3.8.x` or higher |
| Git | `git --version` | any version |
| Camera device | `ls /dev/video*` | `/dev/video2` present |

If ROS Noetic is not installed, stop — it must be installed by the lab administrator before proceeding.

---

## 1. Get the Code

```bash
# If first time on this machine — clone the repo
git clone https://github.com/ongzhaoqian/WID3010-JunoAssist.git
cd WID3010-JunoAssist

# If already cloned — pull latest vanness_integration
cd WID3010-JunoAssist
git fetch origin
git checkout vanness_integration
git pull origin vanness_integration
```

---

## 2. Build the ROS Catkin Workspace

> Run this once per session (or whenever ROS package files change).

```bash
# From project root
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash
```

Verify build succeeded — no red errors in the output. The last line should be:
```
[100%] Built target <package>
```

---

## 3. Create the Python Virtual Environment

> **Critical:** Source catkin `devel/setup.bash` BEFORE activating the venv.  
> Reversing the order breaks `rospy`, `cv_bridge`, and `sensor_msgs` imports.

```bash
# From project root — source catkin FIRST
source devel/setup.bash

# Then create and activate the venv
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt should now show `(.venv)`.

---

## 4. Install Python Dependencies

```bash
# Confirm you are inside backend/ with (.venv) active
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- `fastapi`, `uvicorn`, `pydantic` — backend API
- `numpy>=1.24` — EMA probability smoothing
- `opencv-python>=4.8` — face detection (Phase 2 CNN)
- `tensorflow>=2.13` — Mini-Xception emotion CNN (Phase 2)
- `pytest` — test runner

> **Note:** `tensorflow` is ~500 MB. This step will take several minutes on first install. Keep the terminal open.

Verify key packages after install:

```bash
python3 -c "import numpy; print('numpy', numpy.__version__)"
python3 -c "import cv2; print('cv2', cv2.__version__)"
python3 -c "import tensorflow as tf; print('tensorflow', tf.__version__)"
```

All three must print a version number, not an error.

---

## 5. Run the Unit Tests

```bash
# From backend/ with (.venv) active
python3 -m pytest tests/ -v
```

Expected: **18 passed, 0 failed**.

If any test fails, stop and fix it before proceeding — a failing test means the emotion pipeline has a bug.

---

## 6. Download CNN Model Files (Phase 2 — Real Emotion Detection)

> Skip this section if running mock mode only for the demo.

Place all model files in `backend/models/`. This directory is gitignored — files must be downloaded manually on each machine.

```bash
mkdir -p backend/models
```

### 6a. OpenCV DNN Face Detector (ResNet-SSD)

```bash
cd backend/models

# Prototxt (network architecture)
wget https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt

# Caffemodel (pre-trained weights, ~10 MB)
wget https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel
```

### 6b. Mini-Xception Emotion CNN

Download `emotion_model.h5` from the project shared drive (ask Jon or Anas for the link) and place it at:

```
backend/models/emotion_model.h5
```

Verify all three files are present:

```bash
ls -lh backend/models/
# Expected:
# deploy.prototxt                          (~28 KB)
# res10_300x300_ssd_iter_140000.caffemodel (~10 MB)
# emotion_model.h5                         (~2 MB)
```

---

## 7. Enable Real CNN in the Backend

By default `app.py` instantiates `EmotionDetector()` with `use_real=False` (mock mode).  
To switch to real CNN inference, coordinate with **Jon** to update `app.py` line 46:

```python
# Current (mock mode — default)
emotion_detector = EmotionDetector()

# Change to (real CNN mode — requires model files from §6)
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

## 8. Run the Full System

Open **four terminals** in VS Code (use the split terminal feature). Source order matters in each terminal.

### Terminal 1 — roscore

```bash
source /opt/ros/noetic/setup.bash
roscore
```

Leave running. Do not close.

### Terminal 2 — ROS Nodes (camera, microphone, TTS)

```bash
source /opt/ros/noetic/setup.bash
cd /path/to/WID3010-JunoAssist
source devel/setup.bash
roslaunch juno_bringup juno_robot.launch
```

Confirm camera node started:
```bash
# In a separate terminal
source /opt/ros/noetic/setup.bash
rostopic hz /camera/image_raw
# Expected: ~30 Hz
```

### Terminal 3 — FastAPI Backend (ROS mode)

```bash
# Source catkin FIRST, then venv
source /opt/ros/noetic/setup.bash
cd /path/to/WID3010-JunoAssist
source devel/setup.bash
cd backend
source .venv/bin/activate
export JUNO_ROBOT_INTERFACE=ros
python3 main.py
```

Expected log output:
```
INFO:     Application startup complete.
```

No import errors. If you see `rospy could not be imported`, catkin was not sourced before the venv.

### Terminal 4 — Dashboard

```bash
cd /path/to/WID3010-JunoAssist/dashboard
npm run dev
```

Open `http://localhost:5173` in the browser.

---

## 9. Verification Checklist

Run through this before each demo session.

```bash
# 1. Camera topic is live at 30 Hz
rostopic hz /camera/image_raw

# 2. Camera node is registered
rosnode list | grep camera_node

# 3. Backend started cleanly
curl -s http://localhost:8000/api/status | python3 -m json.tool
# Look for: "current_emotion": (any value — not an error)

# 4. Wake JUNO and confirm active mode
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "Hey, Juno"}'

curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "Yes"}'

# 5. Emotion field is not "unknown" in active mode
curl -s http://localhost:8000/api/status | python3 -m json.tool
# "current_emotion" must be one of: happy / neutral / tired / stressed / frustrated

# 6. Break recommendation responds with emotion-aware text
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "I need a break"}'
```

---

## 10. Common Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: rospy` | venv activated before catkin sourced | Deactivate venv, `source devel/setup.bash`, then reactivate venv |
| `ModuleNotFoundError: cv_bridge` | Same as above | Same fix |
| `ModuleNotFoundError: numpy` | requirements not installed | `pip install -r requirements.txt` |
| `ModuleNotFoundError: cv2` | opencv not installed | `pip install opencv-python>=4.8` |
| `current_emotion: unknown` | Backend not in ACTIVE mode | Send wake phrase + confirmation first |
| `rostopic hz` shows 0 Hz | Camera node not running | Check Terminal 2 for errors; try `camera_device:=/dev/video0` |
| `/dev/video2 not found` | Wrong camera device index | `roslaunch juno_bringup juno_robot.launch camera_device:=/dev/video0` |
| `[EmotionDetector] Model load failed` | Model files missing from `backend/models/` | Follow §6 to download model files |
| `18 passed` but backend crashes | Import error outside test scope | Run `python3 main.py` and read the full traceback |

---

## 11. Environment Variable Reference

| Variable | Default | Purpose |
|---|---|---|
| `JUNO_ROBOT_INTERFACE` | `mock` | Set to `ros` on robot to enable ROS bridge |
| `JUNO_EMOTION_UPDATE_SECONDS` | `3.0` | How often the emotion monitor loop polls the camera (seconds) |
| `EMOTION_MODEL_PATH` | `models/emotion_model.h5` | Path to Mini-Xception `.h5` model file |
| `JUNO_DASHBOARD_URL` | `http://localhost:5173` | Dashboard URL opened by JUNO on activation |
| `JUNO_WAKE_PHRASE` | `hey, juno` | Wake phrase that activates JUNO |
