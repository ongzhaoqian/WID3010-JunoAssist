# JUNO Assist Project Manual and Scaled Demo Plan

## Read This First

This document is the **submission and demo planning guide**: how the team should present JUNO Assist for the WID3010 assessment.

Use this file when you need:

- final demo scope and script
- rubric fulfilment plan
- report structure guidance
- team responsibilities and task ownership
- evidence checklist for screenshots, video, ROS graph, and testing proof

If you are trying to run the robot terminals, use `docs/ros_integration_guide.md`. If you need system requirements or API design, use `docs/product_requirements.md`.

## Quick Navigation

| Need | Go to |
|---|---|
| Understand final demo scope | Recommended Scaled MVP / Final Demo Goal |
| Check rubric coverage | Rubric Fulfilment Plan |
| Follow the live demo sequence | Final Demo Script |
| Collect proof for submission | Final Submission Evidence Checklist |
| Assign team work | Appendix A1: Team Task Distribution |
| Use preserved report draft text | Appendix A2: Vision Report Section Draft |

---

## Q2 Checklist: ROS Workspace Setup

**Status:** The codebase now has the expected ROS/catkin workspace structure. The key improvement is to show clear setup evidence instead of only saying the workspace exists.

| Q2 Requirement from PDF | Current Evidence | Evidence to Capture |
|---|---|---|
| Boot into Ubuntu system | Current development environment is Ubuntu WSL; robot/lab machine should also be Ubuntu | Screenshot of `lsb_release -a` and `python3 --version` |
| Create a folder as ROS workspace | Project root: `/home/johnnyrobs19/WID3010-JunoAssist` | Screenshot of `pwd`, `ls`, and `ls src` |
| Turn folder into catkin workspace | `.catkin_workspace` and `src/CMakeLists.txt` exist | Screenshot of `catkin_make` output showing source/build/devel spaces |
| ROS packages inside workspace | `src/perception_pkg`, `src/language_pkg`, `src/juno_bringup` | Screenshot of `find src -maxdepth 2 -name package.xml -print` |
| Load workspace when opening terminal | Shell config should source ROS + workspace setup | Screenshot of `.bashrc`/`.zshrc` source lines and a new terminal showing `ROS_PACKAGE_PATH` |
| Verify package discovery | `rospack find` works after sourcing workspace | Screenshot of `rospack find perception_pkg`, `language_pkg`, `juno_bringup` |

### Q2 Commands to Capture as Evidence

For local WSL development using the micromamba ROS Noetic environment:

```bash
micromamba activate ros_env
cd ~/WID3010-JunoAssist
source ~/micromamba/envs/ros_env/setup.bash
catkin_make -DCMAKE_POLICY_VERSION_MINIMUM=3.5
source devel/setup.bash

rosversion -d
echo $ROS_PACKAGE_PATH
rospack find perception_pkg
rospack find language_pkg
rospack find juno_bringup
```

For the physical robot/lab Ubuntu machine with standard ROS Noetic:

```bash
cd ~/WID3010-JunoAssist
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash

rosversion -d
echo $ROS_PACKAGE_PATH
rospack find perception_pkg
rospack find language_pkg
rospack find juno_bringup
```

### Recommended Auto-Source Lines

For WSL/local development:

```bash
alias juno_rosstart='export PYTHONPATH="" && micromamba activate ros_env && cd ~/WID3010-JunoAssist && source ~/micromamba/envs/ros_env/setup.bash && source devel/setup.bash'
```

For the robot/lab machine:

```bash
source /opt/ros/noetic/setup.bash
source ~/WID3010-JunoAssist/devel/setup.bash
```

Include both the command outputs and a short explanation that the workspace contains three ROS packages: `perception_pkg` for camera/audio input, `language_pkg` for ASR/TTS, and `juno_bringup` for launching the robot-side nodes.

---

## Q3 Checklist: ROS Application and APIs

**Status:** The codebase has a strong Q3 foundation, but the final submission still needs clear evidence: screenshots, terminal outputs, API examples, and explanation of how each ROS topic connects sensor input to robot/backend decision-making.

| Q3 Requirement from PDF | Current Codebase Evidence | What to Show |
|---|---|---|
| Develop robotics application on ROS workspace | `src/perception_pkg`, `src/language_pkg`, `src/juno_bringup` | Screenshot of `catkin_make` success and `roslaunch juno_bringup juno_robot.launch` running |
| Identify packages to interface with robot | `perception_pkg` for camera/mic, `language_pkg` for ASR/TTS, `juno_bringup` for launch | Report table listing each package, its nodes, and purpose |
| Serve AI techniques for proposed robot application | Whisper Tiny ASR, Moonshine fallback, emotion detector, rule-based intent classifier | Explain speech-to-text, emotion estimation, and intent/reasoning pipeline |
| Design ROS APIs: topics/publishers/subscribers | `/camera/image_raw`, `/audio/raw`, `/speech/transcript`, `/juno/tts`, `/juno/tts_done` | Include topic table with message type, publisher, subscriber, sample input/output |
| Connect sensor output to decision-making | Backend subscribes `/speech/transcript` and `/camera/image_raw`, then updates robot state/dashboard/TTS | Show command flow: speech → transcript → backend intent → response → `/juno/tts` |
| Unit test each ROS API | `rostopic hz`, `rostopic echo`, manual transcript publish, TTS test publisher | Capture terminal screenshots for each API test |
| Successful code execution | launch file and backend runtime | Screenshot 4 terminals running plus dashboard active |

### Q3 ROS API Evidence Table to Include in Report

