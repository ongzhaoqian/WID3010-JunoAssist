# JUNO Assist Team Task Distribution

## Purpose

This task distribution is based on the current codebase, branch history, and the scaled MVP plan in `docs/project_manual_scaled_demo.md`. The goal is to finish a reliable 5-person group project within limited robot access time: about 4 hours per week for 2-3 weeks.

The recommended final scope is:

> **Human command → ROS/input layer → backend NLP/state logic → robot TTS response → dashboard feedback → RQT graph evidence.**

Do not expand into full robot navigation, complex LLM integration, or full CNN emotion training unless the MVP is already stable.

---

## Codebase and Branch Review Summary

### Branch/commit evidence reviewed

| Branch / Area | Evidence from repo | Main work shown |
|---|---|---|
| `mackwongyy` | commits by Mack/Wong Yoong Yee including `915cad1`, `4c5bcfa`, `0d9f42b`, `ddb7021` | Initial frontend/backend project template, README updates, overall project framing. |
| `mackwongyy_integration` | commit `b86a1f4` | First attempt at integrating robot code with existing frontend/backend code; also cleaned duplicated repository work. |
| `anas` | commits leading to `389b4fe` | ROS/catkin structure, perception/language packages, backend ROS bridge, launch file, TTS node, transcriber publishing `/speech/transcript`. |
| `jon_integration` | current branch | Product/manual docs, scaled demo plan, `.gitignore` cleanup, integration planning. |
| `main` | initial repo + README | Base repository and project identity. |

### Current code modules verified

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

## Program Component Completion Checklist

This checklist tracks the actual software components that still need to be completed, verified, or polished. The goal is to make the final project reliable, demonstrable, and clearly connected to the rubric.

### Priority Legend

| Priority | Meaning |
|---|---|
| **Must** | Required for the final demo/submission. |
| **Should** | Strongly recommended if time permits. |
| **Optional** | Nice-to-have only after the core demo is stable. |

### 1. Repository and Integration Hygiene

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| `.gitignore` | Updated on integration branch | Confirm correct `*:Zone.Identifier`, `build/`, `devel/`, `.venv/`, `node_modules/`, `__pycache__/`, `*.pyc` ignores. | Jon | Must |
| Tracked generated files | Some generated files still exist in older branches | Remove tracked `build/`, `devel/`, `__pycache__/`, `*.pyc` from final branch using Git cleanup. | Jon, Zhao Qian | Must |
| Final integration branch | `jon_integration` exists | Decide final branch/commit for submission and make sure all required docs/code are there. | Jon, Zhao Qian | Must |
| Branch consistency | `anas` and `mackwongyy_integration` source mostly aligned | Use final branch as source of truth; avoid reintroducing generated files from older branches. | Jon | Must |

### 2. Backend Assistant Core

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| FastAPI app | Implemented in `backend/src/api/app.py` | Run backend locally and confirm all routes work. | Jon, Zhao Qian | Must |
| Robot mode state | Implemented: idle, confirmation, active | Verify full state flow: idle → confirmation → active → sleep/idle. | Jon | Must |
| Wake word detector | Implemented | Test with `Hey, Juno`, `hey juno`, and wrong phrases. | Jon | Must |
| Confirmation handler | Implemented | Test `Yes` confirmation and non-confirmation fallback. | Jon | Must |
| Command pipeline | Implemented in `process_command_text()` | Verify both dashboard command and ROS transcript use same logic. | Jon, Anas | Must |
| Text-to-speech wrapper | Implemented | Confirm backend calls `tts.speak()` for key responses. | Anas, Jon | Must |
| Error/fallback responses | Basic fallback exists | Make fallback wording clear and demo-friendly. | Jon | Should |

### 3. NLP and Response Logic

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| Intent classifier | Implemented rule-based classifier | Test supported commands: schedule, deadline, timer, reminder, music, break, status, sleep. | Jon, Zhao Qian | Must |
| Timer extraction | Implemented | Test commands like `Set a 5 minute timer` and default timer command. | Zhao Qian | Must |
| Response generator | Implemented | Confirm responses include schedule/deadline/emotion context where relevant. | Jon | Must |
| NLP/LLM report framing | Documented as rule-based NLP | Explain clearly in report; mention LLM as future work only. | Jon | Must |
| Intent tests | Test files exist | Install dependencies and run tests; fix only if failing. | Zhao Qian | Should |

