# Whisper Tiny Integration for JUNO Assist

This document explains the robot-friendly speech pipeline after replacing the heavy Malaysian Llama + LoRA local model path with Hugging Face `openai/whisper-tiny`.

## Why Whisper Tiny Is Used

The robot-connected local machine may not have enough memory or GPU resources to run a large text-generation base model plus LoRA adapter. `openai/whisper-tiny` is much smaller and is suitable for lightweight automatic speech recognition (ASR) in the robotics demo.

Important scope note: Whisper is an ASR/speech-translation model, not a chatbot or general reasoning LLM. In JUNO Assist, Whisper converts speech into text. The backend still handles intent classification, timers, schedules, reminders, music, and responses through deterministic logic.

## Updated ROS Flow

```text
User speech
  ↓
microphone_node.py publishes /audio/raw
  ↓
transcriber.py runs openai/whisper-tiny ASR
  ↓
/speech/transcript
  ↓
FastAPI backend RosJupiterInterface listens to /speech/transcript
  ↓
Backend command pipeline: wake/confirm/intent/response
  ↓
/juno/tts
  ↓
tts_node.py speaks with a British English voice where available
```

Manual fallback remains available:

```text
example_transcriptor.py or external ASR
  ↓
/speech/raw_transcript
  ↓
transcriber.py relays it to /speech/transcript
```

## Key Files Changed

| File | Purpose |
|---|---|
| `src/language_pkg/scripts/transcriber.py` | New Whisper Tiny ROS ASR node. Subscribes to `/audio/raw`, publishes `/speech/transcript`, and preserves `/speech/raw_transcript` fallback. |
| `src/language_pkg/scripts/helper.py` | Downloads/cache-prepares the configured Whisper model. |
| `src/juno_bringup/launch/juno_robot.launch` | Starts `whisper_tiny_transcriber` instead of the heavy language normaliser. |
| `backend/src/core/config.py` | Adds `JUNO_ASR_*` settings and disables text LLM use by default. |
| `backend/src/speech/speech_to_text.py` | Adds a lazy backend-side Whisper utility for future non-ROS audio paths. |
| `backend/.env.example` | Documents Whisper Tiny ASR settings. |
| `backend/requirements-asr.txt` | Optional dependencies for ASR. |
| `src/language_pkg/requirements-asr.txt` | Same dependency list for ROS language package setup. |

## Recommended Environment Variables

```bash
export JUNO_ASR_MODEL_ID=openai/whisper-tiny
export JUNO_ASR_TASK=translate
export JUNO_ASR_LANGUAGE=
export JUNO_ASR_SAMPLE_RATE=16000
export JUNO_ASR_WINDOW_SECONDS=4.0
export JUNO_ASR_MIN_RMS=0.008
export JUNO_ASR_DEVICE=-1
```

Use `JUNO_ASR_TASK=translate` when you want non-English speech to be translated into English before backend intent classification. Use `JUNO_ASR_TASK=transcribe` when you want the transcript to stay in the spoken language.

## Setup

Install normal backend dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Install ASR dependencies on the machine running the ROS transcriber:

```bash
pip install -r requirements-asr.txt
```

Or, from the project root:

```bash
pip install -r src/language_pkg/requirements-asr.txt
```

## Running the ROS Pipeline

```bash
roscore
```

In another terminal:

```bash
catkin_make
source devel/setup.bash
roslaunch juno_bringup juno_robot.launch
```

Then start the backend in ROS mode:

```bash
cd backend
source ../devel/setup.bash
export JUNO_ROBOT_INTERFACE=ros
python main.py
```

The backend still consumes `/speech/transcript`, so no backend ROS topic changes are required.

## Testing

Check microphone audio:

```bash
rostopic echo /audio/raw
```

Check recognised speech:

```bash
rostopic echo /speech/transcript
```

Manual fallback:

```bash
rostopic pub /speech/raw_transcript std_msgs/String "data: 'Hey, Juno'"
rostopic pub /speech/raw_transcript std_msgs/String "data: 'Yes'"
rostopic pub /speech/raw_transcript std_msgs/String "data: 'What is my schedule today?'"
```

## Limitations

- Whisper Tiny transcribes or translates speech; it does not replace a reasoning/chat model.
- British English accent is handled by `tts_node.py` voice selection. Whisper output spelling cannot guarantee British spelling for every phrase.
- Short, clear commands work best in noisy lab environments.
- The first transcription may be slower because the model is lazy-loaded.