| API / Topic | Publisher | Subscriber | Message Type | Purpose | Example Input | Expected Output |
|---|---|---|---|---|---|---|
| `/camera/image_raw` | `camera_node.py` | backend ROS bridge / optional camera listener | `sensor_msgs/Image` | Sends camera frames for dashboard stream and emotion monitoring | Camera frame from Jupiter webcam | `rostopic hz /camera/image_raw` shows stable frame rate |
| `/audio/raw` | `microphone_node.py` | `transcriber.py` | `std_msgs/Float32MultiArray` | Sends raw microphone audio for speech recognition | User says “Hey, John” | Audio samples published at 16 kHz |
| `/speech/transcript` | `transcriber.py` | backend ROS bridge | `std_msgs/String` | Sends recognised speech to backend decision-making | `"What is my schedule today?"` | Backend classifies intent and generates response |
| `/speech/raw_transcript` | `example_transcriptor.py` or manual `rostopic pub` | `transcriber.py` | `std_msgs/String` | Manual fallback to bypass ASR during testing | `"Hey, John"` | Relayed to `/speech/transcript` |
| `/juno/tts` | backend ROS bridge / test publisher | `tts_node.py` | `std_msgs/String` | Sends robot response text to speech node | `"JUNO Assist is now online."` | Robot/laptop speaker speaks response |
| `/juno/tts_done` | `tts_node.py` | `transcriber.py` | `std_msgs/String` | Signals that speech output has completed | TTS finishes speaking | ASR resumes listening |
| `/juno/led_state` | backend ROS bridge | robot LED adapter if available | `std_msgs/String` | Optional robot status feedback | `"active"` | Robot LED/status state changes if hardware is connected |

### Q3 Commands to Capture as Evidence

```bash
# Build and launch ROS application
catkin_make
source devel/setup.bash
roslaunch juno_bringup juno_robot.launch

# Verify APIs
rostopic list
rostopic hz /camera/image_raw
rostopic echo /speech/transcript
rostopic echo /juno/tts
rostopic echo /juno/tts_done

# Manual API test
rostopic pub /speech/raw_transcript std_msgs/String "data: 'Hey, John'"
rostopic pub /speech/raw_transcript std_msgs/String "data: 'Yes'"
rostopic pub /speech/raw_transcript std_msgs/String "data: 'What is my schedule today?'"

# Direct TTS API test
rosrun language_pkg tts_test_publisher.py "Hello, I am JUNO and my speech node is working."
```

For Q3, the code is mostly there. The remaining work is to **prove it clearly** with API tables, command outputs, screenshots, and successful demo execution.

---

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

---

# Appendix A: Preserved Team Responsibilities and Report Draft Notes


## Appendix A1: Preserved from `docs/team_task_distribution.md`

## JUNO Assist Team Task Distribution

### Purpose

This task distribution is based on the current codebase, branch history, and the scaled MVP plan in `docs/project_manual_scaled_demo.md`. The goal is to finish a reliable 5-person group project within limited robot access time: about 4 hours per week for 2-3 weeks.

The recommended final scope is:

> **Human command → ROS/input layer → backend NLP/state logic → robot TTS response → dashboard feedback → RQT graph evidence.**

Do not expand into full robot navigation, complex LLM integration, or full CNN emotion training unless the MVP is already stable.

---

### Codebase and Branch Review Summary

#### Branch/commit evidence reviewed

| Branch / Area | Evidence from repo | Main work shown |
|---|---|---|
| `mackwongyy` | commits by Mack/Wong Yoong Yee including `915cad1`, `4c5bcfa`, `0d9f42b`, `ddb7021` | Initial frontend/backend project template, README updates, overall project framing. |
| `mackwongyy_integration` | commit `b86a1f4` | First attempt at integrating robot code with existing frontend/backend code; also cleaned duplicated repository work. |
| `anas` | commits leading to `389b4fe` | ROS/catkin structure, perception/language packages, backend ROS bridge, launch file, TTS node, transcriber publishing `/speech/transcript`. |
| `jon_integration` | current branch | Product/manual docs, scaled demo plan, `.gitignore` cleanup, integration planning. |
| `main` | initial repo + README | Base repository and project identity. |

#### Current code modules verified

| Layer | Existing files | Current state |
|---|---|---|
| Backend API | `backend/src/api/app.py` | Central command pipeline, wake/confirmation/active modes, REST endpoints, WebSocket status. |
| Activation | `backend/src/activation/` | Wake word and confirmation logic. |
| NLP | `backend/src/nlp/intent_classifier.py`, `response_generator.py` | Rule-based intent classification and contextual response generation. |
| Calendar/Productivity | `backend/src/calendar_module/`, `backend/src/productivity/` | SQLite schedule/reminders, timer, music/break recommendation. |
| Vision | `backend/src/vision/` | Mock emotion detector with smoothing; camera integration path exists through ROS bridge. |
| Robot interface | `backend/src/robot/jupiter_interface.py`, `ros_jupiter_interface.py` | Mock mode and ROS mode abstraction. |
| Dashboard | `dashboard/src/` | React dashboard with status, command, schedule, reminder, and timer panels. |
| ROS | `src/perception_pkg`, `src/language_pkg`, `src/juno_bringup` | Camera, microphone, transcriber, TTS, and launch file structure. |
| Docs | `docs/` and root `.md` files | Implementation plan, ROS guide, project manual, product/component/emotion requirements. |

---

### Program Component Completion Checklist

This checklist tracks the actual software components that still need to be completed, verified, or polished. The goal is to make the final project reliable, demonstrable, and clearly connected to the rubric.

#### Priority Legend

| Priority | Meaning |
|---|---|
| **Must** | Required for the final demo/submission. |
| **Should** | Strongly recommended if time permits. |
| **Optional** | Nice-to-have only after the core demo is stable. |

