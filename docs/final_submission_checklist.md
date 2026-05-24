# Final Submission Checklist

Use this file as the practical checklist for completing the WID3010 submission with minimum rework. Complete items in order.

## Submission Requirements from `WID3010 AA (Q)_2025.2026.pdf`

Use the same naming as the question paper in the report so the mapping is clear.

| Item | Marks | Question-paper wording / required output |
|---|---:|---|
| Q1 | 10 | Explain the robotics application, objectives and scope; describe the technique/algorithm/model used for computer vision, speech processing and reasoning tasks; include a sketch/diagram/visual aid of the experimental setup; list testing scenarios. |
| Q2 | 5 | Develop a ROS workspace: boot Ubuntu, create the ROS workspace folder, turn it into a catkin workspace, and load the workspace when opening a new terminal using `~/.bashrc`. |
| Q3 | 20 | Develop the robotics application on the ROS workspace; identify appropriate packages; design ROS APIs such as topics, publishers and subscribers; connect sensor input to processing and robot/backend decision-making; run/unit-test each ROS API; explain purpose and example input/output. |
| Q4 | 5 | Visualise the ROS graph using `rqt_graph`; show nodes and publishers/subscribers; explain node-topic relationships in the report. |
| Q5 | 5 | Develop a step-by-step manual on how to run/launch the robot application, preferably with screenshots and specific scripts/commands. |
| Q6 | 5 | Develop a max 5-minute robot demo video showing the experimental setup and testing scenarios, preferably with text labels describing the video flow. |

Final Spectrum submission:

- Report with cover page and group details
- Q1, Q4, Q5 answers
- Video link for Q6
- References
- Class/project session photos if available
- ZIP folder containing ROS workspace and related code for Q2/Q3

---

## Current Status: Code vs Evidence

| Question | Codebase status | Still required for submission |
|---|---|---|
| Q1 | Code/docs ready; no more code changes needed unless a feature is broken | polished report text, setup diagram, testing scenario table |
| Q2 | Code/docs ready; ROS workspace structure is ready | physical robot/Ubuntu screenshots proving workspace setup and sourcing |
| Q3 | Code/docs ready; software/ROS structure is ready; CI covers non-hardware unit/API checks | physical robot screenshots proving ROS APIs run successfully, including unit testing each ROS API with `rostopic`/`rosnode` evidence |
| Q4 | Code/docs ready; no code changes needed | `rqt_graph` screenshot and explanation |
| Q5 | Code/docs ready; launch commands and manual structure documented | final step-by-step manual with screenshots |
| Q6 | no code changes unless demo fails | max 5-minute video |

Q1-Q6 are ready from the code/docs side, but they are not submission-complete until the final report/manual text, physical evidence screenshots, and demo video link are collected.

From this point, avoid unnecessary code changes. Focus on evidence collection, report writing, and demo rehearsal. Only change code if physical robot testing reveals a real bug.

---

## Before Doing Anything

```bash
git status
```

Do not commit generated folders unless specifically required:

```text
build/
devel/
install/
__pycache__/
```

Keep `src/CMakeLists.txt` because it proves the catkin workspace structure.

---

## Pull Request Software Checks

The repository includes GitHub Actions software checks for pull requests and pushes to `main`:

```text
.github/workflows/software-checks.yml
```

These checks cover non-hardware validation:

- backend unit/API tests that do not require the robot
- vision smoke test without robot hardware
- Python compile checks
- ROS workspace/package/launch file structure
- ROS script executable permissions
- dashboard build
- repository hygiene checks

These checks do **not** replace physical robot testing for Q3/Q4. Hardware-dependent APIs must still be verified on the robot using `roslaunch`, `rostopic`, `rosnode`, and `rqt_graph`.

---

## Q1: Explain Robotics Application, Objectives, Scope, and AI Methods

No new code is required for Q1 unless a feature is broken. This is mainly report writing.

Include:

1. Application name: JUNO Assist
2. Problem: student productivity, schedules, reminders, focus sessions, emotional fatigue
3. Objectives:
   - wake-word controlled robot assistant
   - speech input and spoken response
   - dashboard feedback
   - camera-based emotion monitoring
   - schedule/timer/reminder support
