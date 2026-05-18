# Report Section Draft: Vision Integration and Emotion-Aware Behaviour

> **Author:** Vanness  
> **Report section:** Vision Integration and Emotion-Aware Behaviour  
> **Required content:** Camera topic path, emotion detector/smoother, dashboard emotion state, limitations  
>
> Instructions: Copy this text into your assigned section of the final report. Edit details based on what was actually tested and confirmed during the robot lab session. Replace placeholder evidence markers (e.g., `[Screenshot X]`) with actual evidence.

---

## Vision Integration and Emotion-Aware Behaviour

### Overview

JUNO Assist includes a vision component that estimates the user's visible emotional state from camera input and adapts its responses accordingly. This module forms part of the system's Human-Robot Interaction (HRI) design: rather than treating every interaction identically, JUNO Assist adjusts its suggestions based on whether the user appears happy, neutral, tired, stressed, or frustrated. This section describes the camera integration path through the ROS layer, the emotion detection and smoothing pipeline in the backend, how the estimated state is displayed on the dashboard, and the limitations of the current prototype.

---

### Camera Integration Path

Camera frames enter the JUNO Assist system through the ROS perception pipeline. The `camera_node` in the `perception_pkg` package captures video from the Jupiter robot's camera at `/dev/video2` and publishes frames as `sensor_msgs/Image` messages on the `/camera/image_raw` topic at 30 Hz. This node is launched as part of the `juno_bringup` launch file alongside the microphone, transcriber, and TTS nodes.

The FastAPI backend subscribes to `/camera/image_raw` through the `RosJupiterInterface` class. Each time a frame arrives, the `_camera_callback` method converts the ROS image message to an OpenCV BGR array using `cv_bridge` and stores it as `self.latest_frame`. The backend retrieves the most recent frame by calling `robot.get_camera_frame()`, which returns this stored array.

The backend's `_emotion_monitor_loop` asyncio task polls `get_camera_frame()` every 3 seconds (configurable via the `JUNO_EMOTION_UPDATE_SECONDS` environment variable) and passes the retrieved frame to the `EmotionDetector`. This polling interval is intentionally slower than the 30 Hz camera rate because emotion states change slowly and continuous polling would waste CPU resources without improving accuracy.

```
camera_node ──/camera/image_raw──► RosJupiterInterface._camera_callback
                                           │ stores: self.latest_frame
                                           ▼
                              robot.get_camera_frame()  [every 3 s]
                                           ▼
                              EmotionDetector.predict_from_frame(frame)
                                           ▼
                              robot_state.set_emotion(emotion)
                                           ▼
                              /ws/status WebSocket → Dashboard
```

`[Screenshot: rostopic hz /camera/image_raw showing ~30 Hz during robot lab session]`

---

### Emotion Detection Pipeline

The `EmotionDetector` class, located in `backend/src/vision/emotion_detector.py`, classifies each frame into one of five operational states defined by the project: `Happy`, `Neutral`, `Tired`, `Stressed`, and `Frustrated`. These states are represented as the `EmotionState` enum in `backend/src/core/models.py`.

The current prototype uses a weighted mock predictor rather than a trained convolutional neural network (CNN). In this approach, the detector randomly selects from a weighted list of the five emotion states, with `Neutral` being the most likely outcome to simulate realistic baseline behaviour. The mock predictor was chosen for the final prototype because it ensures stable, predictable operation during the demonstration without depending on a trained model file, specific hardware compute capabilities, or precise lighting conditions.

The mock prediction is passed through an `EMAFusion` smoother, which applies an Exponential Moving Average (EMA) directly to the five-class probability distribution rather than to discrete labels. At each frame, the running estimate is updated as:

> P_t = α × P_juno + (1 − α) × P_{t-1}

where α = 0.30 gives recent frames 1.4× more weight than older frames while preserving uncertainty information across the window. Initialising P_{t-1} as a Neutral distribution means the system starts in a safe, predictable state.

The smoothed probability distribution is then passed to the `HysteresisStateMachine`, which commits a new emotion label only after it has been the argmax of the distribution for at least 45 consecutive frames (approximately 1.5 seconds at 30 Hz). This prevents the displayed state from flickering between adjacent emotions, such as Neutral and Tired, due to momentary expression changes. A state transition is only recorded and broadcast when the candidate emotion has held its lead for the full dwell period.

This two-stage approach — EMA on probability distributions followed by hysteresis — is strictly better than the simpler majority-vote smoother because it retains confidence information, weights recent evidence more heavily, and explicitly controls the minimum persistence required before a state change is accepted.

---

### Dashboard Emotion Display

