# Vanness — Vision and Emotion Integration

**Primary role:** Backend-Vision layer owner  
**Secondary support:** Break recommender verification, emotion smoothing tests  
**Rubric coverage:** Vision Integration, HRI emotion-aware response

---

## File Ownership

### Owned by Vanness (strict Backend-Vision boundary)

| File | Status | Required Action |
|---|---|---|
| `backend/src/vision/emotion_detector.py` | Implemented — mock weighted predictor | Upgrade: swap `EmotionSmoother` for `EMAFusion + HysteresisStateMachine` |
| `backend/src/vision/emotion_smoothing.py` | Implemented — majority-vote smoother | Keep as-is (used by existing tests); replaced by `emotion_fusion.py` in new code |
| `backend/src/vision/emotion_fusion.py` | Not yet created | **Create this file** — EMA + Hysteresis smoother |
| `backend/tests/test_emotion_smoothing.py` | 1 test (majority vote only) | **Extend** with EMA + Hysteresis tests |

> Do not touch files outside `backend/src/vision/` and `backend/tests/`. Changes to `app.py`, `ros_jupiter_interface.py`, `break_recommender.py`, or ROS nodes require coordination with Jon or Anas first.

### Read-only / Coordinate with Owner

| File | Owner | What Vanness verifies |
|---|---|---|
| `src/perception_pkg/scripts/camera_node.py` | Anas | `/camera/image_raw` topic publishes at 30 Hz |
| `backend/src/robot/ros_jupiter_interface.py` | Anas | `_camera_callback` stores latest frame correctly |
| `backend/src/api/app.py` | Jon | `_emotion_monitor_loop` calls `predict_from_frame()` every 3 s |
| `backend/src/productivity/break_recommender.py` | Jon (support) | Tired/Stressed/Frustrated trigger correct break responses |

---

## Task Checklist (Priority Order)

### Must — Required for demo
- [ ] Confirm mock `EmotionDetector` runs without errors in mock mode (no hardware needed)
- [ ] Confirm dashboard `current_emotion` field updates via `/ws/status` during active mode
- [ ] Verify tired/stressed/frustrated emotion triggers break recommendation (`REQUEST_BREAK` and `ASK_STATUS` intents)
- [ ] Prepare dashboard screenshot showing emotion state in active mode
- [ ] Work with Anas to verify `/camera/image_raw` publishes at 30 Hz during robot lab session
- [ ] Capture camera/emotion evidence screenshot or terminal output for the report

### Should — Complete if core demo is stable
- [ ] Create `backend/src/vision/emotion_fusion.py` with `EMAFusion` and `HysteresisStateMachine`
- [ ] Update `backend/src/vision/emotion_detector.py` to use `EMAFusion + HysteresisStateMachine`
- [ ] Extend `backend/tests/test_emotion_smoothing.py` with EMA + Hysteresis unit tests
- [ ] Run all tests: `cd backend && python -m pytest tests/ -v`

### Optional — Only if core items are all stable
- [ ] Add OpenCV DNN face detection in `emotion_detector.py`
- [ ] Integrate Mini-Xception CNN for real emotion classification

---

## Deliverables

| Deliverable | Where to put it |
|---|---|
| Report subsection: Vision Integration and Emotion-Aware Behaviour | See `03_report_section_draft.md` for a ready-to-submit draft |
| Dashboard emotion screenshot (active mode) | Capture during demo rehearsal |
| Camera/emotion evidence (terminal or dashboard) | Capture during robot lab session with Anas |
| Limitation paragraph (mock vs. real, ethical disclaimer) | Included in `03_report_section_draft.md` |

---

## Document Index

| File | Purpose |
|---|---|
| `01_vision_emotion_pipeline.md` | Full technical implementation: camera path, emotion pipeline, all Python code |
| `02_testing_verification.md` | Unit tests, ROS verification commands, dashboard checks, evaluation criteria |
| `03_report_section_draft.md` | Complete report section ready to submit |
| `04_robot_setup.md` | Step-by-step Ubuntu VS Code setup guide for the robot machine |

---

## Architecture Summary (Vanness's slice)

```
camera_node ──/camera/image_raw──► RosJupiterInterface._camera_callback
                                           │ (stores self.latest_frame)
                                           ▼
                              robot.get_camera_frame()
                                           │ (called every 3 s by _emotion_monitor_loop)
                                           ▼
                              EmotionDetector.predict_from_frame(frame)
                                           │
                              ┌────────────┴────────────┐
                              │ Mock path (MVP)          │ Real path (optional)
                              │ random.choice(weights)   │ face detect → CNN infer
                              └────────────┬────────────┘
                                           │ P_juno (5-class vector)
                                           ▼
                              EMAFusion.update(P_juno)      ← emotion_fusion.py
                                           │ P_t (smoothed distribution)
                                           ▼
                              HysteresisStateMachine.update(P_t) → EmotionState
                                           │
                              robot_state.set_emotion(emotion)
                                           │
                              /ws/status WebSocket broadcast
                                           │
                              Dashboard: current_emotion display
                                           │
                              ResponseGenerator.generate(intent, emotion, text)
                                           │
                              BreakRecommender.recommend(emotion)
```
