# JUNO Assist Project Manual and Scaled Demo Plan

## Project Title

**JUNO Assist: Emotion-Aware Personal Daily Assistant Robot for Student Productivity**

## Project Context

JUNO Assist is a human-robot interaction prototype built around a Jupiter/Juno-style robot. The project targets a realistic student problem: university students often manage classes, assignments, tests, deadlines, and long study sessions with limited support. JUNO Assist acts as a small personal assistant that can be woken by the user, answer academic productivity questions, show a dashboard, estimate the user's visible emotional state, and suggest breaks or study actions.

The current repository already contains three main layers:

1. **Backend assistant logic** using FastAPI, SQLite, rule-based NLP, state management, timer handling, reminder handling, emotion state handling, and robot interface abstraction.
2. **React dashboard** showing robot status, emotion state, schedule, reminders, timer, command input, and quick actions.
3. **ROS robot integration** with camera, microphone, speech transcription, text-to-speech, and a bringup launch structure.

The intended final demonstration should be a reliable robot-assisted productivity workflow rather than a fully autonomous mobile robot. This is important because the team only has around 4 hours of physical robot access per week and only 2-3 weeks left.

## Verified Codebase Summary

The repository currently supports the following functions:

| Area | Verified Files | Current Capability |
|---|---|---|
| Backend API | `backend/src/api/app.py` | Central command processing, dashboard API, WebSocket status stream, startup tasks, robot mode transitions. |
| Wake/confirmation | `backend/src/activation/` | Detects “Hey, John” and requires user confirmation before active mode. |
| NLP | `backend/src/nlp/intent_classifier.py`, `response_generator.py` | Rule-based intent detection for schedule, deadline, timer, reminder, music, break, status, sleep. |
| Speech output | `backend/src/speech/text_to_speech.py`, `src/language_pkg/scripts/tts_node.py` | Backend can publish responses to robot/ROS TTS topic. |
| Speech input | `backend/src/robot/ros_jupiter_interface.py`, `src/language_pkg/scripts/transcriber.py` | ROS transcript topic can feed spoken text into the same command pipeline as dashboard input. |
| Vision | `backend/src/vision/emotion_detector.py`, `emotion_smoothing.py`, `src/perception_pkg/scripts/camera_node.py` | Camera ROS topic exists; backend has mock emotion detection and smoothing. Full CNN emotion recognition is not implemented yet. |
| Productivity | `backend/src/productivity/`, `backend/src/calendar_module/` | Timer, break recommendation, music response, SQLite schedule/reminders. |
| Dashboard | `dashboard/src/App.jsx`, components | User-facing visual interface for status, response, schedule, reminders, timer, and commands. |
| ROS | `src/juno_bringup/launch/juno_robot.launch`, `src/perception_pkg`, `src/language_pkg` | ROS nodes for camera, microphone, transcriber, and TTS are organized as catkin packages. |

## Honest Scope Assessment

The project idea is strong, but the full version is too advanced for the remaining robot access time if the team tries to complete all of these at once:

- full physical robot navigation,
- robust real-time speech recognition in noisy environments,
- trained CNN facial emotion recognition,
- online LLM integration,
- production-quality robot dashboard opening,
- full autonomous behaviour.

The recommended approach is to **scale down to a stable MVP** while still satisfying every rubric item. The MVP should prioritize a complete interaction loop over advanced AI complexity.

## Recommended Scaled MVP

### Final Demo Goal

The final demo should show:

1. User wakes JUNO with “Hey, John”.
2. JUNO asks for confirmation.
3. User confirms with “Yes”.
4. JUNO becomes active and responds by voice.
5. Dashboard shows active state, current emotion estimate, schedule, reminders, and timer.
6. User asks about schedule/deadlines/timer/breaks.
7. JUNO responds using TTS and updates the dashboard.
8. Camera/emotion module shows either real camera feed integration with mock emotion classification, or a simple visible emotion estimate if time permits.
9. RQT graph shows ROS camera, microphone, transcription, TTS, and backend-related topics.