### 4. Calendar, Reminder, and Productivity Features

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| SQLite calendar service | Implemented | Confirm database initializes and sample schedule loads. | Zhao Qian | Must |
| Schedule endpoint | Implemented | Confirm dashboard displays schedule. | Zhao Qian, Mack | Must |
| Deadline endpoint | Implemented | Confirm deadline command gives meaningful response. | Zhao Qian | Must |
| Reminder endpoint | Implemented | Test adding/listing reminders from dashboard. | Zhao Qian, Mack | Should |
| Study timer service | Implemented | Confirm timer starts and dashboard countdown updates. | Zhao Qian, Mack | Must |
| Break recommender | Implemented | Confirm tired/stressed/frustrated status gives break suggestion. | Vanness, Jon | Must |
| Music service | Simple response implemented | Keep as simple response unless audio playback is stable. | Zhao Qian | Optional |

### 5. Dashboard / Frontend

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

### 6. ROS Robot Integration

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| `perception_pkg` | Exists | Confirm package builds/runs on ROS machine. | Anas | Must |
| `language_pkg` | Exists | Confirm package builds/runs on ROS machine. | Anas | Must |
| `juno_bringup` | Exists | Confirm launch file starts required nodes. | Anas | Must |
| Camera node | Implemented | Verify `/camera/image_raw` publishes on robot/laptop camera. | Anas, Vanness | Must |
| Microphone node | Implemented | Verify `/audio/raw` publishes. | Anas | Must |
| Transcriber node | Implemented | Verify `/speech/transcript` publishes text or use manual transcript backup. | Anas | Must |
| TTS node | Implemented | Verify `/juno/tts` is spoken by `pyttsx3`/`espeak`. | Anas | Must |
| Backend ROS bridge | Implemented | Run backend in ROS mode and confirm subscriptions/publishers work. | Anas, Jon | Must |
| LED state topic | Implemented as optional publisher | Show in RQT if available; otherwise document as optional. | Anas | Optional |
| RQT graph | Not yet captured | Capture full RQT graph and topic close-ups. | Anas, Zhao Qian | Must |

### 7. Vision and Emotion Component

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| Camera input path | ROS topic and backend frame getter exist | Verify latest camera frame reaches backend in ROS mode. | Vanness, Anas | Must |
| Emotion detector | Mock/weighted detector implemented | Keep stable for demo; do not rely on heavy CNN. | Vanness | Must |
| Emotion smoothing | Implemented | Run/check smoothing test if dependencies available. | Vanness, Zhao Qian | Should |
| Dashboard emotion display | Implemented through status | Confirm emotion is visible during active mode. | Vanness, Mack | Must |
| Emotion-aware break recommendation | Implemented through response generation | Test break/status command with emotion state. | Vanness, Jon | Must |
| Real CNN emotion recognition | Documented but not implemented | Present as future work unless all core items are stable. | Vanness | Optional |
| Vision evidence | Not yet captured | Capture camera/RQT screenshot and dashboard emotion screenshot. | Vanness | Must |

### 8. Speech Interaction Component

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| User input via dashboard | Implemented | Use as reliable backup for demo. | Mack | Must |
| User input via ROS transcript | Implemented path | Test with microphone/transcriber; if unstable, use manually published transcript evidence. | Anas | Must |
| Robot output via TTS | Implemented path | Confirm `/juno/tts` triggers speech. | Anas | Must |
| Two-way demo | Not yet recorded | Record user command and robot/dashboard response. | Anas, Mack | Must |
| Speech fallback plan | Documented | Use dashboard command if robot microphone fails. | Jon | Must |

### 9. Testing and Demo Evidence

| Component | Current Status | What Still Needs To Be Done | Owner | Priority |
|---|---|---|---|---|
| Backend unit tests | Test files exist | Install dependencies and run tests. | Zhao Qian | Should |
| Python syntax check | Passed locally once | Repeat after final code changes. | Jon | Must |
| Dashboard build/run check | Build failed locally because dependencies not installed | Run after `npm install` on demo machine. | Mack | Must |
| ROS runtime check | Not testable in current non-ROS environment | Test during robot session and record evidence. | Anas | Must |
| Demo script rehearsal | Draft exists | Rehearse exact commands and timing. | All | Must |
| Demo video | Not yet recorded | Record stable end-to-end demo. | Zhao Qian, Mack | Must |
| GitHub/video links | Not yet final | Add final links to report. | Zhao Qian | Must |

### 10. Final Report and Manual Components

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

## Recommended Ownership Model