#### 1. Repository and Integration Hygiene

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| `.gitignore` | Updated on integration branch | Confirm correct `*:Zone.Identifier`, `build/`, `devel/`, `.venv/`, `node_modules/`, `__pycache__/`, `*.pyc` ignores. | Jon | Must |
| Tracked generated files | Some generated files still exist in older branches | Remove tracked `build/`, `devel/`, `__pycache__/`, `*.pyc` from final branch using Git cleanup. | Jon, Zhao Qian | Must |
| Final integration branch | `jon_integration` exists | Decide final branch/commit for submission and make sure all required docs/code are there. | Jon, Zhao Qian | Must |
| Branch consistency | `anas` and `mackwongyy_integration` source mostly aligned | Use final branch as source of truth; avoid reintroducing generated files from older branches. | Jon | Must |

#### 2. Backend Assistant Core

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| FastAPI app | Implemented in `backend/src/api/app.py` | Run backend locally and confirm all routes work. | Jon, Zhao Qian | Must |
| Robot mode state | Implemented: idle, confirmation, active | Verify full state flow: idle → confirmation → active → sleep/idle. | Jon | Must |
| Wake word detector | Implemented | Test with `Hey, John`, `hey john`, and wrong phrases. | Jon | Must |
| Confirmation handler | Implemented | Test `Yes` confirmation and non-confirmation fallback. | Jon | Must |
| Command pipeline | Implemented in `process_command_text()` | Verify both dashboard command and ROS transcript use same logic. | Jon, Anas | Must |
| Text-to-speech wrapper | Implemented | Confirm backend calls `tts.speak()` for key responses. | Anas, Jon | Must |
| Error/fallback responses | Basic fallback exists | Make fallback wording clear and demo-friendly. | Jon | Should |

#### 3. NLP and Response Logic

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| Intent classifier | Implemented rule-based classifier | Test supported commands: schedule, deadline, timer, reminder, music, break, status, sleep. | Jon, Zhao Qian | Must |
| Timer extraction | Implemented | Test commands like `Set a 5 minute timer` and default timer command. | Zhao Qian | Must |
| Response generator | Implemented | Confirm responses include schedule/deadline/emotion context where relevant. | Jon | Must |
| NLP/LLM report framing | Documented as rule-based NLP | Explain clearly in report; mention LLM as future work only. | Jon | Must |
| Intent tests | Test files exist | Install dependencies and run tests; fix only if failing. | Zhao Qian | Should |

#### 4. Calendar, Reminder, and Productivity Features

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| SQLite calendar service | Implemented | Confirm database initializes and sample schedule loads. | Zhao Qian | Must |
| Schedule endpoint | Implemented | Confirm dashboard displays schedule. | Zhao Qian, Mack | Must |
| Deadline endpoint | Implemented | Confirm deadline command gives meaningful response. | Zhao Qian | Must |
| Reminder endpoint | Implemented | Test adding/listing reminders from dashboard. | Zhao Qian, Mack | Should |
| Study timer service | Implemented | Confirm timer starts and dashboard countdown updates. | Zhao Qian, Mack | Must |
| Break recommender | Implemented | Confirm tired/stressed/frustrated status gives break suggestion. | Vanness, Jon | Must |
| Music service | Simple response implemented | Keep as simple response unless audio playback is stable. | Zhao Qian | Optional |

#### 5. Dashboard / Frontend

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| Dashboard app | Implemented in React/Vite | Install dependencies and confirm it runs. | Mack | Must |
| API client | Implemented in `dashboard/src/lib/api.js` | Confirm `VITE_API_BASE` works if backend is not localhost. | Mack | Must |
| Status panel | Implemented | Confirm mode/emotion/last response display correctly. | Mack | Must |
| Command panel | Implemented | Confirm typed command backup works for all demo commands. | Mack | Must |
| Schedule panel | Implemented | Confirm schedule loads from backend. | Mack, Zhao Qian | Must |
| Reminder panel | Implemented | Confirm reminders can be displayed/added. | Mack | Should |
| Timer panel | Implemented | Confirm timer countdown updates through WebSocket/status. | Mack, Zhao Qian | Must |
| Dashboard screenshots | Not yet captured | Capture idle, confirmation, active, timer, emotion screenshots. | Mack | Must |
| UI polish | Basic UI exists | Add labels/captions if needed for evaluator clarity. | Mack | Should |

#### 6. ROS Robot Integration

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| `perception_pkg` | Exists | Confirm package builds/runs on ROS machine. | Anas | Must |
| `language_pkg` | Exists | Confirm package builds/runs on ROS machine. | Anas | Must |
| `juno_bringup` | Exists | Confirm launch file starts required nodes. | Anas | Must |
| Camera node | Implemented | Verify `/camera/image_raw` publishes on robot/laptop camera. | Anas, Vanness | Must |
| Microphone node | Implemented | Verify `/audio/raw` publishes for Whisper Tiny ASR, and `/speech/raw_transcript` can still be used as a manual fallback. | Anas | Must |
| Transcriber node | Implemented | Verify `/speech/transcript` publishes text or use manual transcript backup. | Anas | Must |
| TTS node | Implemented | Verify `/juno/tts` is spoken by `pyttsx3`/`espeak`. | Anas | Must |
| Backend ROS bridge | Implemented | Run backend in ROS mode and confirm subscriptions/publishers work. | Anas, Jon | Must |
| LED state topic | Implemented as optional publisher | Show in RQT if available; otherwise document as optional. | Anas | Optional |
| RQT graph | Not yet captured | Capture full RQT graph and topic close-ups. | Anas, Zhao Qian | Must |

