# JUNOAssist — Revised Action Plan (Post-Feedback)

**Updated:** 19 June 2026  
**Submission deadline:** Sunday, 21 June 2026

This plan was written in direct response to the feedback received on 17 June 2026. It maps each piece of feedback to a concrete change, assigns ownership to a team member, and defines a single cohesive demo scenario to replace the disconnected feature-by-feature presentation used previously.

---

## Revised Demo Scenario

> A student sits at their desk under deadline stress. JUNO detects stress via camera and voice, automatically plays calming music without the student needing to press anything, recommends a movement break after sustained stress, and supports the student's return to focused study through a timer, reminders, and a weekly schedule.

Three emotional states drive JUNO's responses:

| Detected State | JUNO's Response |
|----------------|-----------------|
| Stressed / Fearful | Calming music auto-plays + break recommended |
| Tired / Sad | Break recommended + calming music |
| Frustrated / Angry | Calming music auto-plays + break recommended |

Schedule and reminders are presented as long-term stress management tools, not the core detection loop. The study timer is framed as a focus and recovery aid, not a stress monitor.

---

## Team Responsibilities

### Zhao Qian — Vision & Timer

**Goal:** Vision triggers a break timer when sustained stress is detected. Timer supports the study session.

#### Default study timer
When the user requests a study session without specifying a duration, JUNO defaults to 25 minutes (Pomodoro method).
- `backend/src/productivity/timer_service.py` — add `start_default_timer()` method
- `dashboard/src/components/TimerPanel.jsx` — add a "Start 25-min session" quick-start button

#### Break timer triggered by sustained stress
When a stress-class emotion (stressed, fearful, tired) is detected continuously for 30 seconds:
- JUNO speaks: *"You have been stressed for a while. A short break can help — starting a 5-minute break timer now."*
- A 5-minute break timer starts automatically
- The break recommendation panel is highlighted on the dashboard

Relevant files:
- `backend/src/api/app.py` — `_emotion_monitor_loop()`: add stress duration counter; on threshold, start break timer and set `break_suggested` flag in robot state
- `backend/src/core/state.py` — add `break_suggested` to the state snapshot
- `dashboard/src/components/TimerPanel.jsx` — display "Break in progress" when a break timer is running

---

### Jon — Music

**Goal:** Music plays automatically based on detected emotion, with no manual input required. Genre buttons remain available as a user override.

#### Automatic music playback on stress detection
When emotion changes to a stress-class state and no music is currently playing:
- Backend calls `music_service.play_for_emotion(current_emotion)` automatically
- JUNO speaks: *"Playing some calming music for you."*
- Dashboard iframe updates via the existing WebSocket state flow
- Auto-play applies only to stress-class emotions; happy and neutral states do not trigger music

Relevant files:
- `backend/src/api/app.py` — `_emotion_monitor_loop()`: after each emotion update, check if stress-class and music is stopped, then trigger playback

#### Manual genre override (existing feature)
The five mood buttons (Focus, Calm, Happy, Gentle, Cool Down) on the music panel remain available. The user can override the auto-selected playlist at any time. TTS announces the selected playlist title without referencing emotion.

#### Music during break
When a break timer starts, calming music plays automatically if not already playing, reinforcing the break recommendation with an appropriate audio environment.

---

### Mack — Fitness Game (Movement Break) & Emotion Visibility

**Goal:** The fitness game is presented as a movement break and stress-relief tool. The emotion indicator is visually prominent and clearly readable on video.

#### Movement break integration
- `dashboard/src/components/FitnessPanel.jsx` — rename panel heading to "Movement Break" with subtitle: *"A short movement break helps reset focus and reduce stress."*
- When `break_suggested` is true in WebSocket state, display a highlighted prompt: *"JUNO recommends a movement break — try the destress game!"* with a button that opens the fitness panel

#### Emotion indicator improvements
- `dashboard/src/components/StatusPanel.jsx` — colour-code emotion states:
  - Red (`#ef4444`) — stressed, fearful, angry, frustrated
  - Blue (`#60a5fa`) — tired, sad
  - Green (`#4ade80`) — happy, calm, focused
  - Grey (`#94a3b8`) — neutral, unknown
