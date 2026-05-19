# Pull Request Checklist

## 1. Summary

Briefly describe what this PR changes.

- 

## 2. Component Worked On

Tick all components affected by this PR.

- [ ] Backend API / command flow
- [ ] Wake word / confirmation / robot mode state
- [ ] NLP / response generation
- [ ] Calendar / reminders / study timer / productivity
- [ ] Dashboard / frontend UI
- [ ] ROS perception package: `src/perception_pkg` camera / microphone
- [ ] ROS language package: `src/language_pkg` speech-to-text / text-to-speech
- [ ] ROS bringup package: `src/juno_bringup`
- [ ] Backend ROS bridge / Jupiter robot interface
- [ ] Vision / emotion detection and smoothing
- [ ] Documentation / report / manual
- [ ] Repo cleanup / `.gitignore`
- [ ] Testing / demo evidence

## 3. What Has Been Completed

Tick everything that is done in this PR.

- [ ] Code implemented
- [ ] Code reviewed by PR author
- [ ] Related documentation updated
- [ ] Report/manual section updated, if relevant
- [ ] Screenshots, video, RQT graph, or terminal evidence added, if relevant
- [ ] Known limitations written clearly below

Completed details:

- 

## 4. What Is Not Completed Yet

Be honest and specific. Write anything that still needs follow-up.

- 

## 5. Testing Evidence

Tick all checks that were performed.

### Backend

- [ ] Backend starts successfully
- [ ] `/api/status` checked
- [ ] `/api/command` checked
- [ ] Wake flow tested: `Hey, Jude`
- [ ] Confirmation flow tested: `Yes`
- [ ] Schedule/deadline command tested
- [ ] Reminder command/form tested
- [ ] Timer command tested
- [ ] Break/status recommendation tested
- [ ] Sleep command tested
- [ ] Python tests passed
- [ ] Not applicable

### Dashboard

- [ ] Dashboard starts successfully
- [ ] Dashboard connects to backend
- [ ] WebSocket status updates work
- [ ] Command panel tested
- [ ] Schedule panel checked
- [ ] Timer panel checked
- [ ] Emotion/status display checked
- [ ] Not applicable

### ROS / Robot

- [ ] `perception_pkg` builds or launches successfully
- [ ] `language_pkg` builds or launches successfully
- [ ] `juno_bringup` launch file checked
- [ ] `/camera/image_raw` checked
- [ ] `/audio/raw` checked
- [ ] `/speech/transcript` checked
- [ ] `/juno/tts` checked
- [ ] `/juno/led_state` checked, if relevant
- [ ] RQT graph checked or updated
- [ ] Robot/lab machine tested
- [ ] Not applicable

### Vision / Emotion

- [ ] Camera input path checked
- [ ] Emotion state appears on dashboard
- [ ] Emotion smoothing checked
- [ ] Break recommendation checked
- [ ] Current limitation documented: mock/simple emotion detection unless real model is implemented
- [ ] Not applicable

Testing notes / commands / evidence:

```text
Paste terminal output, screenshots, video link, or RQT evidence here if relevant.
```

## 6. Demo Impact

Does this PR affect the final demo script?

- [ ] Yes
- [ ] No

If yes, explain what changed:

- 

## 7. Report / Rubric Impact

Tick all rubric areas supported by this PR.

- [ ] HRI elements
- [ ] Codes and manual
- [ ] ROS development
- [ ] RQT graph
- [ ] Report context
- [ ] Code organization
- [ ] Vision integration
- [ ] Speech interaction, two-way
- [ ] NLP/LLM element
- [ ] Notable mention / extra feature
- [ ] Video/GitHub evidence
- [ ] Extra manual / extra RQT evidence

## 8. Clean Repository Checklist

Before requesting review, confirm this PR does not add generated or local-only files.

- [ ] No `node_modules/`
- [ ] No `.venv/`, `venv/`, or `env/`
- [ ] No `build/`, `devel/`, `install/`, `log/`, or `logs/`
- [ ] No `__pycache__/`
- [ ] No `.pyc` files
- [ ] No `*:Zone.Identifier` files
- [ ] No local database changes unless intentionally required for sample/demo data
- [ ] No secrets, API keys, or private credentials

## 9. Reviewer Focus

What should reviewers pay most attention to?

- 

## 10. Final Merge Checklist

- [ ] PR has a clear title
- [ ] PR description is complete
- [ ] Incomplete work is clearly stated
- [ ] Evidence is attached or linked where relevant
- [ ] Changes match the scaled project scope
- [ ] Ready for teammate review
