# Vision and Emotion Pipeline — Technical Implementation

> Companion to `docs/technical_requirements_emotion.md` and `docs/product_requirements.md § F4`.  
> **Layer boundary:** All code in this document lives in `backend/src/vision/` and `backend/tests/`.  
> Do not modify files outside this boundary without coordinating with the owner listed in `README.md`.

---

## 0. Pre-Integration Checklist (Run Before Anything Else)

Before touching any vision code, verify these pass:

```bash
# From project root
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

## 1. Camera Integration Path (ROS → Backend)

Vanness verifies this path works. The implementation is owned by Anas (`ros_jupiter_interface.py`) and the perception_pkg (`camera_node.py`).

### Data flow

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

### Key contract points

- `_emotion_monitor_loop` in `app.py` only runs when `robot_state.snapshot()["mode"] == RobotMode.ACTIVE`. The emotion field stays at its last value when Juno is idle or in confirmation mode.
- In **mock mode** (`JUNO_ROBOT_INTERFACE` not set), `robot.get_camera_frame()` returns `None`. `EmotionDetector.predict_from_frame(None)` handles `None` safely via the mock path.
- `_camera_callback` runs on a ROS subscriber thread; `get_camera_frame()` is called on the asyncio thread. `self.latest_frame` is not protected by a lock, but this is acceptable for demo purposes — a stale frame produces a valid (if slightly delayed) emotion estimate.

### ROS catkin workspace — what is already set up

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

### Build and run sequence (ROS machine only)

```bash
# From project root — only needs to be done once per session
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash

# Terminal 1: roscore
roscore

# Terminal 2: launch perception + language nodes
roslaunch juno_bringup juno_robot.launch

# Terminal 3: backend in ROS mode (source catkin devel BEFORE activating venv)
source devel/setup.bash
cd backend
source .venv/bin/activate
export JUNO_ROBOT_INTERFACE=ros
python main.py

# Terminal 4: dashboard
cd dashboard
npm run dev
```

> The backend must `source devel/setup.bash` BEFORE activating the Python venv so that `rospy`, `cv_bridge`, and `sensor_msgs` are importable. Sourcing order matters.

---

## 2. Current MVP Implementation

These files run **without hardware**. Verify they work first. Do not modify them until confirmed passing.

### `backend/src/vision/emotion_smoothing.py` (existing — keep as-is)

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

### `backend/src/vision/emotion_detector.py` (existing MVP)

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

# Start backend in mock mode (no ROS needed)
python main.py
# Expected: "Application startup complete." — no errors

# In another terminal, verify emotion is in the status response
curl -s http://localhost:8000/api/status | python3 -m json.tool
# Look for "current_emotion": — it will be "unknown" until ACTIVE mode

# Activate JUNO then check emotion changes
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "Hey, Juno"}'

curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "Yes"}'

# Now check status — current_emotion should be a valid state (not "unknown")
curl -s http://localhost:8000/api/status | python3 -m json.tool
```

---

## 3. Upgraded Emotion Pipeline — EMA + Hysteresis (Should)

The upgrade replaces `EmotionSmoother` (majority vote) with `EMAFusion + HysteresisStateMachine`.  
**The public interface `predict_from_frame(frame=None) -> EmotionState` is unchanged — `app.py` needs zero modification.**

### 3.1 Step 0: Add `numpy` to `backend/requirements.txt`

`numpy` is not currently in `requirements.txt` but is required by `emotion_fusion.py`.

Edit `backend/requirements.txt` to add `numpy`:

```
fastapi==0.115.6
uvicorn[standard]==0.33.0
pydantic==2.10.4
python-multipart==0.0.20
pytest==8.3.4
numpy>=1.24
```

Then reinstall:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

Verify: `python -c "import numpy; print(numpy.__version__)"` — should print a version, not an error.

### 3.2 Create `backend/src/vision/emotion_fusion.py` (new file)

Create this file at exactly `backend/src/vision/emotion_fusion.py`. It has no dependencies outside `numpy` and `src.core.models`.

