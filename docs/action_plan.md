# JUNOAssist — Action Plan (Post-Feedback)

**Scenario:** Student under deadline stress → emotion detected → music auto-plays → break recommended → uses schedule → sets timer.

---

## Do in this order

### 1. Music autoplay by emotion
Biggest lecturer complaint. Auto-trigger playlist when smoothed emotion state changes — no manual button press.
- File: `dashboard/src/components/MusicPanel.jsx`
- Wire existing emotion state from WebSocket to auto-call `POST /api/music/play`
- No new model needed

### 2. Break recommendation visible on dashboard
Backend already detects tiredness/stress and generates recommendation via `backend/src/productivity/break_recommender.py`. Lecturer said this is valid but was invisible.
- Add dashboard panel that shows recommendation when emotion is sad/stressed/tired
- No backend changes needed

### 3. Emotion indicator colour-coding
Make it readable on video.
- Red = stressed/frustrated, Blue = tired/sad, Green = happy, Grey = neutral
- File: `dashboard/src/components/StatusPanel.jsx`

### 4. Re-record demo video
Follow the single-story storyboard in `docs/priority_demo_video.md`.
- Do this after steps 1–3 are done
- Use live camera, not static images

### 5. Peer assessment table (parallel task)
Fill Section 7 in the report — can be done by another team member at any time.

---

## Do not touch

| Feature | Reason |
|---|---|
| Schedule / Reminders | Already works, secondary stress feature, demo as-is |
| Timer | Frame in narration as study-session tool — no code change |
| Emotion model retraining | Out of scope, fall back to speech detection if live vision fails |

---

## Narrative for demo

> "JUNOAssist detects student stress and fatigue through voice and vision, then responds — recommending breaks, selecting calming music, and helping manage workload — so students can recover and refocus."

Schedule and reminders support long-term stress management. Timer supports focused study sessions. Both are secondary to the detection-and-response loop above.