#### 7. Vision and Emotion Component

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| Camera input path | ROS topic and backend frame getter exist | Verify latest camera frame reaches backend in ROS mode. | Vanness, Anas | Must |
| Emotion detector | Mock/weighted detector implemented | Keep stable for demo; do not rely on heavy CNN. | Vanness | Must |
| Emotion smoothing | Implemented | Run/check smoothing test if dependencies available. | Vanness, Zhao Qian | Should |
| Dashboard emotion display | Implemented through status | Confirm emotion is visible during active mode. | Vanness, Mack | Must |
| Emotion-aware break recommendation | Implemented through response generation | Test break/status command with emotion state. | Vanness, Jon | Must |
| Real CNN emotion recognition | Documented but not implemented | Present as future work unless all core items are stable. | Vanness | Optional |
| Vision evidence | Not yet captured | Capture camera/RQT screenshot and dashboard emotion screenshot. | Vanness | Must |

#### 8. Speech Interaction Component

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| User input via dashboard | Implemented | Use as reliable backup for demo. | Mack | Must |
| User input via ROS transcript | Implemented path | Test with Whisper Tiny ASR/manual transcript fallback; if unstable, use manually published `/speech/transcript` evidence. | Anas | Must |
| Robot output via TTS | Implemented path | Confirm `/juno/tts` triggers speech. | Anas | Must |
| Two-way demo | Not yet recorded | Record user command and robot/dashboard response. | Anas, Mack | Must |
| Speech fallback plan | Documented | Use dashboard command if robot microphone fails. | Jon | Must |

#### 9. Testing and Demo Evidence

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| Backend unit tests | Test files exist | Install dependencies and run tests. | Zhao Qian | Should |
| Python syntax check | Passed locally once | Repeat after final code changes. | Jon | Must |
| Dashboard build/run check | Build failed locally because dependencies not installed | Run after `npm install` on demo machine. | Mack | Must |
| ROS runtime check | Not testable in current non-ROS environment | Test during robot session and record evidence. | Anas | Must |
| Demo script rehearsal | Draft exists | Rehearse exact commands and timing. | All | Must |
| Demo video | Not yet recorded | Record stable end-to-end demo. | Zhao Qian, Mack | Must |
| GitHub/video links | Not yet final | Add final links to report. | Zhao Qian | Must |

#### 10. Final Report and Manual Components

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| Project manual | Exists | Keep updated with final scope and evidence. | Jon | Must |
| Task distribution | Exists | Keep updated with responsibilities and component checklist. | Jon | Must |
| Report writing distribution | Exists | Every member writes assigned section. | All | Must |
| Architecture diagram | Not yet confirmed | Add diagram showing user → ROS → backend → dashboard/TTS. | Jon, Zhao Qian | Must |
| RQT graph explanation | Not yet captured | Add screenshot and labelled explanation. | Anas | Must |
| Vision explanation | Draft responsibility assigned | Include honest current/future distinction. | Vanness | Must |
| Dashboard explanation | Draft responsibility assigned | Include screenshots and UI explanation. | Mack | Must |
| Backend/testing explanation | Draft responsibility assigned | Include feature checklist and test results. | Zhao Qian | Must |
| Rubric mapping table | Planned | Include final table mapping rubric to evidence. | Jon | Must |

---

### Recommended Ownership Model

Each member should own one clear layer but still support integration. This avoids everyone editing the same files and causing merge conflicts.

| Member | Primary ownership | Secondary support | Main rubric coverage |
|---|---|---|---|
| **Mack** | Dashboard + frontend/backend usability polish | README, demo flow, frontend bug fixing | Codes organization, HRI, video/dashboard presentation |
| **Anas** | ROS robot integration + RQT graph | Robot lab testing, speech topics, launch file | ROS Development, RQT Graph, speech interaction |
| **Jon** | Integration coordination + manuals/report structure | Backend command flow verification, Git branch hygiene | Codes/manual, report context, HRI framing |
| **Vanness** | Vision/emotion integration | Testing camera topic, emotion explanation/evaluation | Vision Integration, HRI emotion-aware response |
| **Zhao Qian** | Backend productivity/calendar QA + final submission packaging | GitHub/release, video link, report assembly | GitHub link, report, code organization, demo evidence |

---

### Individual Task Breakdown

### 1. Mack — Dashboard and User Experience Lead

#### Existing contribution evidence

Based on the `mackwongyy` and `mackwongyy_integration` branches, Mack has already contributed strongly to:

- initial frontend/backend template,
- README/project description updates,
- first integration attempt between frontend/backend and robot code,
- cleanup of duplicated repository work.

#### Final responsibilities

Mack should own the demo-facing dashboard and make sure the system looks complete during presentation.

##### Tasks

1. **Dashboard polish**
   - Verify `dashboard/src/App.jsx` and components display:
     - robot mode,
     - current emotion,
     - last response,
     - schedule,
     - reminders,
     - timer.
   - Ensure the dashboard looks good on the demo laptop screen.
   - Add small labels if needed so evaluators can immediately understand what is happening.

2. **Command panel reliability**
   - Ensure the typed command flow works as a backup for speech.
   - Confirm demo commands work:
     - “Hey, John”
     - “Yes”
     - “What do I have today?”
     - “Set a 25 minute timer”
     - “What should I do now?”
     - “Juno, go to sleep”

3. **Frontend/backend API check**
   - Confirm dashboard calls match backend endpoints:
     - `/api/status`
     - `/api/schedule/today`
     - `/api/reminders`
     - `/api/command`
     - `/ws/status`

4. **Presentation visuals**
   - Prepare dashboard screenshots for the report.
   - Help record the dashboard portion of the demo video.

#### Deliverables

- Dashboard screenshot in active mode.
- Dashboard screenshot showing timer and emotion state.
- Report subsection: **Dashboard and User Interface**.
- Report subsection contribution: dashboard screenshots with captions.
- Confirmation that manual text input works as backup.

---

### 2. Anas — ROS Integration and Robot Testing Lead

#### Existing contribution evidence

The `anas` branch contains the main ROS integration work:

- `src/perception_pkg/` camera and microphone nodes,
- `src/language_pkg/` Whisper Tiny transcriber and British-English TTS node,
- `src/juno_bringup/launch/juno_robot.launch`,
- `backend/src/robot/ros_jupiter_interface.py`,
- backend API updates to consume ROS speech transcripts,
- ROS integration documentation.

#### Final responsibilities

Anas should own the live robot/ROS side and produce the RQT graph evidence.

##### Tasks

1. **ROS node verification**
   - Confirm these nodes can run on the robot/lab machine:
     - `camera_node`
     - `microphone_node`
     - `whisper_tiny_transcriber`
     - `juno_tts_node`
   - Confirm the bringup launch starts the required nodes.

2. **Topic verification**
   - Verify these topics appear:
     - `/camera/image_raw`
     - `/audio/raw`
     - `/speech/raw_transcript`
     - `/speech/transcript`
     - `/juno/tts`
     - `/juno/led_state` if used

3. **Speech pipeline**
   - Test that user speech or manually published transcript reaches the backend.
   - Test that backend responses are published to `/juno/tts`.
   - Keep speech commands short for reliability.

4. **RQT graph**
   - Capture final RQT graph screenshots.
   - Capture at least one close-up screenshot of speech topics and one of camera topics.

5. **Robot lab session planning**
   - Before each robot session, prepare exact tests to avoid wasting limited lab time.
   - Record evidence immediately when something works.

#### Deliverables

- RQT graph screenshot.
- Topic list screenshot or notes.
- Short video clip of speech/TTS working, if possible.
- Report subsection: **ROS Development and Robot Integration**.
- Report subsection contribution: labelled ROS node/topic table and RQT graph explanation.

---

### 3. Jon — Integration, Manual, and Report Structure Lead

#### Existing contribution evidence

The current `jon_integration` branch contains:

- product requirements documentation,
- project component documentation,
- technical requirements for emotion recognition,
- scaled demo manual,
- `.gitignore` cleanup for generated files and Windows metadata.

#### Final responsibilities

Jon should coordinate the final integration story and ensure the project satisfies the rubric even with scaled scope.

##### Tasks

1. **Integration checklist**
   - Maintain a final checklist for:
     - backend starts,
     - dashboard connects,
     - command pipeline works,
     - ROS mode path is documented,
     - mock fallback works,
     - demo script is rehearsed.

2. **Manual and report structure**
   - Use `docs/project_manual_scaled_demo.md` as the manual base.
   - Create final report sections:
     - title,
     - project context,
     - architecture,
     - HRI elements,
     - ROS development,
     - vision integration,
     - speech interaction,
     - NLP/LLM element,
     - limitations and future work,
     - GitHub/video links.

3. **HRI explanation**
   - Clearly explain why wake + confirmation is safe HRI.
   - Explain how dashboard + speech output gives two feedback channels.
   - Explain emotion-aware break recommendation carefully and ethically.

4. **Git hygiene**
   - Keep generated files ignored.
   - Avoid committing virtual environments, `node_modules`, `build`, `devel`, and `Zone.Identifier` files.
   - Coordinate branch merges before final submission.

#### Deliverables

- Final manual/report structure draft.
- Report subsection: **Project Context, HRI Design, Scope, and Conclusion**.
- Rubric mapping table.
- Demo script.
- Clean final branch checklist.

---

### 4. Vanness — Vision and Emotion Integration Lead

#### Current codebase situation

The vision path exists but should be treated as a scaled MVP:

- ROS camera publishes `/camera/image_raw`.
- Backend ROS bridge stores latest camera frame.
- `EmotionDetector` currently uses weighted mock prediction.
- `EmotionSmoother` stabilizes the displayed emotion.
- Full CNN emotion recognition is documented but not required for a stable final demo.

#### Final responsibilities

Vanness should own the vision story and make it credible without overpromising.

##### Tasks

1. **Camera integration verification**
   - Work with Anas to confirm `/camera/image_raw` is active.
   - Confirm backend can receive latest frames through `RosJupiterInterface.get_camera_frame()`.

2. **Emotion MVP**
   - Keep current mock/smoothed emotion working for demo reliability.
   - If time permits, add simple face-detection proof only; do not make final demo depend on a heavy CNN.

3. **Dashboard emotion verification**
   - Confirm dashboard updates `current_emotion` through `/ws/status`.
   - Prepare screenshot showing emotion state.

4. **Report explanation**
   - Explain that the prototype estimates visible expression only.
   - State clearly that it is not a medical or psychological diagnosis.
   - Describe future CNN path using `docs/technical_requirements_emotion.md`.

5. **Evaluation notes**
   - Prepare simple evaluation criteria:
     - camera topic active,
     - emotion label changes are stable,
     - break recommendation responds to tired/stressed/frustrated state,
     - dashboard updates without reload.

#### Deliverables

- Report subsection: **Vision Integration and Emotion-Aware Behaviour**.
- Emotion screenshot from dashboard.
- Short explanation of mock/current implementation vs future CNN implementation.
- Optional simple camera evidence screenshot.

---

### 5. Zhao Qian — Backend QA, Submission, and Evidence Lead

#### Existing contribution evidence

The repository is under Zhao Qian's GitHub organization/account context and the initial commit is associated with Ong Zhao Qian. This makes Zhao Qian suitable to own final submission packaging, GitHub link readiness, and final quality checks.

#### Final responsibilities

Zhao Qian should make sure the project is complete from an evaluator's perspective: working backend features, clean submission, video link, GitHub link, and final evidence.

##### Tasks

1. **Backend feature QA**
   - Test the backend features:
     - schedule query,
     - deadline query,
     - reminder creation/listing,
     - timer start,
     - music response,
     - sleep mode.
   - Confirm sample schedule data appears correctly.

2. **Test checklist**
   - Run or document tests for:
     - intent classification,
     - emotion smoothing,
     - command responses.
   - If local Python environment lacks dependencies, document that tests require installing backend requirements first.