This is achievable and covers HRI, ROS, speech, vision, NLP, dashboard, and manual/report expectations.

## What to Keep

Keep these as core deliverables:

- Wake word and confirmation flow.
- Two-way speech interaction: user speech/text input and robot speech output.
- Dashboard as visual HRI feedback.
- ROS camera and microphone topics.
- ROS speech transcript topic.
- ROS TTS topic.
- Rule-based NLP intent classification.
- Schedule, deadlines, reminders, study timer, and break recommendation.
- Mock or simple emotion detection with smoothing.
- RQT graph screenshot showing the ROS nodes and topics.

## What to Defer or Present as Future Work

Defer these unless the core demo is already stable:

- Robot navigation or physical movement.
- Complex gestures.
- Full CNN emotion model training.
- Cloud LLM dependency.
- Full calendar API integration.
- Perfect speech recognition in all environments.
- Multi-user support.

These can be described in the report as future improvements.

## Rubric Fulfilment Plan

### 1. HRI Elements (10%)

JUNO Assist includes clear human-robot interaction through:

- wake command interaction,
- confirmation before activation,
- spoken robot responses,
- dashboard visual feedback,
- emotion-aware break suggestions,
- study support commands,
- safe fallback when the robot does not understand.

The HRI design is suitable because the robot does not act unexpectedly. It waits in idle mode, asks for confirmation, and gives understandable responses.

### 2. Codes and Manual (5%)

The repository is organized into backend, dashboard, ROS packages, and documentation. This manual explains the project purpose, reduced scope, architecture, demo flow, and rubric mapping.

Recommended documentation deliverables:

- this manual,
- README project overview,
- ROS integration guide,
- final report,
- demo video link,
- GitHub link.

### 3. ROS Development (20%)

The ROS side should be presented as the robot integration layer. The important ROS components are:

| ROS Package | Role |
|---|---|
| `perception_pkg` | Publishes camera frames and microphone audio. |
| `language_pkg` | Converts microphone audio into speech transcript and performs TTS output. |
| `juno_bringup` | Starts the robot-facing nodes together. |
| Backend ROS bridge | Subscribes to transcript/camera topics and publishes TTS/LED state. |

Expected ROS topics:

| Topic | Purpose |
|---|---|
| `/camera/image_raw` | Robot camera frames for vision/emotion input. |
| `/audio/raw` | Raw microphone audio. |
| `/speech/transcript` | Recognized user speech text. |
| `/juno/tts` | Robot speech output text. |
| `/juno/led_state` | Optional robot status feedback. |

This is enough ROS development for the course because the project demonstrates perception input, speech input, speech output, and backend decision integration.

### 4. RQT Graph (5%)

The final report should include an RQT graph screenshot showing the ROS nodes and topics. The expected graph should include:

- camera node publishing `/camera/image_raw`,
- microphone node publishing `/audio/raw`,
- ASR/manual transcript source publishing `/speech/raw_transcript`,
- Whisper Tiny transcriber publishing `/speech/transcript`,
- backend bridge subscribing to `/speech/transcript` and `/camera/image_raw`,
- backend bridge publishing `/juno/tts`,
- TTS node subscribing to `/juno/tts`.

If the backend bridge does not appear clearly in RQT due to runtime environment issues, the team can still show the ROS-side graph and explain the backend bridge separately in the architecture diagram.

### 5. Report Context

The report should explain:

- student productivity problem,
- why a personal assistant robot is useful,
- why wake-confirmation interaction improves safety,
- how emotion estimate supports break recommendation,
- how ROS connects robot sensors to the assistant backend,
- limitations due to limited physical robot access.

### 6. Code Organization

The codebase is already reasonably organized:

```text
backend/      Assistant logic, APIs, NLP, speech, vision, productivity, robot interface
dashboard/    React user dashboard
src/          ROS catkin packages for perception, language, and bringup
docs/         Project documentation and integration notes
```