4. Scope:
   - voice interaction
   - dashboard interaction
   - ROS camera/microphone/TTS integration
   - emotion-aware productivity support
   - not full autonomous navigation
5. AI/algorithm table:

| Component | Technique / Model | Purpose |
|---|---|---|
| Speech-to-text | Whisper Tiny primary, Moonshine fallback | Convert microphone audio to text |
| Text-to-speech | ROS TTS node with `espeak`/British English voice | Speak backend responses |
| Wake word | fuzzy phrase matching | Detect “Hey, John” despite ASR errors |
| Intent reasoning | rule-based intent classifier | Convert transcript to assistant action |
| Vision | camera stream + emotion detector | Estimate user emotion state |
| Emotion smoothing | EMA/hysteresis or mock smoother depending runtime | Reduce flickering emotion states |
| Dashboard | React + WebSocket | Display state, camera, schedule, timer, response |

6. Experimental setup diagram:

```text
User
 ├─ speaks → microphone_node → /audio/raw → transcriber → /speech/transcript
 ├─ appears on camera → camera_node → /camera/image_raw → backend vision
 └─ views dashboard ← FastAPI/WebSocket ← backend decision pipeline

Backend → /juno/tts → tts_node → robot/laptop speaker
```

7. Testing scenarios:

| Scenario | Input | Expected Output |
|---|---|---|
| Wake activation | “Hey, John” | confirmation prompt |
| Confirmation | “Yes” | active mode and dashboard opens |
| Schedule query | “What is my schedule today?” | schedule response |
| Timer | “Set a 25 minute timer” | timer starts |
| Break recommendation | “I feel tired” / “I need a break” | emotion-aware advice |
| TTS | backend response | `/juno/tts` publishes and robot speaks |
| Camera | switch on dashboard camera | camera stream visible |
| Sleep | “Juno, go to sleep” | idle mode |

---

## Q2: Develop ROS Workspace Setup Evidence

Codebase status: the ROS workspace structure is ready. Main evidence should be captured on the physical robot/lab Ubuntu machine. Use laptop/WSL only as backup.

### Commands to run on physical robot

```bash
lsb_release -a
python3 --version
rosversion -d
```

Expected: Ubuntu with ROS Noetic available.

```bash
cd ~/WID3010-JunoAssist
pwd
ls
ls src
```

Show that the repo is the ROS workspace folder.

```bash
source /opt/ros/noetic/setup.bash
ls -la .catkin_workspace src/CMakeLists.txt
find src -maxdepth 2 -name package.xml -print
find src -maxdepth 2 -name CMakeLists.txt -print
catkin_make
```

Show successful catkin build.

```bash
source devel/setup.bash
echo $ROS_PACKAGE_PATH
rospack find perception_pkg
rospack find language_pkg
rospack find juno_bringup
```

Show that packages are discoverable.

### Auto-source evidence

Add to `~/.bashrc` on the robot:

```bash
echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc
echo "source ~/WID3010-JunoAssist/devel/setup.bash" >> ~/.bashrc
```

Open a new terminal:

```bash
echo $ROS_PACKAGE_PATH
rospack find perception_pkg
rospack find language_pkg
rospack find juno_bringup
```

Screenshots to capture:

- Ubuntu/ROS version
- workspace folder and `src/`
- package list
- `catkin_make` success
- `ROS_PACKAGE_PATH`
- `rospack find` results
- `.bashrc` source lines

---

## Q3: Develop Robotics Application on ROS Workspace, APIs, and Testing

Codebase/software status: the ROS packages, launch file, backend bridge, and CI non-hardware unit/API checks are ready. Do not make more Q3 code changes unless robot testing reveals a bug.

The question paper specifically asks to **perform unit testing by running each ROS API**. For this project, that means two layers of evidence:

1. **Software unit/API testing** — automated backend/dashboard/vision checks in GitHub Actions.
2. **ROS API unit testing on the robot** — run each ROS topic/API with `rostopic`, `rosnode`, manual transcript input, and TTS test commands, then screenshot the outputs.

This is the largest technical section. Prioritise clear proof of execution on the physical robot.

### ROS packages to explain

