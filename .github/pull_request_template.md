# Pull Request Checklist

## 1. Summary

Briefly describe what this PR changes.

- Adds stress-triggered and study-timer-triggered break offers (JUNO asks "Would you like to take a short break?" and starts a 5-minute break timer on "yes"), with a default 25-minute study timer and stash/resume logic so a study timer frozen for a break offer resumes correctly afterwards.
- Integrates the destress (6-7) game into the dashboard as a "Movement Break" flow, then removes 6-7 score/statistics storage and the related save-score UI entirely (stats are no longer recorded).
- Reworks the dashboard layout: paired rows (DateTime+Timer, Status+Ask JUNO, Camera, Music, Movement Break, Schedule+Reminders), adds a visible Power Off button with on/off state label on Robot Status, fixes a layout overflow bug in Robot Status caused by nested viewport-breakpoint conflicts, and simplifies the Camera panel's live-status sidebar to a flat minimalist list.
- Renames "focus session" wording to "study session" across backend phrases and dashboard copy (voice recognition still accepts both phrasings).
- Updates vision/emotion labels and dashboard emphasis on the vision module per `8b7cb6e`.

## 2. Component Worked On

Tick all components affected by this PR.

- [x] Backend API / command flow
- [x] Wake word / confirmation / robot mode state
- [x] NLP / response generation
- [x] Calendar / reminders / study timer / productivity
- [x] Dashboard / frontend UI
- [ ] ROS perception package: `src/perception_pkg` camera / microphone
- [ ] ROS language package: `src/language_pkg` speech-to-text / text-to-speech
- [ ] ROS bringup package: `src/juno_bringup`
- [ ] Backend ROS bridge / Jupiter robot interface
- [x] Vision / emotion detection and smoothing
- [x] Documentation / report / manual
- [ ] Repo cleanup / `.gitignore`
- [x] Testing / demo evidence

## 3. What Has Been Completed

Tick everything that is done in this PR.

- [x] Code implemented
- [x] Code reviewed by PR author
- [ ] Related documentation updated
- [ ] Report/manual section updated, if relevant
- [x] Screenshots, video, RQT graph, or terminal evidence added, if relevant
- [x] Known limitations written clearly below

Completed details:

- Break-offer flow (stress-triggered and study-timer-complete) implemented and verified live end-to-end with audible TTS through the full ROS stack (camera_node, microphone_node, transcriber, tts_node + backend).
- Destress game stats/save-score UI and backend call removed; Movement Break panel simplified to play-only.
- Dashboard layout reorganised into the agreed 6-row plan; Robot Status overflow bug fixed; Camera panel live-status simplified; Power Off button made visible with on/off label and hover tooltip.
- "Focus session" → "study session" terminology rename across backend phrase bank and dashboard copy.

## 4. What Is Not Completed Yet

Be honest and specific. Write anything that still needs follow-up.

- Fitness profile (height/weight) form is hidden but not removed from the codebase; decide if it should be deleted outright since 6-7 stats are no longer stored.
- `docs/action_plan.md` was trimmed in this branch; confirm the report/manual still reflects the current scope before submission.

## 5. Testing Evidence

Tick all checks that were performed.

### Backend

- [x] Backend starts successfully
- [x] `/api/status` checked
- [x] `/api/command` checked
- [x] Wake flow tested: `Hey, John`
- [x] Confirmation flow tested: `Yes`
- [ ] Schedule/deadline command tested
- [ ] Reminder command/form tested
- [x] Timer command tested
- [x] Break/status recommendation tested
- [ ] Sleep command tested
- [ ] Backend unit/API tests passed
- [ ] Not applicable

### Dashboard

- [x] Dashboard starts successfully
- [x] Dashboard connects to backend
- [x] WebSocket status updates work
- [ ] Command panel tested
- [ ] Schedule panel checked
- [x] Timer panel checked
- [x] Emotion/status display checked
- [ ] Not applicable

### ROS / Robot

