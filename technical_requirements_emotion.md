# Facial Emotion Recognition — Technical Requirements

> Companion to `product_requirements.md` § F4.  
> Covers the full CV pipeline: face detection → CNN inference → class remapping → state determination.  
> **Coding agent:** Backend-Vision (`backend/src/vision/`)

---

## 1. Problem Statement

The system must reliably classify a user's emotional state into one of five Juno-specific labels:

| Juno Label | Behavioural Meaning |
| :--- | :--- |
| `Happy` | Positive, engaged — Juno responds warmly |
| `Neutral` | Default resting state — Juno responds normally |
| `Tired` | Low energy / drowsy — Juno suggests a break or shorter responses |
| `Stressed` | Anxious or under pressure — Juno lowers stimulus, offers calm guidance |
| `Frustrated` | Irritated, blocked — Juno uses shorter sentences, offers help |

These labels are **not** directly available from any standard emotion dataset. The pipeline must bridge from a standard CNN's output to these five operational states in a principled way.

---

## 2. Pipeline Overview

Camera frames enter the pipeline via `RosJupiterInterface.get_camera_frame()`, which returns `self.latest_frame` — an OpenCV BGR array stored by `_camera_callback` each time a `sensor_msgs/Image` message arrives on `/camera/image_raw`. No intermediate ROS node is required; the backend subscribes directly.

```
camera_node  →  /camera/image_raw  →  RosJupiterInterface._camera_callback
                                              │
                              robot.get_camera_frame()
                                              │
                                              ▼
Camera Frame (latest, up to 30 Hz)
        │
        ▼
┌───────────────────┐
│  Face Detection   │  OpenCV DNN or MediaPipe Face Mesh
│  (confidence > θ) │  Reject frame if no face or confidence < 0.70
└────────┬──────────┘
         │  Bounding box
         ▼
┌───────────────────┐
│  Preprocessing    │  Crop → 48×48 or 224×224 → normalise
└────────┬──────────┘
         │  Tensor
         ▼
┌───────────────────┐
│  CNN Inference    │  Softmax over 7 standard FER classes
│  (FER+ or Mini-   │  Output: probability vector P_raw ∈ ℝ⁷
│   Xception)       │
└────────┬──────────┘
         │  P_raw
         ▼
┌───────────────────┐
│  Class Remapping  │  Projection matrix M ∈ ℝ⁵ˣ⁷
│                   │  P_juno = M · P_raw  (see § 5)
└────────┬──────────┘
         │  P_juno ∈ ℝ⁵
         ▼
┌───────────────────┐
│  EMA Fusion       │  P_t = α · P_juno + (1-α) · P_{t-1}
│  (on distribution)│  α = 0.30, skip update if face not detected
└────────┬──────────┘
         │  P_t (smoothed distribution)
         ▼
┌───────────────────┐
│  Hysteresis       │  Candidate = argmax(P_t)
│  State Machine    │  Transition only after dwell ≥ T_dwell frames
└────────┬──────────┘
         │  EmotionState (final)
         ▼
   Stored in backend state (core/state.py)
   Broadcast → /ws/status  (field: current_emotion)
   Optional: robot.set_led_state() on emotion-triggered break recommendation
```

---

## 3. Face Detection

### 3.1 Recommended Model

Use **OpenCV's DNN face detector** (`deploy.prototxt` + `res10_300x300_ssd_iter_140000.caffemodel`) rather than Haar cascades, as it handles partial occlusion and varied lighting better.

```python
net = cv2.dnn.readNetFromCaffe(prototxt_path, caffemodel_path)
blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104, 177, 123))
net.setInput(blob)
detections = net.forward()
confidence = detections[0, 0, i, 2]
```

Alternatively, **MediaPipe FaceMesh** is acceptable if the robot has sufficient compute for the heavier model.

### 3.2 Frame Rejection Policy

- If no face is detected in the frame: **do not update** the EMA smoother. The last known smoothed distribution `P_t` is retained.
- If face detection confidence < 0.70: treat as no-face (reject frame).
- If face bounding box area < 1 000 px²: reject (too far from camera to be reliable).

This is **confidence gating** — it ensures only high-quality frames contribute to the emotional state, which is strictly better than naive window averaging where noisy frames pollute the history.

---

## 4. CNN Model Selection