3. **Final video and GitHub evidence**
   - Collect video link.
   - Ensure GitHub link is correct.
   - Ensure final branch/commit is clearly stated in report.

4. **Report assembly**
   - Insert screenshots:
     - dashboard,
     - RQT graph,
     - terminal/topic evidence,
     - robot/demo image if available.
   - Ensure all rubric items are explicitly mentioned.

5. **Final submission checklist**
   - Verify README is accurate.
   - Verify manual exists.
   - Verify no large generated files are newly added.
   - Verify links are accessible.

#### Deliverables

- Final GitHub link.
- Final video link.
- Backend QA checklist.
- Report subsection: **Backend Features, Testing, and Final Evidence**.
- Final report with screenshots inserted and formatting checked.

---

### Report Writing Distribution

Everyone is responsible for writing part of the final report, not only coding or screenshots. Jon and Zhao Qian will coordinate the final formatting, but each member must submit their own section draft with evidence.

| Report Section | Main Writer | Supporting Members | Required Content |
|---|---|---|---|
| Title page, abstract, project context | Jon | Zhao Qian | Project title, team members, problem statement, target user, short system summary. |
| System architecture and code organization | Zhao Qian | Jon, Mack | Backend/dashboard/ROS/docs folder explanation, architecture diagram, GitHub branch/commit. |
| HRI design and interaction flow | Jon | Mack, Vanness | Wake word, confirmation, active/sleep mode, safety, dashboard feedback, user-centred design. |
| Dashboard and frontend | Mack | Jon | Dashboard panels, API/WebSocket usage, screenshots, fallback text command explanation. |
| ROS development and RQT graph | Anas | Zhao Qian | ROS packages, nodes, topics, launch file, RQT graph screenshot and explanation. |
| Speech interaction | Anas | Mack | User input through transcript/dashboard, robot response through TTS, two-way interaction evidence. |
| Vision and emotion integration | Vanness | Anas | Camera topic path, emotion detector/smoother, dashboard emotion state, limitations. |
| NLP/LLM element and backend logic | Jon | Zhao Qian | Rule-based intent classifier, response generator, command examples, future LLM extension. |
| Testing, evaluation, limitations | Zhao Qian | All | Backend tests/checklist, demo results, risks, limitations, future improvements. |
| Conclusion and appendix | Jon, Zhao Qian | All | Summary, rubric mapping, video link, GitHub link, extra screenshots/manual references. |

#### Report Writing Rules

- Each member must write their own assigned section in clear paragraph form, not only bullet points.
- Every technical claim should have evidence: screenshot, code path, RQT graph, video timestamp, or file reference.
- Use honest wording for incomplete parts, especially emotion recognition and speech reliability.
- Keep the final report consistent: same project title, same terminology, same topic names.
- Jon and Zhao Qian should edit for flow, but should not have to write every section from scratch.

---

### Rubric-to-Member Mapping

| Rubric item | Primary owner | Supporting members | Evidence to submit |
|---|---|---|---|
| HRI Elements | Jon | Mack, Vanness | Wake-confirmation flow, dashboard, TTS response, emotion-aware break suggestion. |
| Codes and Manual | Jon | Zhao Qian | `docs/project_manual_scaled_demo.md`, README, organized repo. |
| ROS Development | Anas | Vanness, Jon | ROS packages, launch file, ROS bridge, topic explanations. |
| RQT Graph | Anas | Zhao Qian | RQT graph screenshots in report. |
| Report Context | Jon | Zhao Qian | Problem statement, system architecture, scaled-scope explanation. |
| Code Organization | Zhao Qian | Jon, Mack | Backend/dashboard/src/docs structure, clean `.gitignore`. |
| Vision Integration | Vanness | Anas | Camera topic, emotion detector/smoother, dashboard emotion state. |
| Speech Interaction, 2-way | Anas | Mack | `/speech/transcript`, `/juno/tts`, dashboard backup command. |
| NLP/LLM Element | Jon | Zhao Qian | Rule-based NLP explanation, intent classifier examples, future LLM note. |
| Notable Mention | Jon | All | Safe activation, hybrid ROS + dashboard architecture, fallback design. |
| Title | Jon | Zhao Qian | Final report cover/title. |
| Video Link | Zhao Qian | Mack | Demo video link in report. |
| GitHub Link | Zhao Qian | Jon | Repo link and final branch/commit. |
| Extra/Special Manual | Jon | All | This manual + scaled demo manual. |
| Extra RQT | Anas | Zhao Qian | Extra topic/RQT screenshots. |

---

### 2-3 Week Execution Plan

### Week 1 — Stabilize Mock Mode and Documentation

| Task | Owner |
|---|---|
| Confirm backend starts and command pipeline works in mock/dashboard mode | Jon, Zhao Qian |
| Confirm dashboard displays all required panels | Mack |
| Confirm ROS launch and package structure on local/robot environment | Anas |
| Confirm emotion state appears on dashboard | Vanness |
| Draft final report skeleton and rubric table | Jon |
| Each member drafts their own assigned report subsection outline | All |

### Week 2 — Robot Lab Integration and Evidence Capture

| Task | Owner |
|---|---|
| Test camera/microphone/transcriber/TTS on robot | Anas |
| Capture RQT graph screenshots | Anas, Zhao Qian |
| Capture dashboard screenshots and short demo clips | Mack, Zhao Qian |
| Verify camera/emotion story and collect evidence | Vanness |
| Rehearse final demo script | All |
| Each member writes first full draft of their report subsection | All |

### Week 3 — Polish Only

