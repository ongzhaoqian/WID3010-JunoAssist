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
| Python 3.8 exactly | `python3 --version` | `Python 3.8.x` — ROS Noetic requires 3.8 |
| Git | `git --version` | any version |
| Camera device | `ls /dev/video*` | `/dev/video2` present |

If ROS Noetic is not installed, stop — it must be installed by the lab administrator before proceeding.

---

## 1. Pull Latest Code

The repository is already open in VS Code. Before running anything, pull the latest changes from `main`:

```bash
git fetch origin
git checkout main
git pull origin main
```

> If you are still on a feature branch before the merge, switch to `main` first — all vision/emotion code has been merged in.

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

## 3. Create the Python Virtual Environments

Two venvs are required. Vision deps (`numpy`, `opencv`, `tensorflow`) conflict with the backend's `typing-extensions` — they use separate venvs.

```bash
# Backend venv (for running main.py)
cd backend
python3 -m venv .venv

# Bootstrap a fresh pip — the bundled pip on this machine is broken due to a system OpenSSL issue
wget -O /tmp/get-pip.py https://bootstrap.pypa.io/pip/3.8/get-pip.py
.venv/bin/python3 /tmp/get-pip.py

source .venv/bin/activate
```

Your prompt should now show `(.venv)`.

```bash
# Vision venv (for tests and TensorFlow inference) — separate terminal
cd backend
python3 -m venv .venv-vision
```

---

## 4. Install Python Dependencies

### Backend venv (`.venv`)

```bash
# Confirm you are inside backend/ with (.venv) active
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-vision.txt

# tensorflow downgrades typing-extensions to 4.5.0 — fix it:
pip install "typing-extensions>=4.12.2"

# rospkg is not bundled with ROS Noetic — install it in the venv:
pip install rospkg
```

This installs fastapi, uvicorn, pydantic, pytest, numpy, opencv, tensorflow, rospkg. The `typing-extensions` pin after tensorflow is required — tensorflow's declared constraint (`<4.6.0`) is overly strict and the fix is safe to ignore.

### Vision venv (`.venv-vision`)

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

## 5. Run the Unit Tests

```bash
# From backend/ — use .venv-vision (tests import numpy via emotion_fusion)
.venv-vision/bin/python3 -m pytest tests/ -v
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

The model is `fer2013_mini_XCEPTION.102-0.66.hdf5` from the `oarriaga/face_classification` repository — the standard FER2013-trained Mini-Xception model (~580 KB). It outputs 7 emotion classes (Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral), which our `MAPPING_MATRIX` in `emotion_detector.py` remaps to the 5 Juno states.

```bash
cd backend/models

# Download the model (~580 KB)
wget https://github.com/oarriaga/face_classification/raw/master/trained_models/emotion_models/fer2013_mini_XCEPTION.102-0.66.hdf5

# Rename to the expected filename
mv fer2013_mini_XCEPTION.102-0.66.hdf5 emotion_model.h5
```

> `.hdf5` and `.h5` are the same file format — the rename is just for consistency with the default `EMOTION_MODEL_PATH`.  
> If `wget` is slow, download the file in a browser and `scp` it to the robot at `backend/models/emotion_model.h5`.

Verify all three files are present:

```bash
ls -lh backend/models/
# Expected:
# deploy.prototxt                          (~28 KB)
# res10_300x300_ssd_iter_140000.caffemodel (~10 MB)
# emotion_model.h5                         (~580 KB)
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
source /opt/ros/noetic/setup.bash
cd /path/to/WID3010-JunoAssist
source devel/setup.bash
cd backend
source .venv/bin/activate
# Expose ROS Python packages to the venv (rospy, cv_bridge, sensor_msgs, etc.)
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
     -d '{"text": "Hey, John"}'

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

## 11. Environment Variable Reference

| Variable | Default | Purpose |
|---|---|---|
| `JUNO_ROBOT_INTERFACE` | `mock` | Set to `ros` on robot to enable ROS bridge |
| `JUNO_EMOTION_UPDATE_SECONDS` | `3.0` | How often the emotion monitor loop polls the camera (seconds) |
| `EMOTION_MODEL_PATH` | `models/emotion_model.h5` | Path to Mini-Xception `.h5` model file |
| `JUNO_DASHBOARD_URL` | `http://localhost:5173` | Dashboard URL opened by JUNO on activation |
| `JUNO_WAKE_PHRASE` | `hey john` | Wake phrase that activates JUNO |
