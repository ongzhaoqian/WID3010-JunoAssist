# JUNOAssist — Codebase Remediation Plan

**Purpose:** This document records the specific code changes planned in response to the lecturer's feedback session (17 June 2026), where the project scored 20/40. It maps each piece of feedback to the relevant source file and the concrete change being made, so progress can be tracked and reviewed.

**Key finding:** Several capabilities the lecturer asked for — tiredness detection and a corresponding break recommendation — were already implemented in the backend before this review, but were not visible in the demo or the dashboard. The remediation plan below is therefore focused on surfacing and connecting existing, working logic rather than building new models from scratch.

---

## Priority 1 — Directly addresses the lecturer's feedback

### 1. Surface the tiredness/break recommendation on the dashboard

The system already detects tiredness from speech (e.g. "I'm tired", "I'm exhausted") and generates an appropriate break suggestion via `backend/src/productivity/break_recommender.py`. This is currently spoken aloud by the robot but not shown anywhere on the dashboard screen.

**Change:** Add a dashboard panel that displays the current break/wellness recommendation whenever the system detects sadness or stress, so the feature the lecturer asked to see is visibly demonstrated, not just spoken.

### 2. Make the music recommendation appear autonomous

At present, the dashboard requires the user to press a "Play by Emotion" button (`dashboard/src/components/MusicPanel.jsx`) before a playlist is selected. This matches the lecturer's specific criticism that "the user still had to manually select" music rather than the robot recommending it on its own.

**Change:** Trigger music selection automatically when the system's smoothed emotion state changes (using the existing `EMAFusion` and `HysteresisStateMachine` logic in `backend/src/vision/emotion_fusion.py`), so the recommendation happens without requiring a manual click.

### 3. Validate live facial emotion recognition before re-filming

The facial expression classifier (`backend/src/vision/facial_expression_classifier.py`) already performs face detection and classification on live camera frames, not static images. The previous demo used static pictures because live recognition was unreliable on real faces due to a skewed training dataset, as explained to the lecturer.

**Change:** Test the live pipeline under the actual recording conditions before filming. If accuracy is still insufficient, the demo will rely on the already-reliable speech-based emotion detection path instead of disguising a known limitation.

---

## Priority 2 — Strengthens the project narrative

### 4. Reframe the study timer honestly

The current timer (`dashboard/src/components/TimerPanel.jsx`) is a simple start/stop countdown, which the lecturer correctly identified as not constituting genuine focus monitoring. Rather than building new posture- or attention-tracking technology under time pressure, the timer will be reframed and connected to the stress/break detection flow it already integrates with — presented honestly as a recovery and study-session tool, not a focus-monitoring system.

### 5. Improve the visibility of the emotion indicator

The dashboard's emotion display (`dashboard/src/components/StatusPanel.jsx`) will be updated with colour-coded states (for example, red for stress, blue for tiredness/sadness, green for happiness) so the indicator is clearly visible at a glance, addressing the lecturer's comment on poor contrast and placement.

---

## Priority 3 — Time permitting

### 6. Link the break recommendation to the fitness game

When a break is recommended, offer a direct prompt to launch the existing fitness game feature, so the wellness flow and the movement-break feature work together as one connected experience rather than two separate features.

---

## Out of scope for this revision

- A full rename of the project across all source files. The report's title has already been updated to reflect the project's specific contribution; renaming internal code identifiers is cosmetic and does not affect the demonstrated functionality.
- Retraining the facial emotion recognition model to fix the dataset bias. Given the available time, the project will rely on the speech-based detection path, which does not have this limitation, while being transparent about the vision model's current constraint.

---

## Verification before submission

Run the existing automated test suite to confirm no regressions were introduced:

```
python -m pytest tests/test_intent_classifier.py tests/test_dashboard_productivity_api.py tests/test_vision_stream_api.py -q
```