| Task | Owner |
|---|---|
| Assemble final report | Jon, Zhao Qian |
| Review and improve all member-written sections | All |
| Insert screenshots/video/GitHub links | Zhao Qian |
| Polish README/manual wording | Mack, Jon |
| Final robot demo recording if needed | Anas, Mack |
| Final branch cleanup and submission check | Jon, Zhao Qian |

---

### Final Demo Roles

| Demo segment | Person leading |
|---|---|
| Introduce project context and HRI goal | Jon |
| Show dashboard and command flow | Mack |
| Explain/run ROS nodes and RQT graph | Anas |
| Explain vision/emotion integration | Vanness |
| Present final evidence, GitHub/video/report wrap-up | Zhao Qian |

---

### Minimal Demo Script

1. Jon introduces JUNO Assist as an emotion-aware student productivity robot.
2. Mack shows dashboard in idle mode.
3. User says/types “Hey, John”.
4. JUNO asks for confirmation.
5. User says/types “Yes”.
6. Dashboard changes to active mode.
7. User asks “What do I have today?”
8. JUNO responds with schedule.
9. User asks “Set a 25 minute timer.”
10. Dashboard timer starts.
11. User asks “What should I do now?” or “I feel tired.”
12. JUNO gives emotion-aware break/productivity suggestion.
13. Anas shows RQT graph and explains ROS topics.
14. Vanness explains camera/emotion path and limitation.
15. Zhao Qian shows GitHub/video/report evidence and final submission links.

---

### Final Quality Gate Before Submission

Before submitting, every member should sign off on these items:

| Quality Gate | Owner | Required Evidence |
|---|---|---|
| Backend command loop works from idle → confirmation → active → sleep | Jon, Zhao Qian | Short screen recording or live test checklist. |
| Dashboard clearly shows mode, emotion, response, schedule, reminders, timer | Mack | Dashboard screenshots. |
| ROS topics appear and match the architecture | Anas | RQT graph and topic screenshots. |
| Two-way interaction is demonstrated | Anas, Mack | User input evidence and robot/TTS/dashboard response evidence. |
| Vision/emotion integration is honestly presented | Vanness | Camera/emotion screenshot and limitation paragraph. |
| Every member has contributed their assigned report section | All | Section drafts with names or tracked contributions. |
| Final report maps every rubric item explicitly | Jon | Rubric table in report. |
| GitHub branch is clean and link works | Zhao Qian | Final branch/commit noted in report. |
| Video link works and follows final demo script | Zhao Qian, Mack | Accessible video URL. |

### Presentation Strategy

The team should present the project as a complete, reliable integration prototype:

- Do **not** claim full autonomous navigation.
- Do **not** claim medical-grade emotion detection.
- Do **not** depend on a cloud LLM during the live demo.
- Do emphasize ROS integration, HRI safety, two-way speech, dashboard feedback, and practical fallback design.

Best one-sentence pitch:

> “JUNO Assist is a ROS-integrated human-robot interaction prototype that helps students manage study tasks through wake-confirmed speech interaction, dashboard feedback, emotion-aware break suggestions, and a reliable fallback mode for limited robot access.”

### Important Scope Rule

If the team runs out of time, prioritize these deliverables in order:

1. Dashboard + backend command pipeline works.
2. ROS topics and RQT graph evidence exist.
3. TTS/speech or dashboard backup interaction works.
4. Emotion state is visible and explained honestly.
5. Report/manual explicitly maps to every rubric item.

Do not sacrifice stability for advanced features. A simple working end-to-end robot interaction will score better than an ambitious but unreliable system.


## Appendix A2: Preserved from `docs/vanness/03_report_section_draft.md`

## Report Section Draft: Vision Integration and Emotion-Aware Behaviour

> **Author:** Vanness  
> **Report section:** Vision Integration and Emotion-Aware Behaviour  
> **Required content:** Camera topic path, emotion detector/smoother, dashboard emotion state, limitations  
>
> Instructions: Copy this text into your assigned section of the final report. Edit details based on what was actually tested and confirmed during the robot lab session. Replace placeholder evidence markers (e.g., `[Screenshot X]`) with actual evidence.

---

### Vision Integration and Emotion-Aware Behaviour

#### Overview

JUNO Assist includes a vision component that estimates the user's visible emotional state from camera input and adapts its responses accordingly. This module forms part of the system's Human-Robot Interaction (HRI) design: rather than treating every interaction identically, JUNO Assist adjusts its suggestions based on whether the user appears happy, neutral, tired, stressed, or frustrated. This section describes the camera integration path through the ROS layer, the emotion detection and smoothing pipeline in the backend, how the estimated state is displayed on the dashboard, and the limitations of the current prototype.

---

#### Camera Integration Path

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

#### Emotion Detection Pipeline

The `EmotionDetector` class, located in `backend/src/vision/emotion_detector.py`, classifies each frame into one of five operational states defined by the project: `Happy`, `Neutral`, `Tired`, `Stressed`, and `Frustrated`. These states are represented as the `EmotionState` enum in `backend/src/core/models.py`.

The current prototype uses a weighted mock predictor rather than a trained convolutional neural network (CNN). In this approach, the detector randomly selects from a weighted list of the five emotion states, with `Neutral` being the most likely outcome to simulate realistic baseline behaviour. The mock predictor was chosen for the final prototype because it ensures stable, predictable operation during the demonstration without depending on a trained model file, specific hardware compute capabilities, or precise lighting conditions.

The mock prediction is passed through an `EMAFusion` smoother, which applies an Exponential Moving Average (EMA) directly to the five-class probability distribution rather than to discrete labels. At each frame, the running estimate is updated as:

> P_t = α × P_juno + (1 − α) × P_{t-1}

where α = 0.30 gives recent frames 1.4× more weight than older frames while preserving uncertainty information across the window. Initialising P_{t-1} as a Neutral distribution means the system starts in a safe, predictable state.