Each member should own one clear layer but still support integration. This avoids everyone editing the same files and causing merge conflicts.

| Member | Primary ownership | Secondary support | Main rubric coverage |
|---|---|---|---|
| **Mack** | Dashboard + frontend/backend usability polish | README, demo flow, frontend bug fixing | Codes organization, HRI, video/dashboard presentation |
| **Anas** | ROS robot integration + RQT graph | Robot lab testing, speech topics, launch file | ROS Development, RQT Graph, speech interaction |
| **Jon** | Integration coordination + manuals/report structure | Backend command flow verification, Git branch hygiene | Codes/manual, report context, HRI framing |
| **Vanness** | Vision/emotion integration | Testing camera topic, emotion explanation/evaluation | Vision Integration, HRI emotion-aware response |
| **Zhao Qian** | Backend productivity/calendar QA + final submission packaging | GitHub/release, video link, report assembly | GitHub link, report, code organization, demo evidence |

---

## Individual Task Breakdown

## 1. Mack — Dashboard and User Experience Lead

### Existing contribution evidence

Based on the `mackwongyy` and `mackwongyy_integration` branches, Mack has already contributed strongly to:

- initial frontend/backend template,
- README/project description updates,
- first integration attempt between frontend/backend and robot code,
- cleanup of duplicated repository work.

### Final responsibilities

Mack should own the demo-facing dashboard and make sure the system looks complete during presentation.

#### Tasks

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
     - “Hey, Juno”
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

### Deliverables

- Dashboard screenshot in active mode.
- Dashboard screenshot showing timer and emotion state.
- Report subsection: **Dashboard and User Interface**.
- Report subsection contribution: dashboard screenshots with captions.
- Confirmation that manual text input works as backup.

---

## 2. Anas — ROS Integration and Robot Testing Lead

### Existing contribution evidence

The `anas` branch contains the main ROS integration work:

- `src/perception_pkg/` camera and microphone nodes,
- `src/language_pkg/` Moonshine transcriber and TTS node,
- `src/juno_bringup/launch/juno_robot.launch`,
- `backend/src/robot/ros_jupiter_interface.py`,
- backend API updates to consume ROS speech transcripts,
- ROS integration documentation.

### Final responsibilities

Anas should own the live robot/ROS side and produce the RQT graph evidence.

#### Tasks

1. **ROS node verification**
   - Confirm these nodes can run on the robot/lab machine:
     - `camera_node`
     - `microphone_node`
     - `moonshine_transcriber`
     - `juno_tts_node`
   - Confirm the bringup launch starts the required nodes.

2. **Topic verification**
   - Verify these topics appear:
     - `/camera/image_raw`
     - `/audio/raw`
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

### Deliverables

- RQT graph screenshot.
- Topic list screenshot or notes.
- Short video clip of speech/TTS working, if possible.
- Report subsection: **ROS Development and Robot Integration**.
- Report subsection contribution: labelled ROS node/topic table and RQT graph explanation.

---

## 3. Jon — Integration, Manual, and Report Structure Lead

### Existing contribution evidence

The current `jon_integration` branch contains:

- product requirements documentation,
- project component documentation,
- technical requirements for emotion recognition,
- scaled demo manual,
- `.gitignore` cleanup for generated files and Windows metadata.

### Final responsibilities

Jon should coordinate the final integration story and ensure the project satisfies the rubric even with scaled scope.

#### Tasks

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

### Deliverables

- Final manual/report structure draft.
- Report subsection: **Project Context, HRI Design, Scope, and Conclusion**.
- Rubric mapping table.
- Demo script.
- Clean final branch checklist.

---

## 4. Vanness — Vision and Emotion Integration Lead

### Current codebase situation

The vision path exists but should be treated as a scaled MVP:

- ROS camera publishes `/camera/image_raw`.
- Backend ROS bridge stores latest camera frame.
- `EmotionDetector` currently uses weighted mock prediction.
- `EmotionSmoother` stabilizes the displayed emotion.
- Full CNN emotion recognition is documented but not required for a stable final demo.

### Final responsibilities

Vanness should own the vision story and make it credible without overpromising.

#### Tasks

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
   - Describe future CNN path using `technical_requirements_emotion.md`.

5. **Evaluation notes**
   - Prepare simple evaluation criteria:
     - camera topic active,
     - emotion label changes are stable,
     - break recommendation responds to tired/stressed/frustrated state,
     - dashboard updates without reload.

### Deliverables

