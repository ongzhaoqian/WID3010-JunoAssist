# JUNO TTS Voice/Accent Fix — Problem Statement, Scope, and Technical Plan

**Status:** Proposed, not yet implemented
**Author:** Investigation by Claude (Vanness), 2026-06-20

## Problem Statement

JUNO's text-to-speech output is described as "robotic" and a British accent that
is "not soothing at all." Previous attempts to change the configured locale to
`en_US`/`en_GB` did not change the resulting voice — the accent stayed the same
regardless of configuration.

## Root Cause

The TTS node (`src/language_pkg/scripts/tts_node.py`) reads a `voice_locale`
setting (ROS param `~voice_locale` → env `JUNO_TTS_VOICE_LOCALE` → default
`en_GB`, see line 47).

### Confirmed root cause on the actual robot: the launch file overrides the env var

`src/juno_bringup/launch/juno_robot.launch` (lines 35-42) starts `tts_node.py`
with hardcoded `<param>` tags:

```xml
<node pkg="language_pkg" type="tts_node.py" name="juno_tts_node" output="screen">
  <param name="tts_topic" value="/juno/tts" />
  <param name="tts_done_topic" value="/juno/tts_done" />
  <param name="tts_stop_topic" value="/juno/tts_stop" />
  <param name="voice_locale" value="en_GB" />
  <param name="rate" value="165" />
  <param name="backend" value="espeak" />
</node>
```

`rospy.get_param('~voice_locale', os.getenv(...))` only falls back to the env
var when **no ROS param exists**. Because the launch file explicitly sets
`voice_locale` (and `backend`, `rate`) on the parameter server, those values
always win — `JUNO_TTS_VOICE_LOCALE` is silently ignored whenever the robot
is started via `roslaunch juno_bringup juno_robot.launch`. This is the most
likely reason previous env-var-only attempts had no effect on the real robot.

### Important correction: the pyttsx3 bias bug does not currently trigger on the robot

The launch file also hardcodes `backend="espeak"` (not `auto`/`pyttsx3`).
`_init_pyttsx3()` only runs when backend is `auto` or `pyttsx3` (line 64), so
on the robot as currently launched, `self.engine` stays `None` and `_speak()`
(line 192) goes straight to `_speak_with_espeak()`. That means:

1. **`_select_british_voice()`** (lines 100-131) — the pyttsx3 voice-matching
   method described in the original analysis below — is **not actually
   reached on the robot today**, because the pyttsx3 backend is never
   initialized. Its matching logic is still a real bug (an OR-condition that
   can return a British voice before requested locale is checked properly),
   but it would only matter if `backend` is changed to `auto` or `pyttsx3`.

2. **`_candidate_voices()`** (lines 213-223) — used by the espeak/espeak-ng
   subprocess path that the robot actually uses. This one does put the
   requested locale first in the list and returns on the first successful
   subprocess exit, so it is *not* inherently biased toward British. Once the
   `voice_locale` param genuinely changes (see Testing Plan below) and the
   requested voice is installed in espeak, this path should honor it
   correctly.

There's also a secondary, unrelated config mismatch: the README documents
`JUNO_TTS_VOICE=en-gb+f3`, but the code only reads `JUNO_TTS_VOICE_LOCALE`.
`JUNO_TTS_VOICE` is dead config and has no effect.

Two hardcoded log lines also assume British English regardless of config
(`"Using pyttsx3 British English voice"`, `"JUNO says in British English"`).
These only fire on the pyttsx3 path, so they're currently dormant on the
robot, but should still be fixed for correctness if `backend` is ever changed.

## Scope

**Confined to a single file:** `src/language_pkg/scripts/tts_node.py`.

The backend ROS bridge (`backend/src/robot/ros_jupiter_interface.py`) only
publishes plain text strings to the `/juno/tts` topic and never touches
voice/locale/accent — it has no knowledge of TTS internals. The topic
contract (`/juno/tts`, `/juno/tts_stop`, `/juno/tts_done`) does not change.

**Not in scope / not touched:**
- Backend (`backend/src/`), dashboard (`dashboard/src/`), STT/Whisper node,
  camera node, or any other ROS package.
- The publish/subscribe topic names or message types.
- Switching to a different TTS engine entirely (see "Out of scope" below).

This means the fix carries very low blast radius — no other working module
depends on, or is affected by, the internals of `tts_node.py`'s voice
selection.

## Technical Plan