The smoothed probability distribution is then passed to the `HysteresisStateMachine`, which commits a new emotion label only after it has been the argmax of the distribution for at least 45 consecutive frames (approximately 1.5 seconds at 30 Hz). This prevents the displayed state from flickering between adjacent emotions, such as Neutral and Tired, due to momentary expression changes. A state transition is only recorded and broadcast when the candidate emotion has held its lead for the full dwell period.

This two-stage approach — EMA on probability distributions followed by hysteresis — is strictly better than the simpler majority-vote smoother because it retains confidence information, weights recent evidence more heavily, and explicitly controls the minimum persistence required before a state change is accepted.

---

#### Dashboard Emotion Display

The estimated emotion state is included in every broadcast from the `/ws/status` WebSocket endpoint, which the React dashboard consumes at approximately 1 Hz. The `StatusPanel` component displays the `current_emotion` field in real time without requiring a page reload. During active mode, the emotion label is visible alongside the robot's current mode and last spoken response.

`[Screenshot: Dashboard Status Panel in ACTIVE mode showing current_emotion field]`

The emotion field is part of the `RobotStatus` Pydantic model, which serialises to JSON and is broadcast by the `_ws_status` WebSocket handler in `app.py`. This path is fully functional in both mock mode (laptop development) and ROS mode (robot deployment).

---

#### Emotion-Aware Break Recommendation

The `BreakRecommender` class in `backend/src/productivity/break_recommender.py` translates the current `EmotionState` into a contextually appropriate suggestion. It is called by the `ResponseGenerator` when the user's intent is `REQUEST_BREAK` or `ASK_STATUS`. The mapping from emotion to suggestion is as follows:

- **Tired:** Recommends a 5-minute break before continuing.
- **Stressed:** Encourages prioritising the nearest deadline and starting with a short study session.
- **Frustrated:** Suggests pausing and breaking the current task into smaller steps.
- **Happy:** Affirms the user's positive state and encourages continuing.
- **Neutral:** Offers to help with schedule, timer, or task planning.

The emotion state used by the `ResponseGenerator` is retrieved from `robot_state.snapshot()["current_emotion"]`, which is set by the emotion monitor loop. This creates a closed feedback path: the camera informs the emotion estimate, the estimate informs the response, and the response reaches the user through both TTS (spoken output on the robot) and the dashboard command panel.

`[Screenshot: Dashboard showing emotion-aware break suggestion in response panel]`

---

#### Limitations

The current implementation has the following limitations, which are presented honestly and without overstatement.

**Mock predictor, not real recognition:** The prototype uses a weighted random selection rather than a trained CNN. This means the system does not read the user's actual facial expression; it simulates one. Real emotion recognition would require a CNN trained on facial expression data, such as the Mini-Xception model trained on FER2013, combined with OpenCV face detection. The full CNN pipeline design is documented in `docs/technical_requirements_emotion.md` and is planned as future work.

**Not a diagnostic tool:** The emotion labels used by JUNO Assist — Tired, Stressed, Frustrated, Happy, and Neutral — are operational categories designed to adapt the robot's responses to the user's visible state. They are not medical assessments, psychological diagnoses, or measures of internal mental health. Any statement the system makes about the user's emotion is an estimate of visible expression only, under normal lighting conditions.

**Face detection dependency:** In the real CNN path, emotion classification depends on successful face detection. If the user is not looking directly at the camera, is in poor lighting, or is too far from the camera, face detection will fail. In this case, the EMA smoother is designed to retain the last known distribution rather than reset, which maintains a reasonable estimate while the face is temporarily unavailable.

**Camera access during demo:** Camera integration depends on the robot session. If the camera topic is unavailable during the demonstration, the system falls back to mock mode transparently, allowing the rest of the demonstration to proceed normally. The dashboard will still display a simulated emotion state.

---

#### Future Work

The proposed upgrade path for the real emotion recognition pipeline includes:

1. **Face detection:** Replace the mock predictor with OpenCV DNN face detection using the ResNet-SSD model (`res10_300x300_ssd_iter_140000.caffemodel`), which handles partial occlusion and varied lighting better than Haar cascades.
2. **CNN inference:** Run the Mini-Xception model (approximately 2 MB, ~15 ms/frame on CPU) on the detected face region.
3. **Class remapping:** Project the 7-class FER2013 output to the 5 Juno emotion classes using a fixed projection matrix encoding domain knowledge about which standard emotions correspond to each Juno state (e.g., FER `Sad` maps to Juno `Tired` because fatigue manifests as low-arousal negative affect).
4. **EMA + Hysteresis smoothing:** The same `EMAFusion` and `HysteresisStateMachine` components already implemented in the prototype would be used with real CNN outputs without modification.

This upgrade path is fully designed and documented. It was not implemented in the current prototype due to the priority of delivering a stable, reliable demonstration system within the available robot access time.

---

#### Evidence Summary

| Item | Evidence |
|---|---|
| Camera topic active | `rostopic hz /camera/image_raw` showing ~30 Hz `[Screenshot]` |
| Emotion state on dashboard | Status Panel screenshot in active mode `[Screenshot]` |
| Break recommendation working | Command panel response screenshot `[Screenshot]` |
| Unit tests passing | `pytest tests/ -v` output `[Screenshot]` |


### Timer cancellation and speech-prioritised emotion update

The timer duration prompt now accepts flexible formats such as `twenty five minutes`, `1h 30m`, `half an hour`, and `2:30`. The user may exit the timer flow by saying `cancel`, `not now`, `skip`, or `never mind`; repeated unclear responses also cancel the pending timer setup.

When the user's transcript explicitly states an emotion, such as `I am stressed` or `I feel tired`, the backend treats the speech cue as higher priority than the visual emotion estimate for a short configurable window (`JUNO_SPEECH_EMOTION_OVERRIDE_SECONDS`).
