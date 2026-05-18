# Testing and Verification — Vision and Emotion

> **Run all test commands from `backend/`** — not from project root.  
> `src/` is a Python package relative to `backend/`; running pytest from the project root will cause `ModuleNotFoundError`.

---

## 1. Environment Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # Must include numpy>=1.24 (see 01_vision_emotion_pipeline.md § 3.1)

# Confirm numpy is installed
python -c "import numpy; print('numpy', numpy.__version__)"

# Confirm pytest is available
python -m pytest --version
```

---

## 2. Baseline Test (Run Before Any Changes)

```bash
python -m pytest tests/ -v
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

## 3. Full Test File: `backend/tests/test_emotion_smoothing.py`

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


# ── Legacy EmotionSmoother (keep — still imported by emotion_smoothing.py) ───

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


# ── EMAFusion ─────────────────────────────────────────────────────────────────

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


# ── HysteresisStateMachine ────────────────────────────────────────────────────

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


# ── EmotionDetector integration (mock path) ───────────────────────────────────

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
    """After committing a state via direct EMA+HSM drive, fewer than DWELL_FRAMES
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
python -m pytest tests/test_emotion_smoothing.py -v
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

### Failure triage

| Failing test | Most likely cause | Fix |
|---|---|---|
| `test_ema_initialises_to_neutral` | `EMAFusion.__init__` not setting P_t[1]=1.0 | Check `np.array([0.0, 1.0, ...]` init |
| `test_ema_update_correct_weighted_blend` | Alpha constant differs | Confirm `ALPHA = 0.30` in `emotion_fusion.py` |
| `test_hysteresis_transitions_at_dwell` | `DWELL_FRAMES` differs between test import and module | Both import from `src.vision.emotion_fusion` — check constant value |
| `test_ema_*` | `ModuleNotFoundError: numpy` | Add `numpy>=1.24` to `requirements.txt` and reinstall |
| `test_ema_*` or `test_hysteresis_*` | `ModuleNotFoundError: emotion_fusion` | Create `backend/src/vision/emotion_fusion.py` first |
| `test_mock_detector_*` | `ImportError` from `emotion_detector.py` | Check that `emotion_detector.py` imports from `.emotion_fusion` not `.emotion_smoothing` |

---

## 4. Backend Mock Mode Verification (No ROS Required)

```bash
# Terminal 1 — Start backend in mock mode
cd backend
source .venv/bin/activate
python main.py
# Expected: "Application startup complete." with no import errors

# Terminal 2 — Verify emotion appears in status
# First wake JUNO
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "Hey, Juno"}' | python3 -m json.tool

# Confirm
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "Yes"}' | python3 -m json.tool

# Check status — current_emotion should be a valid state
curl -s http://localhost:8000/api/status | python3 -m json.tool
# Expected: "current_emotion": "neutral"  (or tired/stressed/happy/frustrated)
# NOT "unknown" — that would mean _emotion_monitor_loop is not running

# Wait 3 seconds and check again — emotion should change (mock is random)
sleep 4
curl -s http://localhost:8000/api/status | python3 -m json.tool
```

---

## 5. Break Recommender Verification

JUNO must be in ACTIVE mode first (run the wake+confirm commands from § 4 above).

```bash
# Test REQUEST_BREAK intent
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "I need a break"}' | python3 -m json.tool
# "response" field should match BreakRecommender output for the current emotion

# Test ASK_STATUS intent (also emotion-aware)
curl -s -X POST http://localhost:8000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "What should I do now?"}' | python3 -m json.tool
# "response" field should include emotion context + deadline info
```

Since the mock detector cycles randomly, run the request several times to see different emotion-driven responses. Check that the `intent` field in the JSON response is `"request_break"` or `"ask_status"` — not `"unknown"`.

---

## 6. ROS Camera Topic Verification (Robot Lab Session — with Anas)

Run these during the robot lab session. Record terminal output as report evidence.

```bash
# After roslaunch juno_bringup juno_robot.launch

# Confirm camera topic is active
rostopic hz /camera/image_raw
# Expected: average rate: 30.000 (±5 Hz acceptable)

# Confirm topic exists
rostopic list | grep camera
# Expected: /camera/image_raw

# Confirm node is registered
rosnode list
# Expected: /camera_node in the list

# Confirm frames have valid headers
rostopic echo /camera/image_raw/header --noarr
# Expected: seq incrementing, stamp is recent
```

If camera topic is at wrong rate or absent:

```bash
# Check camera_node is running
rosnode info /camera_node

# Check for errors in the launch terminal
# Common issue: /dev/video2 not found → change camera_device param in launch file
roslaunch juno_bringup juno_robot.launch camera_device:=/dev/video0
```

After backend starts in ROS mode with camera running:

```bash
# Backend in ROS mode (separate terminal, after sourcing catkin devel)
export JUNO_ROBOT_INTERFACE=ros
python main.py

# Confirm backend started cleanly
# Expected log: "JUNO backend ROS bridge is ready."

# With JUNO in ACTIVE mode, check emotion is NOT "unknown"
curl -s http://localhost:8000/api/status | python3 -m json.tool
# "current_emotion" should be one of: happy/neutral/tired/stressed/frustrated
```

---

## 7. WebSocket Emotion Verification (Dashboard)

```bash
# Option A: Browser DevTools
# 1. Open http://localhost:5173
# 2. DevTools → Network → WS tab
# 3. Find /ws/status connection
# 4. Watch the JSON messages — "current_emotion" must update every ~1 s

# Option B: wscat command line
npm install -g wscat
wscat -c ws://localhost:8000/ws/status
# Watch the stream — should see JSON with current_emotion changing over time
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

## 8. Evaluation Criteria Table

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

## 9. Screenshot Checklist

Capture all of these before the final demo:

- [ ] `pytest tests/ -v` terminal output — all 18 tests passing
- [ ] `curl /api/status` JSON output — `current_emotion` showing a valid state
- [ ] Dashboard Status Panel — `current_emotion` visible in active mode
- [ ] Dashboard Command Panel — emotion-aware break suggestion in response field
- [ ] `rostopic hz /camera/image_raw` — showing ~30 Hz (robot lab session)
- [ ] `rosnode list` — showing `/camera_node` (robot lab session)