1. **Rename and fix `_select_british_voice()` → `_select_voice()`**
   (lines 100-131). Change the matching logic so the requested locale is
   checked first and exclusively; only fall back to the hardcoded
   British-token list as a true last resort (i.e., only when *no* voice on
   the system matches the requested locale at all), and only if no locale was
   requested or pyttsx3 has no matching voice installed.

2. **Fix `_candidate_voices()`** (lines 213-223): keep `requested` first in
   the candidate list (already correct), but make the fallback chain
   (`en-gb`, `en-uk`, `en-rp`, `en`) explicit as a degrade path the team can
   choose to disable per-deployment (e.g., via a `strict_locale` flag) rather
   than something that silently runs every time the requested voice fails for
   any reason, including transient ones.

3. **Update the two hardcoded log strings** to reflect the actual configured
   locale instead of always saying "British English."

4. **Decide on the default locale** (`en_GB` is currently hardcoded in
   `src/juno_bringup/launch/juno_robot.launch` line 39 and
   `backend/.env.example` line 124). Either:
   - Leave default as `en_GB` and let operators override per-deployment, or
   - Switch the default to `en_US` (or another locale) team-wide.

5. **Fix the dead `JUNO_TTS_VOICE` reference in README.md** (line ~312) to
   use the correct variable name `JUNO_TTS_VOICE_LOCALE`, or document both
   the locale (e.g. `en_US`) and the engine-specific voice ID format
   (e.g. `en-us+f3` for espeak) if finer voice selection is desired.

## Verification Plan

- On the robot (or a Linux dev machine with `espeak-ng`/`pyttsx3` installed),
  run `espeak --voices` / `espeak-ng --voices` to confirm `en-us` is actually
  installed.
- Set `JUNO_TTS_VOICE_LOCALE=en_US` and launch `tts_node.py` standalone;
  confirm via `rospy.loginfo` output which voice ID was actually selected,
  and listen to confirm the accent changed.
- Repeat with `en_GB` to confirm the fallback/default path still works
  (regression check).
- Re-run existing integration/launch flow end-to-end (backend → `/juno/tts` →
  tts_node → speech) to confirm no behavior change outside of accent.

## Testing Plan on the Real Robot

Because the launch file hardcodes `voice_locale`/`backend`/`rate`, an env var
change alone will not be visible during a normal `roslaunch` run. Two ways to
test without permanently altering the launch file:

**Option A — run `tts_node.py` standalone with a private param override
(recommended for a quick test, no file edits):**

1. Comment out or skip the `juno_tts_node` block in
   `src/juno_bringup/launch/juno_robot.launch` for this test run (or simply
   don't roslaunch the full bringup file — start the other nodes you need
   separately).
2. Run:
   ```bash
   rosrun language_pkg tts_node.py _voice_locale:=en_US _backend:=espeak _rate:=165 \
     _tts_topic:=/juno/tts _tts_done_topic:=/juno/tts_done _tts_stop_topic:=/juno/tts_stop
   ```
3. Publish a test phrase and listen:
   ```bash
   rostopic pub /juno/tts std_msgs/String "data: 'Hello, this is a test of the American accent.'"
   ```

**Option B — temporarily edit the launch file value, then revert:**

1. Change `src/juno_bringup/launch/juno_robot.launch` line 39 to
   `value="en_US"`.
2. `roslaunch juno_bringup juno_robot.launch` as normal and listen to JUNO
   speak.
3. Revert the line back to `en_GB` (or to whatever the team decides as the
   final default) once testing is done.

**Before either option:** confirm the requested voice is actually installed
in the robot's espeak/espeak-ng package:
```bash
espeak --voices=en
# or
espeak-ng --voices=en
```
If `en-us` isn't listed, no config change will produce an American accent —
the voice data would need to be installed first.

**While testing:** watch the node's log output. `_speak_with_espeak()` logs
`"Trying TTS command: %s -v %s"` (line 235) for every voice it attempts, so
you can confirm exactly which voice string was tried and whether it
succeeded, rather than guessing from the audio alone.

## Out of Scope (separate discussion)

Even after this fix, `pyttsx3`/`espeak` voices are synthesized and inherently
robotic-sounding — changing the accent will not by itself make the voice
"soothing." If a more natural/soothing voice is desired, that requires
evaluating a different TTS engine entirely (e.g. Piper, edge-tts, a cloud
neural TTS API), which is a larger architectural change with its own
latency/offline/cost tradeoffs and is **not** part of this fix.