- [x] `perception_pkg` builds or launches successfully
- [x] `language_pkg` builds or launches successfully
- [x] `juno_bringup` launch file checked
- [ ] `/camera/image_raw` checked
- [ ] `/audio/raw` checked
- [x] `/speech/transcript` checked
- [x] `/juno/tts` checked
- [ ] `/juno/led_state` checked, if relevant
- [ ] RQT graph checked or updated
- [x] Robot/lab machine tested
- [ ] Not applicable

### Vision / Emotion

- [x] Camera input path checked
- [x] Emotion state appears on dashboard
- [ ] Emotion smoothing checked
- [x] Break recommendation checked
- [x] Current limitation documented: mock/simple emotion detection unless real model is implemented
- [ ] Not applicable

Testing notes / commands / evidence:

```text
Full live verification (roscore + juno_bringup.launch + backend with JUNO_ROBOT_INTERFACE=ros):
- Woke JUNO ("hey john" -> "yes"), started a 5s study timer via /api/timer/start.
- On completion, backend published to /juno/tts: "Your study timer is up. Would you like to take a short break?"
  and awaiting_break_confirmation/break_confirmation_reason flipped to true/"study_complete".
- Said "yes" -> "Sounds good. Starting a 5-minute break timer now." active_timer_type flipped to "break".
- On break completion, backend published: "Ding. Your Break timer is complete." active_timer_type reverted to "study".
- Note: JUNO_ROBOT_INTERFACE defaults to "mock" with no .env present, which silently no-ops TTS
  (prints instead of publishing). Must export JUNO_ROBOT_INTERFACE=ros before `python main.py`
  when testing on the robot/lab machine, otherwise no audio will be heard despite correct logic.
```

## 6. Demo Impact

Does this PR affect the final demo script?

- [x] Yes
- [ ] No

If yes, explain what changed:

- The break-offer step (study timer complete -> "Would you like to take a short break?" -> destress game) is now demoable end to end, including audible TTS. The destress game segment no longer shows or saves a 6-7 score, so the demo narration should not reference saved statistics.

## 7. Report / Rubric Impact

Tick all rubric areas supported by this PR.

- [x] HRI elements
- [ ] Codes and manual
- [ ] ROS development
- [ ] RQT graph
- [ ] Report context
- [x] Code organization
- [x] Vision integration
- [x] Speech interaction, two-way
- [ ] NLP/LLM element
- [x] Notable mention / extra feature
- [ ] Video/GitHub evidence
- [ ] Extra manual / extra RQT evidence

## 8. Clean Repository Checklist

Before requesting review, confirm this PR does not add generated or local-only files.

- [x] No `node_modules/`
- [x] No `.venv/`, `venv/`, or `env/`
- [x] No `build/`, `devel/`, `install/`, `log/`, or `logs/`
- [x] No `__pycache__/`
- [x] No `.pyc` files
- [x] No `*:Zone.Identifier` files
- [x] No local database changes unless intentionally required for sample/demo data
- [x] No secrets, API keys, or private credentials

## 9. Reviewer Focus

What should reviewers pay most attention to?

- The Robot Status layout fix (`StatusPanel.jsx`): nested Tailwind breakpoints keyed to viewport width caused the right-side stat grid to clip once the card was paired half-width with another card. Worth double-checking at other viewport sizes.
- The removal of 6-7 score saving (`FitnessGameModal.jsx`, `/api/fitness/sessions` no longer called from the dashboard) — confirm this matches product intent before merging, since the backend endpoint itself was left untouched.
- `JUNO_ROBOT_INTERFACE` defaults to `mock` with no `.env` present in this repo checkout; this silently no-ops TTS/robot calls. Worth flagging to teammates so demo rehearsals aren't run accidentally in mock mode.

## 10. Final Merge Checklist

- [ ] PR has a clear title
- [ ] PR description is complete
- [ ] Incomplete work is clearly stated
- [ ] Evidence is attached or linked where relevant
- [ ] Changes match the scaled project scope
- [ ] Ready for teammate review