The estimated emotion state is included in every broadcast from the `/ws/status` WebSocket endpoint, which the React dashboard consumes at approximately 1 Hz. The `StatusPanel` component displays the `current_emotion` field in real time without requiring a page reload. During active mode, the emotion label is visible alongside the robot's current mode and last spoken response.

`[Screenshot: Dashboard Status Panel in ACTIVE mode showing current_emotion field]`

The emotion field is part of the `RobotStatus` Pydantic model, which serialises to JSON and is broadcast by the `_ws_status` WebSocket handler in `app.py`. This path is fully functional in both mock mode (laptop development) and ROS mode (robot deployment).

---

### Emotion-Aware Break Recommendation

The `BreakRecommender` class in `backend/src/productivity/break_recommender.py` translates the current `EmotionState` into a contextually appropriate suggestion. It is called by the `ResponseGenerator` when the user's intent is `REQUEST_BREAK` or `ASK_STATUS`. The mapping from emotion to suggestion is as follows:

- **Tired:** Recommends a 5-minute break before continuing.
- **Stressed:** Encourages prioritising the nearest deadline and starting with a short study session.
- **Frustrated:** Suggests pausing and breaking the current task into smaller steps.
- **Happy:** Affirms the user's positive state and encourages continuing.
- **Neutral:** Offers to help with schedule, timer, or task planning.

The emotion state used by the `ResponseGenerator` is retrieved from `robot_state.snapshot()["current_emotion"]`, which is set by the emotion monitor loop. This creates a closed feedback path: the camera informs the emotion estimate, the estimate informs the response, and the response reaches the user through both TTS (spoken output on the robot) and the dashboard command panel.

`[Screenshot: Dashboard showing emotion-aware break suggestion in response panel]`

---

### Limitations

The current implementation has the following limitations, which are presented honestly and without overstatement.

**Mock predictor, not real recognition:** The prototype uses a weighted random selection rather than a trained CNN. This means the system does not read the user's actual facial expression; it simulates one. Real emotion recognition would require a CNN trained on facial expression data, such as the Mini-Xception model trained on FER2013, combined with OpenCV face detection. The full CNN pipeline design is documented in `docs/technical_requirements_emotion.md` and is planned as future work.

**Not a diagnostic tool:** The emotion labels used by JUNO Assist — Tired, Stressed, Frustrated, Happy, and Neutral — are operational categories designed to adapt the robot's responses to the user's visible state. They are not medical assessments, psychological diagnoses, or measures of internal mental health. Any statement the system makes about the user's emotion is an estimate of visible expression only, under normal lighting conditions.

**Face detection dependency:** In the real CNN path, emotion classification depends on successful face detection. If the user is not looking directly at the camera, is in poor lighting, or is too far from the camera, face detection will fail. In this case, the EMA smoother is designed to retain the last known distribution rather than reset, which maintains a reasonable estimate while the face is temporarily unavailable.

**Camera access during demo:** Camera integration depends on the robot session. If the camera topic is unavailable during the demonstration, the system falls back to mock mode transparently, allowing the rest of the demonstration to proceed normally. The dashboard will still display a simulated emotion state.

---

### Future Work

The proposed upgrade path for the real emotion recognition pipeline includes:

1. **Face detection:** Replace the mock predictor with OpenCV DNN face detection using the ResNet-SSD model (`res10_300x300_ssd_iter_140000.caffemodel`), which handles partial occlusion and varied lighting better than Haar cascades.
2. **CNN inference:** Run the Mini-Xception model (approximately 2 MB, ~15 ms/frame on CPU) on the detected face region.
3. **Class remapping:** Project the 7-class FER2013 output to the 5 Juno emotion classes using a fixed projection matrix encoding domain knowledge about which standard emotions correspond to each Juno state (e.g., FER `Sad` maps to Juno `Tired` because fatigue manifests as low-arousal negative affect).
4. **EMA + Hysteresis smoothing:** The same `EMAFusion` and `HysteresisStateMachine` components already implemented in the prototype would be used with real CNN outputs without modification.

This upgrade path is fully designed and documented. It was not implemented in the current prototype due to the priority of delivering a stable, reliable demonstration system within the available robot access time.

---

### Evidence Summary

| Item | Evidence |
|---|---|
| Camera topic active | `rostopic hz /camera/image_raw` showing ~30 Hz `[Screenshot]` |
| Emotion state on dashboard | Status Panel screenshot in active mode `[Screenshot]` |
| Break recommendation working | Command panel response screenshot `[Screenshot]` |
| Unit tests passing | `pytest tests/ -v` output `[Screenshot]` |