For the final submission, avoid adding unrelated experiments into these folders. Keep demo-specific notes in `docs/`.

### 7. Vision Integration

The safest target is:

- use the ROS camera topic as the real vision input,
- pass camera frames to the backend through the ROS bridge,
- use the current emotion detector as a mock/simple classifier,
- show smoothed emotion state on the dashboard,
- explain that the prototype estimates visible expression only and is not a medical diagnosis.

If time allows, a simple OpenCV face detector can be added, but full CNN emotion recognition should not be the main dependency for the final demo.

### 8. Speech Interaction: Two-Way

The project should demonstrate two-way speech:

- **User to robot:** microphone/transcriber or dashboard command input sends text to the backend.
- **Robot to user:** backend response is sent to TTS and spoken aloud.

The dashboard command box can remain as a backup input method during demonstration. This reduces risk if the robot microphone or environment noise causes recognition issues.

### 9. NLP/LLM Element

The current project uses rule-based NLP instead of a large language model. This is acceptable if presented correctly:

- It classifies intent from natural phrases.
- It extracts timer duration.
- It generates context-aware responses based on schedule, deadline, and emotion state.
- It is deterministic and reliable for a short robotics demo.

If the rubric specifically expects an LLM element, the report can describe this as a “lightweight NLP module” and optionally list future LLM integration as an extension. Do not depend on a cloud LLM for the final demo unless the base system is already stable.

### 10. Notable Mention

Good points to highlight:

- Safe wake-confirmation interaction.
- ROS and web-dashboard hybrid architecture.
- Emotion-aware break recommendation.
- Robot interface abstraction that allows mock mode and ROS mode.
- Practical fallback design for limited robot access.

### 11. Title, Video Link, GitHub Link

The final report should include:

- project title,
- short demo video link,
- GitHub repository link,
- team member names,
- branch or commit used for final demo.

### 12. Extra/Special Manual

This file can be submitted as the extra manual. It explains not only how the project works, but also how the scope was reduced to match time constraints.

### 13. Extra RQT

For extra RQT evidence, include:

- full RQT graph screenshot,
- close-up screenshot of speech topics,
- close-up screenshot of camera topic,
- short explanation of each node/topic in the report.

## Final Demo Script

Use this sequence for the demo video and live presentation:

1. Show the robot and dashboard in idle mode.
2. User says or enters “Hey, John”.
3. JUNO asks for confirmation.
4. User says or enters “Yes”.
5. JUNO becomes active and the dashboard updates.
6. User asks about today’s schedule.
7. JUNO reads the schedule response aloud.
8. User asks for a study timer.
9. Dashboard timer starts.
10. User asks what they should do now or asks for a break.
11. JUNO uses current emotion state and workload to recommend a short break or next task.
12. Show RQT graph with camera, audio, transcript, and TTS topics.
13. End by putting JUNO back to sleep.

## Minimum Success Criteria

The project should be considered successful if the team can demonstrate:

- stable dashboard,
- stable backend command pipeline,
- at least one ROS camera or audio topic active,
- two-way speech or speech-equivalent interaction,
- robot response through TTS,
- visible emotion state on dashboard,
- one schedule/deadline response,
- one timer response,
- RQT graph evidence.

## Risk Management

| Risk | Recommended Backup |
|---|---|
| Robot microphone fails | Use dashboard command input while still showing ROS microphone/transcript design. |
| Camera device path changes | Use laptop camera or mock emotion state. |
| TTS package fails | Use terminal/log response plus dashboard response, then explain intended `/juno/tts` path. |
| ROS environment unstable | Record RQT evidence during a successful lab session. |
| Speech recognition inaccurate | Use short commands only: “Hey John”, “Yes”, “What do I have today”, “Set timer”. |
| Not enough robot time | Prepare and test in mock/laptop mode before each robot session. |

## Recommended Work Plan for 2-3 Weeks

### Week 1

- Stabilize backend and dashboard in mock mode.
- Confirm wake, confirmation, schedule, timer, reminder, break, and sleep flows.
- Prepare final demo script.
- Clean generated files from Git tracking.