| Package | Purpose |
|---|---|
| `perception_pkg` | camera and microphone sensor input |
| `language_pkg` | ASR transcription, manual transcript fallback, TTS output |
| `juno_bringup` | launch file for robot-side ROS nodes |

### ROS APIs to explain

| Topic | Publisher | Subscriber | Message Type | Purpose |
|---|---|---|---|---|
| `/camera/image_raw` | `camera_node.py` | backend / diagnostic listener | `sensor_msgs/Image` | camera frames |
| `/audio/raw` | `microphone_node.py` | `transcriber.py` | `std_msgs/Float32MultiArray` | microphone audio |
| `/speech/raw_transcript` | manual input | `transcriber.py` | `std_msgs/String` | fallback text input |
| `/speech/transcript` | `transcriber.py` | backend bridge | `std_msgs/String` | recognised command text |
| `/juno/tts` | backend bridge | `tts_node.py` | `std_msgs/String` | spoken response text |
| `/juno/tts_done` | `tts_node.py` | `transcriber.py` | `std_msgs/String` | resume listening after speech |
| `/juno/led_state` | backend bridge | robot LED adapter if available | `std_msgs/String` | optional robot state feedback |

### ROS API unit testing commands to run and screenshot

Terminal 1:

```bash
source /opt/ros/noetic/setup.bash
roscore
```

Terminal 2:

```bash
cd ~/WID3010-JunoAssist
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch juno_bringup juno_robot.launch
```

Diagnostics:

```bash
rostopic list
rosnode list
rostopic hz /camera/image_raw
rostopic echo /speech/transcript
rostopic echo /juno/tts
rostopic echo /juno/tts_done
```

Manual transcript test:

```bash
rostopic pub /speech/raw_transcript std_msgs/String "data: 'Hey, John'"
rostopic pub /speech/raw_transcript std_msgs/String "data: 'Yes'"
rostopic pub /speech/raw_transcript std_msgs/String "data: 'What is my schedule today?'"
```

TTS test:

```bash
rosrun language_pkg tts_test_publisher.py "Hello, I am JUNO and my speech node is working."
```

Backend integration test:

```bash
cd ~/WID3010-JunoAssist/backend
source ../devel/setup.bash
source .venv/bin/activate
export JUNO_ROBOT_INTERFACE=ros
python main.py
```

Dashboard:

```bash
cd ~/WID3010-JunoAssist/dashboard
npm install
npm run dev
```

Screenshots to capture for ROS API unit testing:

- `roslaunch` running nodes
- `rostopic list`
- `rosnode list`
- `/camera/image_raw` rate
- `/audio/raw` publishing microphone data, if stable
- transcript topic receiving text
- `/juno/tts` output
- `/juno/tts_done` output after speech finishes
- backend running in ROS mode
- dashboard active

Minimum conclusion needed for Q3:

```text
The perception package publishes camera/audio sensor data, the language package converts speech to transcript and handles TTS, and the backend ROS bridge consumes transcripts/camera frames for decision-making before publishing responses back to `/juno/tts`.
```

---

## Q4: Visualise ROS Graph using RQT Graph

Q4 requires a clear `rqt_graph` screenshot and an explanation of the node-topic relationships. No code changes are required unless the graph reveals a broken node or topic.

### Step 1: Start the full ROS system

Terminal 1:

```bash
source /opt/ros/noetic/setup.bash
roscore
```

Terminal 2:

```bash
cd ~/WID3010-JunoAssist
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch juno_bringup juno_robot.launch
```

Terminal 3:

```bash
cd ~/WID3010-JunoAssist/backend
source ../devel/setup.bash
source .venv/bin/activate
export JUNO_ROBOT_INTERFACE=ros
python main.py
```

### Step 2: Open RQT graph

Terminal 4:

```bash
source /opt/ros/noetic/setup.bash
source ~/WID3010-JunoAssist/devel/setup.bash
rqt_graph
```

In the `rqt_graph` window:

- refresh the graph after all nodes are running
- show nodes and topics clearly
- if the graph is too cluttered, hide debug topics but keep the main JUNO topics visible
- take a screenshot for the report

The screenshot should ideally show:

```text
/camera_node
/microphone_node
/whisper_tiny_transcriber
/juno_tts_node
/juno_backend_bridge, if visible
/camera/image_raw
/audio/raw
/speech/transcript
/juno/tts
/juno/tts_done
```