### 4.1 Recommended: Mini-Xception (FER+ trained)

| Property | Value |
| :--- | :--- |
| Input | 64×64 grayscale |
| Output | 7-class softmax (FER2013 classes) |
| Size | ~2 MB |
| Inference (CPU) | ~15 ms per frame |
| Source | `oarriaga/face_classification` (MIT licence) |

The 7 standard FER2013 classes output by this model are:

```
Index  Label
  0    Angry
  1    Disgust
  2    Fear
  3    Happy
  4    Sad
  5    Surprise
  6    Neutral
```

### 4.2 Alternative: DeepFace Library

If the team prefers a plug-and-play approach, `deepface` wraps multiple pre-trained models (VGG-Face, ArcFace, Facenet):

```python
from deepface import DeepFace
result = DeepFace.analyze(frame, actions=["emotion"], enforce_detection=False)
probabilities = result[0]["emotion"]  # dict: {angry, disgust, fear, happy, sad, surprise, neutral}
```

Use `enforce_detection=False` to gracefully handle frames where a face is marginal.

**Trade-off:** DeepFace is easier to integrate but adds ~200 MB of dependencies and is slower (~80 ms/frame on CPU). Mini-Xception is preferred for the Jupiter robot's limited compute.

### 4.3 Preprocessing (Mini-Xception path)

```python
face_roi = frame[y:y+h, x:x+w]
face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
face_resized = cv2.resize(face_gray, (64, 64))
face_norm = face_resized.astype("float32") / 255.0
face_tensor = np.expand_dims(np.expand_dims(face_norm, -1), 0)  # (1, 64, 64, 1)
P_raw = model.predict(face_tensor)[0]  # shape (7,)
```

---

## 5. Class Remapping: FER7 → Juno5

This is the critical design decision. Standard FER2013 classes do not include `Tired`, `Stressed`, or `Frustrated`. The remapping uses a fixed **projection matrix M** that encodes domain knowledge about which standard emotions correspond to each Juno state.

### 5.1 Projection Matrix

```
            Angry  Disgust  Fear  Happy   Sad  Surprise  Neutral
             [0]     [1]    [2]    [3]    [4]     [5]      [6]
Happy      [  0.0    0.0    0.0    1.0    0.0     0.0      0.0  ]
Neutral    [  0.0    0.0    0.0    0.0    0.0     0.2      0.8  ]
Tired      [  0.0    0.0    0.0    0.0    1.0     0.0      0.0  ]
Stressed   [  0.3    0.1    0.6    0.0    0.0     0.0      0.0  ]
Frustrated [  0.7    0.3    0.0    0.0    0.0     0.0      0.0  ]
```

As Python (stored in `backend/src/vision/emotion_detector.py`):

```python
import numpy as np

MAPPING_MATRIX = np.array([
    # Angry  Disgust  Fear  Happy   Sad  Surprise  Neutral
    [  0.0,    0.0,   0.0,   1.0,   0.0,    0.0,     0.0],  # Happy
    [  0.0,    0.0,   0.0,   0.0,   0.0,    0.2,     0.8],  # Neutral
    [  0.0,    0.0,   0.0,   0.0,   1.0,    0.0,     0.0],  # Tired
    [  0.3,    0.1,   0.6,   0.0,   0.0,    0.0,     0.0],  # Stressed
    [  0.7,    0.3,   0.0,   0.0,   0.0,    0.0,     0.0],  # Frustrated
], dtype=np.float32)

def remap(P_raw: np.ndarray) -> np.ndarray:
    """Project 7-class FER softmax onto 5 Juno emotion classes."""
    P_juno = MAPPING_MATRIX @ P_raw          # shape (5,)
    P_juno = P_juno / P_juno.sum()           # re-normalise to sum to 1
    return P_juno
```

### 5.2 Mapping Rationale

| Juno State | FER Source | Weight Justification |
| :--- | :--- | :--- |
| `Happy` | Happy (1.0) | Direct 1:1 correspondence |
| `Neutral` | Neutral (0.8) + Surprise (0.2) | Surprise is often neutral in brief interactions; slight blend prevents over-sensitivity to mild surprise |
| `Tired` | Sad (1.0) | Fatigue manifests as low-arousal negative affect, visually closest to sadness (drooped eyelids, downturned mouth) |
| `Stressed` | Fear (0.6) + Angry (0.3) + Disgust (0.1) | Stress is high-arousal negative affect; fear dominates, anger secondary for deadline stress |
| `Frustrated` | Angry (0.7) + Disgust (0.3) | Frustration sits between anger and disgust; anger slightly dominant |