### Week 2

- Test ROS camera, microphone, transcript, and TTS nodes on the robot.
- Capture RQT graph screenshots.
- Record a short successful robot interaction video, even if simple.

### Week 3, if available

- Improve polish only: dashboard text, report screenshots, video editing, presentation flow.
- Do not add major new features unless the MVP is already reliable.

## Final Submission Evidence Checklist

To make the submission strong, the final report/video should not only describe the system; it should prove that each rubric item is satisfied. The team should include the following evidence:

| Rubric Item | Evidence to Include |
|---|---|
| HRI Elements | Screenshot/video of wake command, confirmation prompt, active mode, spoken response, dashboard feedback, and safe sleep mode. Explain why confirmation prevents accidental activation. |
| Codes and Manual | GitHub repository link, clean folder structure screenshot, this manual, ROS guide, and clear explanation of how each module connects. |
| ROS Development | RQT graph, ROS topic table, launch/package explanation, and short evidence that camera/audio/transcript/TTS topics exist. |
| RQT Graph | Full RQT graph screenshot plus a labelled explanation of each node/topic in the report. |
| Report Context | Clear problem statement: student productivity support under real robot/time constraints. Explain why the scaled MVP is realistic and reliable. |
| Code Organization | Show `backend/`, `dashboard/`, `src/`, and `docs/` structure. Mention `.gitignore` cleanup for generated files. |
| Vision Integration | Show camera topic path and dashboard emotion state. Be honest that current emotion classification is mock/simple but integrated through the vision pipeline. |
| Speech Interaction (2-way) | Show user input through speech/transcript or dashboard backup, and robot output through `/juno/tts`/TTS/dashboard response. |
| NLP/LLM Element | Explain rule-based NLP with examples of intents and responses. If asked about LLM, frame it as a future upgrade for open-ended dialogue. |
| Notable Mention | Highlight hybrid ROS + web dashboard design, hardware abstraction layer, fallback mode, and emotion-aware break recommendation. |
| Title/Video/GitHub | Place all three clearly on the first or last page of the report. |
| Extra Manual/RQT | Submit this manual and extra RQT/topic screenshots as appendix evidence. |

## Final Report Structure Recommendation

Use this structure for the final report:

1. **Title Page** — project title, team members, GitHub link, video link.
2. **Problem Context** — student workload/productivity issue and why HRI is useful.
3. **System Overview** — architecture diagram and explanation of backend, dashboard, ROS.
4. **HRI Design** — wake word, confirmation, active/sleep modes, dashboard feedback, safety.
5. **ROS Development** — packages, nodes, topics, launch file, ROS bridge.
6. **Vision Integration** — camera topic, backend frame path, emotion state, limitation.
7. **Speech Interaction** — user speech/transcript input and robot TTS output.
8. **NLP/LLM Element** — intent classifier, response generator, future LLM extension.
9. **Demo Flow and Results** — screenshots from dashboard, RQT, robot demo.
10. **Limitations and Future Work** — limited robot access, mock emotion model, speech reliability.
11. **Conclusion** — why the scaled MVP still fulfils the robotics/HRI objective.
12. **Appendix** — manuals, extra RQT screenshots, topic tables, test evidence.

## Grading Risk Notes

The main risk is overclaiming. For a strong submission, the team should phrase the project as a **working integration prototype** rather than claiming full production-grade emotion recognition or open-domain AI. Strong marks should come from:

- a complete end-to-end interaction loop,
- clear ROS evidence,
- clear HRI justification,
- clean code organization,
- honest scope control,
- reliable demo video.

## Final Recommendation

The project should not be expanded further. It is already broad enough for the rubric. The best strategy is to present JUNO Assist as a **practical HRI and ROS integration prototype** with a reliable scaled demo. Focus on demonstrating the full loop:

**human command → ROS/input layer → backend NLP/state logic → robot speech response → dashboard feedback → RQT evidence.**