### Step 3: Capture supporting topic evidence

Run these after taking the graph screenshot:

```bash
rosnode list
rostopic list
rostopic info /camera/image_raw
rostopic info /audio/raw
rostopic info /speech/transcript
rostopic info /juno/tts
rostopic info /juno/tts_done
```

These commands support the graph explanation, especially if the backend node is hard to see in `rqt_graph`.

### Q4 report explanation template

```text
The RQT graph visualises the ROS communication structure of JUNO Assist. The perception package provides sensor input through camera_node and microphone_node. camera_node publishes camera frames to /camera/image_raw for backend vision processing and dashboard camera streaming. microphone_node publishes raw audio samples to /audio/raw. The whisper_tiny_transcriber node subscribes to /audio/raw, performs speech-to-text processing, and publishes recognised commands to /speech/transcript.

The backend ROS bridge subscribes to /speech/transcript and /camera/image_raw. It forwards recognised speech into the backend decision pipeline, where wake-word detection, intent classification, schedule/timer logic, and response generation are performed. The backend then publishes the response text to /juno/tts. The juno_tts_node subscribes to /juno/tts, speaks the response, and publishes /juno/tts_done after speech output finishes. The transcriber uses /juno/tts_done to resume listening, preventing the robot from transcribing its own speech.
```

### If the backend does not appear clearly in RQT graph

Write this in the report and include `rostopic info` screenshots:

```text
The backend ROS bridge is embedded inside the FastAPI backend process, so it may not always appear clearly in the rqt_graph view depending on process timing and graph refresh. Its publisher/subscriber connections were verified separately using rostopic info and rostopic echo for /speech/transcript, /camera/image_raw, /juno/tts, and /juno/tts_done.
```

### Q4 evidence checklist

- [ ] `rqt_graph` screenshot
- [ ] `rosnode list` screenshot
- [ ] `rostopic list` screenshot
- [ ] `rostopic info /camera/image_raw`
- [ ] `rostopic info /audio/raw`
- [ ] `rostopic info /speech/transcript`
- [ ] `rostopic info /juno/tts`
- [ ] `rostopic info /juno/tts_done`
- [ ] short paragraph explaining the graph

---

## Q5: Manual on How to Run/Launch Robot Application

Q5 is a documentation/manual task. No code changes are required unless a launch command fails during testing. The manual should be step-by-step and include screenshots, commands, purpose, and expected output for each step.

Recommended manual structure:

1. Prerequisites
   - Ubuntu
   - ROS Noetic
   - Python environment
   - Node.js/npm for dashboard
2. Build workspace
3. Terminal 1: `roscore`
4. Terminal 2: `roslaunch juno_bringup juno_robot.launch`
5. Terminal 3: backend in ROS mode
6. Terminal 4: dashboard
7. Verification commands
8. Optional manual transcript fallback
9. Troubleshooting table

### Q5 screenshot checklist

- [ ] prerequisites/version commands
- [ ] `catkin_make` successful build
- [ ] Terminal 1: `roscore` running
- [ ] Terminal 2: `roslaunch juno_bringup juno_robot.launch` running
- [ ] Terminal 3: backend running with `JUNO_ROBOT_INTERFACE=ros`
- [ ] Terminal 4: dashboard running and showing local URL
- [ ] dashboard open in browser
- [ ] verification commands such as `rostopic list`, `rosnode list`, and backend `/api/status`

### Prerequisite checks

```bash
lsb_release -a
rosversion -d
python3 --version
node --version
npm --version
```

### Build workspace

```bash
cd ~/WID3010-JunoAssist
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash
```

Expected output: catkin build completes without errors and creates/updates `devel/`.

### Four-terminal demo setup

Terminal 1:

```bash
source /opt/ros/noetic/setup.bash
roscore
```

Terminal 2:

```bash
cd ~/WID3010-JunoAssist
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch juno_bringup juno_robot.launch
```

Terminal 3:

```bash
cd ~/WID3010-JunoAssist/backend
source ../devel/setup.bash
source .venv/bin/activate
export JUNO_ROBOT_INTERFACE=ros
export JUNO_DASHBOARD_URL=http://localhost:5173
python main.py
```