> **Note:** These weights are a starting point. They should be validated empirically on a small dataset of the target user population if time permits. The matrix rows need not sum to 1 (renormalisation is applied in `remap()`), so individual row weights express relative contribution strength.

---

## 6. State Determination: EMA + Hysteresis

This is the replacement for the current majority-vote smoother. The approach operates in two stages.

### 6.1 Stage 1 — EMA on the Probability Distribution

Rather than collecting discrete labels and voting on them, we apply an exponential moving average **directly on the 5-class probability vector**. This retains uncertainty information across frames — a distinction the majority vote discards.

```
P_t = α · P_juno_new + (1 - α) · P_{t-1}
```

- **α = 0.30** (smoothing factor; lower = more inertia, higher = more reactive)
- `P_{t-1}` is initialised to `[0, 1, 0, 0, 0]` (Neutral) on startup
- Update is **skipped** (P_t unchanged) on frames where face detection fails

**Why EMA on distributions is better than label averaging:**
- Label averaging (majority vote, mean) loses the *degree* of confidence. A frame with 55% Tired and 44% Stressed votes the same as a frame with 99% Tired. EMA on distributions preserves this.
- The resulting `P_t` is a proper probability distribution and can be directly reported as `emotion_confidence` in the WebSocket payload.

```python
ALPHA = 0.30

class EMAFusion:
    def __init__(self):
        self.P_t = np.array([0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)  # start Neutral

    def update(self, P_juno: np.ndarray) -> np.ndarray:
        self.P_t = ALPHA * P_juno + (1 - ALPHA) * self.P_t
        return self.P_t

    def skip(self) -> np.ndarray:
        return self.P_t  # no update; return last known distribution
```

### 6.2 Stage 2 — Hysteresis State Machine

The candidate emotion is `argmax(P_t)`, but the **output state does not change immediately**. A transition is only committed after the candidate has been the argmax for at least `T_dwell` consecutive frames.

```
T_dwell = 45 frames  (≈ 1.5 seconds at 30 Hz)
```

This prevents the displayed state from flickering between adjacent emotions (e.g., Neutral ↔ Tired) due to momentary expression changes.

```python
DWELL_FRAMES = 45

class HysteresisStateMachine:
    def __init__(self):
        self.current_state = EmotionState.NEUTRAL
        self.candidate = EmotionState.NEUTRAL
        self.dwell_count = 0

    def update(self, P_t: np.ndarray) -> EmotionState:
        LABELS = [EmotionState.HAPPY, EmotionState.NEUTRAL,
                  EmotionState.TIRED, EmotionState.STRESSED, EmotionState.FRUSTRATED]
        new_candidate = LABELS[int(np.argmax(P_t))]

        if new_candidate == self.candidate:
            self.dwell_count += 1
        else:
            self.candidate = new_candidate
            self.dwell_count = 1

        if self.dwell_count >= DWELL_FRAMES and new_candidate != self.current_state:
            self.current_state = new_candidate
            self.dwell_count = 0  # reset after committing transition

        return self.current_state
```

### 6.3 Combined Flow

```python
# Called once per camera frame
def process_frame(frame) -> tuple[EmotionState, float]:
    face, face_confidence = detect_face(frame)

    if face is None or face_confidence < 0.70:
        P_t = ema.skip()
    else:
        P_raw = cnn.infer(preprocess(face))       # shape (7,)
        P_juno = remap(P_raw)                      # shape (5,)
        P_t = ema.update(P_juno)

    state = hsm.update(P_t)
    confidence = float(P_t[np.argmax(P_t)])
    return state, confidence
```

---

## 7. Summary: Why Not Averaging?

| Method | What it discards | Problem |
| :--- | :--- | :--- |
| **Label mean** (e.g., encode Happy=0, Neutral=1…) | Ordinal structure is meaningless for emotions | "Average of Happy and Frustrated" has no semantic value |
| **Rolling mode / majority vote** (current impl) | Per-frame confidence scores | A barely-winning label in a noisy window looks identical to a dominant one |
| **Simple rolling average of probabilities** | History weighting | All frames in window weighted equally; old stale frames matter as much as the latest |
| **EMA on distributions + Hysteresis** (proposed) | Nothing meaningful | Retains confidence, weights recent frames more, prevents flickering on transitions |