- Report subsection: **Vision Integration and Emotion-Aware Behaviour**.
- Emotion screenshot from dashboard.
- Short explanation of mock/current implementation vs future CNN implementation.
- Optional simple camera evidence screenshot.

---

## 5. Zhao Qian — Backend QA, Submission, and Evidence Lead

### Existing contribution evidence

The repository is under Zhao Qian's GitHub organization/account context and the initial commit is associated with Ong Zhao Qian. This makes Zhao Qian suitable to own final submission packaging, GitHub link readiness, and final quality checks.

### Final responsibilities

Zhao Qian should make sure the project is complete from an evaluator's perspective: working backend features, clean submission, video link, GitHub link, and final evidence.

#### Tasks

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

### Deliverables

- Final GitHub link.
- Final video link.
- Backend QA checklist.
- Report subsection: **Backend Features, Testing, and Final Evidence**.
- Final report with screenshots inserted and formatting checked.

---

## Report Writing Distribution

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

### Report Writing Rules

- Each member must write their own assigned section in clear paragraph form, not only bullet points.
- Every technical claim should have evidence: screenshot, code path, RQT graph, video timestamp, or file reference.
- Use honest wording for incomplete parts, especially emotion recognition and speech reliability.
- Keep the final report consistent: same project title, same terminology, same topic names.
- Jon and Zhao Qian should edit for flow, but should not have to write every section from scratch.

---

## Rubric-to-Member Mapping

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

## 2-3 Week Execution Plan

## Week 1 — Stabilize Mock Mode and Documentation

| Task | Owner |
|---|---|
| Confirm backend starts and command pipeline works in mock/dashboard mode | Jon, Zhao Qian |
| Confirm dashboard displays all required panels | Mack |
| Confirm ROS launch and package structure on local/robot environment | Anas |
| Confirm emotion state appears on dashboard | Vanness |
| Draft final report skeleton and rubric table | Jon |
| Each member drafts their own assigned report subsection outline | All |

## Week 2 — Robot Lab Integration and Evidence Capture

| Task | Owner |
|---|---|
| Test camera/microphone/transcriber/TTS on robot | Anas |
| Capture RQT graph screenshots | Anas, Zhao Qian |
| Capture dashboard screenshots and short demo clips | Mack, Zhao Qian |
| Verify camera/emotion story and collect evidence | Vanness |
| Rehearse final demo script | All |
| Each member writes first full draft of their report subsection | All |

## Week 3 — Polish Only

| Task | Owner |
|---|---|
| Assemble final report | Jon, Zhao Qian |
| Review and improve all member-written sections | All |
| Insert screenshots/video/GitHub links | Zhao Qian |
| Polish README/manual wording | Mack, Jon |
| Final robot demo recording if needed | Anas, Mack |
| Final branch cleanup and submission check | Jon, Zhao Qian |

---

## Final Demo Roles

| Demo segment | Person leading |
|---|---|
| Introduce project context and HRI goal | Jon |
| Show dashboard and command flow | Mack |
| Explain/run ROS nodes and RQT graph | Anas |
| Explain vision/emotion integration | Vanness |
| Present final evidence, GitHub/video/report wrap-up | Zhao Qian |

---

## Minimal Demo Script

1. Jon introduces JUNO Assist as an emotion-aware student productivity robot.
2. Mack shows dashboard in idle mode.
3. User says/types “Hey, Juno”.
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

## Final Quality Gate Before Submission

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

## Presentation Strategy

The team should present the project as a complete, reliable integration prototype:

- Do **not** claim full autonomous navigation.
- Do **not** claim medical-grade emotion detection.
- Do **not** depend on a cloud LLM during the live demo.
- Do emphasize ROS integration, HRI safety, two-way speech, dashboard feedback, and practical fallback design.

Best one-sentence pitch:

> “JUNO Assist is a ROS-integrated human-robot interaction prototype that helps students manage study tasks through wake-confirmed speech interaction, dashboard feedback, emotion-aware break suggestions, and a reliable fallback mode for limited robot access.”

## Important Scope Rule

If the team runs out of time, prioritize these deliverables in order:

1. Dashboard + backend command pipeline works.
2. ROS topics and RQT graph evidence exist.
3. TTS/speech or dashboard backup interaction works.
4. Emotion state is visible and explained honestly.
5. Report/manual explicitly maps to every rubric item.

Do not sacrifice stability for advanced features. A simple working end-to-end robot interaction will score better than an ambitious but unreliable system.