```python
import numpy as np

from src.core.models import EmotionState

ALPHA: float = 0.30
DWELL_FRAMES: int = 45

# Ordered labels — index must match probability vector positions used throughout this module
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

### 3.3 Replace `backend/src/vision/emotion_detector.py`

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

# One-hot Juno-5 vectors — index order must match emotion_fusion._LABELS exactly:
# [Happy=0, Neutral=1, Tired=2, Stressed=3, Frustrated=4]
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

### 3.4 Migration steps (in order)

```
Step 0: Add numpy to backend/requirements.txt and reinstall
Step 1: Create backend/src/vision/emotion_fusion.py  (new file, § 3.2)
Step 2: Replace backend/src/vision/emotion_detector.py  (§ 3.3)
        DO NOT delete emotion_smoothing.py
Step 3: Run tests:  cd backend && python -m pytest tests/ -v
        All tests must pass before committing
Step 4: Verify backend starts:  python main.py  (no import errors)
Step 5: Extend test file with EMA + Hysteresis tests  (see 02_testing_verification.md)
```

### 3.5 Verify the upgrade is working

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

## 4. Optional: Real CNN Extension

> Complete only after Must checklist and Should (EMA upgrade) are both done and stable.

### 4.1 Class remapping: FER-7 → Juno-5

Standard CNN models (Mini-Xception/FER2013) output 7 classes that do not include `Tired`, `Stressed`, or `Frustrated`. A projection matrix maps them to the 5 Juno labels.

```python
# Add to emotion_detector.py if implementing the real CNN path
# Rows = Juno-5 [Happy, Neutral, Tired, Stressed, Frustrated]
# Cols = FER-7  [Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral]
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

### 4.2 Face detection (OpenCV DNN)

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

### 4.3 Mini-Xception preprocessing

Input: 64×64 grayscale. Output: 7-class softmax.

```python
def preprocess_face(face_roi: np.ndarray) -> np.ndarray:
    face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    face_resized = cv2.resize(face_gray, (64, 64))
    face_norm = face_resized.astype("float32") / 255.0
    return np.expand_dims(np.expand_dims(face_norm, -1), 0)  # shape (1, 64, 64, 1)
```

### 4.4 Extended `EmotionDetector` with real CNN path

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

## 5. Break Recommender Integration

Vanness **verifies** — the `BreakRecommender` is already implemented. Do not modify `break_recommender.py`.

### Full emotion → response chain

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

### `BreakRecommender.recommend()` output by emotion state

| EmotionState | Response |
|---|---|
| `TIRED` | "You seem a little tired. I recommend a 5-minute break before continuing." |
| `STRESSED` | "You seem a bit stressed. Let us prioritise the nearest deadline and start with a short study session." |
| `FRUSTRATED` | "You seem frustrated. Try pausing briefly, then break the task into smaller steps." |
| `HAPPY` | "You seem to be doing well. This is a good time to continue your current task." |
| `NEUTRAL` | "You seem neutral. I can help you check your schedule, set a timer, or plan your next task." |

---

## 6. Dependency Reference

### Backend `requirements.txt` (after adding numpy)

```
fastapi==0.115.6
uvicorn[standard]==0.33.0
pydantic==2.10.4
python-multipart==0.0.20
pytest==8.3.4
numpy>=1.24
```

### Optional CNN dependencies (add only if implementing Phase 2)

```
opencv-python>=4.8
tensorflow>=2.13
```

Do not install `deepface` — it adds ~200 MB and runs at ~80 ms/frame vs ~15 ms for Mini-Xception.

### ROS-side dependencies (already declared in package.xml — no changes needed)

| Package | Declared in |
|---|---|
| `rospy`, `sensor_msgs`, `std_msgs` | Both perception_pkg and language_pkg package.xml |
| `cv_bridge` | perception_pkg package.xml (build_depend) |
| `pyaudio`, `moonshine_onnx` | Python packages, must be pip-installed on robot OS |
| `pyttsx3` or `espeak` | tts_node.py runtime dependency, must be present on robot |

These are Anas's responsibility. Vanness only needs to confirm `/camera/image_raw` is publishing.