The proposed method has two tunable parameters with clear semantics:
- `α` (EMA decay): controls how quickly the system responds to genuine changes
- `T_dwell` (hysteresis frames): controls how long a new emotion must persist before it is committed

---

## 8. Required Changes to Existing Code

### 8.1 `backend/src/vision/emotion_smoothing.py`

**Replace** the `EmotionSmoother` class with `EMAFusion` + `HysteresisStateMachine` as specified in § 6.1 and § 6.2.

The existing `Counter.most_common` approach in `EmotionSmoother` is the mode-based discrete smoother that is being retired.

Rename the file to `emotion_fusion.py` (or keep `emotion_smoothing.py` and replace the class) — keep the import path stable so `emotion_detector.py` doesn't break.

### 8.2 `backend/src/vision/emotion_detector.py`

Replace the mock random predictor with the real pipeline:

1. Load face detection model on init
2. Load CNN model on init  
3. In `predict_from_frame(frame)`:
   - Call face detector
   - If face found and confident: preprocess → CNN infer → remap → EMA update
   - If no face: EMA skip
   - Call hysteresis state machine
   - Return `(EmotionState, confidence: float)`

The method signature should change from `predict_from_frame(frame) -> EmotionState` to `predict_from_frame(frame) -> tuple[EmotionState, float]` to expose confidence to the WebSocket payload.

### 8.3 Update `backend/tests/test_emotion_smoothing.py`

The existing test:

```python
def test_emotion_smoother_returns_majority():
    smoother = EmotionSmoother(window_size=5)
    smoother.add(EmotionState.TIRED)
    smoother.add(EmotionState.NEUTRAL)
    smoother.add(EmotionState.NEUTRAL)
    assert smoother.current() == EmotionState.NEUTRAL
```

Must be replaced with tests for `EMAFusion` and `HysteresisStateMachine`:

| Test | Assertion |
| :--- | :--- |
| EMA initialises to Neutral distribution | `P_t[1] == 1.0` on fresh instance |
| EMA skip does not change distribution | Identical `P_t` before and after `skip()` |
| EMA update moves toward new input | `P_t` after update closer to `P_juno` than before |
| Hysteresis does not transition on fewer than `DWELL_FRAMES` | State unchanged after 44 Tired candidates |
| Hysteresis transitions after `DWELL_FRAMES` | State becomes Tired after 45 Tired candidates |
| Hysteresis resets dwell count on candidate change | Injecting Neutral mid-run resets count |

---

## 9. Tuning Parameters

| Parameter | Location | Default | Guidance |
| :--- | :--- | :--- | :--- |
| `ALPHA` | `emotion_fusion.py` | `0.30` | Increase → faster response, more noise. Decrease → smoother, slower |
| `DWELL_FRAMES` | `emotion_fusion.py` | `45` (1.5 s) | Decrease for faster UI updates; increase to reduce false transitions |
| Face confidence threshold | `emotion_detector.py` | `0.70` | Lower if robot is far from user; raise if too many false detections |
| Min face area (px²) | `emotion_detector.py` | `1000` | Tune based on typical user distance from robot camera |
| Emotion poll interval | `core/config.py` | `3.0 s` | Set via env var `JUNO_EMOTION_UPDATE_SECONDS` |
| CNN model path | `core/config.py` | `models/emotion_model.h5` | Set via env var `EMOTION_MODEL_PATH` |

---

## 10. File Locations

```
backend/
├── src/
│   └── vision/
│       ├── emotion_detector.py     ← REPLACE mock with real pipeline (§ 8.2)
│       ├── emotion_smoothing.py    ← REPLACE Counter with EMA + Hysteresis (§ 8.1)
│       └── __init__.py
└── tests/
    └── test_emotion_smoothing.py   ← UPDATE tests (§ 8.3)

models/                             ← ADD: store CNN weights here (not in src/)
└── emotion_model.h5                ← Mini-Xception weights
```

The face detection model weights (Caffe `.prototxt` + `.caffemodel`) should also live in `models/` and be loaded via path from `core/config.py`, not hardcoded.