Terminal 4:

```bash
cd ~/WID3010-JunoAssist/dashboard
npm install
npm run dev
```

No separate vision terminal is required during the live demo. Use `.venv-vision` only for vision tests or CNN experiments.

### Verification commands for manual

Run these after the four terminals are active:

```bash
rostopic list
rosnode list
curl http://localhost:8000/api/status
```

Expected output:

- `rostopic list` shows `/camera/image_raw`, `/audio/raw`, `/speech/transcript`, `/juno/tts`, and `/juno/tts_done`
- `rosnode list` shows camera, microphone, transcriber, and TTS nodes
- backend status endpoint returns JSON instead of an error

### Optional manual transcript fallback

Use this when ASR or microphone input is unstable during testing:

```bash
cd ~/WID3010-JunoAssist
source /opt/ros/noetic/setup.bash
source devel/setup.bash
rosrun language_pkg example_transcriptor.py
```

Then type:

```text
Hey, John
Yes
What is my schedule today?
```

### Q5 report/manual format

For each step in the final manual, use this structure:

```text
Step number:
Purpose:
Command:
Expected output:
Screenshot/Figure:
```

---

## Q6: Max 5-Minute Robot Demo Video

Q6 is a recording/editing task. No code changes are required unless the demo fails during rehearsal.

Maximum length: 5 minutes.

The video should show:

- the physical robot/application setup
- ROS/backend/dashboard running
- the robot performing the testing scenarios
- clear text labels describing the video flow
- no unnecessary long terminal setup time

Suggested flow:

| Time | Action |
|---|---|
| 0:00-0:20 | show robot setup and dashboard |
| 0:20-0:50 | show ROS/backend/dashboard terminals running |
| 0:50-1:20 | wake command: “Hey, John” |
| 1:20-1:50 | confirmation: “Yes” and dashboard active |
| 1:50-2:30 | schedule query |
| 2:30-3:10 | study timer command |
| 3:10-3:50 | camera/emotion or dashboard status |
| 3:50-4:30 | break recommendation / productivity response |
| 4:30-5:00 | sleep command and closing screen |

Use text labels in the video:

```text
1. ROS nodes launched
2. Wake word detected
3. Voice confirmation completed
4. Dashboard activated
5. Schedule command processed
6. Timer command processed
7. Robot response spoken through TTS
8. Camera/emotion state displayed
9. Sleep command returns JUNO to idle mode
```

### Q6 recording checklist

- [ ] video is under 5 minutes
- [ ] robot/setup is visible
- [ ] dashboard is visible
- [ ] ROS/backend/dashboard terminals are briefly shown
- [ ] wake phrase is demonstrated
- [ ] confirmation flow is demonstrated
- [ ] at least one productivity command is demonstrated
- [ ] TTS/spoken response is demonstrated
- [ ] camera/emotion/dashboard state is shown
- [ ] sleep/ending command is shown
- [ ] text labels are added to explain each scene
- [ ] final video link is added to the report

### Only change code for Q6 if rehearsal reveals one of these issues

- wake word fails
- TTS does not speak
- dashboard does not load
- ROS node crashes
- camera or microphone topic does not publish
- backend does not respond to transcript commands

---

## Final Report Structure

1. Cover page
   - course code
   - project title
   - group number
   - names and matric IDs
2. Q1 answer
3. Q4 answer with rqt graph
4. Q5 manual
5. Video link for Q6
6. References
7. Photos from class/project sessions
8. Appendix/evidence section
   - Q2 screenshots
   - Q3 ROS API screenshots
   - test outputs

---

## Final No-More-Code Rule

After Q1-Q3 evidence is captured, do not keep refactoring. Only fix:

- a command that fails on the robot
- a missing file needed for submission
- a typo in the report/docs
- a CI failure caused by the current PR

Everything else should move to screenshots, report, and video preparation.

---

## Final Git Checklist

Before final commit:

```bash
git status
```

Expected intentional changes may include:

```text
README.md
docs/*.md
.gitignore
src/CMakeLists.txt
```

Avoid committing:

```text
build/
devel/
install/
__pycache__/
*.pyc
.ros/
```