- Increase badge and font size for readability on video
- Add `animate-pulse` when a stress-class emotion is active
- Reposition indicator to a prominent location (top or centre of dashboard)

---

### Anas — Reminders

**Goal:** Reminders persist across restarts, support full CRUD, and notify the user at 30 minutes and at the due time.

#### Persistent storage
Reminders are currently stored in SQLite but cleared on each backend restart. This will be fixed so reminders survive a terminal kill and backend restart.
- `backend/src/calendar_module/calendar_service.py` — remove reminders from the startup reset path
- Reminders cannot be backdated; `date >= today` is enforced on creation

#### CRUD functionality
All four operations demonstrated clearly on the dashboard:
- **Create** — voice ("remind me to submit assignment tomorrow at 9am") or dashboard form
- **Read** — upcoming reminders listed in the reminders panel
- **Update** — edit reminder title or time via an edit button on each reminder card
- **Delete** — mark as done or remove entirely

Relevant files: `dashboard/src/components/RemindersPanel.jsx`, `backend/src/calendar_module/calendar_service.py`

#### Proactive notifications
A background loop checks reminders every 60 seconds:
- 30 minutes before due: JUNO speaks *"Reminder: [title] is in 30 minutes."*
- At due time: JUNO speaks *"[title] is due now."*
- Each reminder is notified at most once per threshold to avoid repetition

Relevant file: `backend/src/api/app.py` — add `_reminder_notification_loop()` async task

---

### Vanness — Schedule

**Goal:** Schedule persists across restarts, supports full CRUD including update, and notifies the user at 30 minutes and at the scheduled time.

#### Persistent storage
Same fix as reminders — schedule items will not be cleared on restart.
- `backend/src/calendar_module/calendar_service.py` — remove schedule items from the startup reset path
- Schedule entries can be backdated (weekly and monthly historical views are valid)

#### CRUD functionality
- **Create** — voice ("add study session on Friday at 2pm") or dashboard form
- **Read** — today's schedule and a weekly view on the dashboard
- **Update** — edit title, date, or time via an edit button
  - `backend/src/api/app.py` — add `PUT /api/schedule/{item_id}` endpoint if not present
- **Delete** — remove completed or cancelled items

Relevant files: `dashboard/src/components/SchedulePanel.jsx`, `backend/src/api/app.py`, `backend/src/calendar_module/calendar_service.py`

#### Proactive notifications
Same pattern as reminder notifications, coordinated with Anas to share a single notification loop:
- 30 minutes before: *"Upcoming: [title] in 30 minutes."*
- At scheduled time: *"[title] starts now."*

---

## Demo Sequence

| Step | What the audience sees |
|------|------------------------|
| 1 | Student says wake word → JUNO activates and opens dashboard |
| 2 | Student appears stressed in front of camera |
| 3 | Emotion indicator on dashboard turns red |
| 4 | Calming music plays automatically — no button pressed |
| 5 | After 30 seconds of detected stress, JUNO recommends a break and starts a 5-minute break timer |
| 6 | Movement break panel highlights with a prompt to try the destress game |
| 7 | Student plays the fitness game during the break |
| 8 | Break timer ends; student says "start study timer" — 25-minute session begins |
| 9 | Student asks "what are my reminders?" — list is read aloud and displayed |
| 10 | Student adds a reminder by voice |
| 11 | Student views the weekly schedule |
| 12 | Student says "power off" — JUNO shuts down gracefully |

---

## What Is Not Changing

| Item | Reason |
|------|--------|
| Emotion recognition model retraining | Insufficient time; speech-based emotion detection is reliable and will be used alongside camera detection |
| Wake word and confirmation flow | Working correctly |
| TTS and ROS integration | Working correctly |
| Authentication and login | Working correctly |

---

## Pre-Submission Checklist

- [ ] Emotion auto-play tested: stress detected → music plays without any button press
- [ ] Break timer tested: 30 seconds of stress → timer fires and panel highlights
- [ ] Reminders survive backend restart
- [ ] Schedule survives backend restart
- [ ] Reminder and schedule notifications fire at 30 min and 0 min
- [ ] Emotion indicator colour-coded and visible at a glance on video
- [ ] Demo recorded with live camera, not static images
- [ ] Section 7 (Peer Assessment) filled in the report
- [ ] Demo video link on report cover page updated after recording
