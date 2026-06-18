# JUNOAssist — Demo Video Remediation Plan

**Purpose:** This document outlines how the demonstration video will be revised in response to the lecturer's feedback (17 June 2026). The core comments were that the vision component "was not really there," that static images were used instead of live faces, that the tiredness-detection feature was not shown, that music selection appeared manual rather than autonomous, and that the demonstration lacked a cohesive storyboard.

The revised video will follow the storyboard already documented in the project report (Section 2.2), presented as a single continuous scenario rather than a list of disconnected features.

---

## Priority 1 — Directly addresses the lecturer's feedback

1. **Use live facial recognition, not static images.** The underlying vision pipeline already supports live camera input. Before recording, the team will test recognition accuracy under the actual lighting conditions to be used on the day, since the classifier requires reasonably well-lit, clear frames. If live accuracy still proves insufficient on the day, the video will rely on the reliable speech-based emotion detection instead of repeating the static-image approach.

2. **Visibly demonstrate the tiredness-detection feature.** This was specifically flagged as an unshowcased but valid feature. The recording will include a clear moment where the user states they are tired, and the dashboard's emotion display and the robot's resulting break recommendation will both be clearly visible on screen.

3. **Present music selection as an autonomous recommendation.** The video will show the robot identifying the user's emotional state and recommending music in response, framed as the robot's decision being confirmed by the user, rather than the user independently selecting a track.

4. **Tell one continuous story.** The video will follow a single narrative — a student under deadline stress being supported by JUNOAssist — using the sequence already laid out in the report's storyboard: login, wake word, confirmation, tiredness detected via speech, movement break, stress detected via camera, calming music, schedule and timer support, and shutdown.

---

## Priority 2 — Strengthens overall presentation

5. **Open with the problem statement.** A brief introduction (on screen or narrated) will state the problem the project addresses — high reported stress levels among Malaysian university students — before any feature demonstration begins, so the audience understands the purpose behind each feature shown.

6. **Use the updated project title.** The video will use the full title from the report, *"JUNOAssist: A Voice and Vision Fused Companion for Detecting Student Stress and Fatigue,"* to clearly convey the project's specific contribution, addressing the lecturer's comment that the original title did not do so.

7. **Ensure the dashboard is clearly readable on camera.** The recording will frame the dashboard so emotion indicators and other key information are large enough to read on video, independent of any styling improvements already made to the interface.

---

## Priority 3 — Time permitting

8. On-screen captions naming the active module (for example, "Speech Emotion Detector") at key moments, to help the viewer follow the system's reasoning.

---

## Sequencing note

This recording will take place after the related codebase changes (see the codebase remediation plan) are completed, so the video reflects the improved, more autonomous version of the system rather than requiring a second re-shoot.
