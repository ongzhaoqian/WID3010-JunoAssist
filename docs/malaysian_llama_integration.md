# Malaysian Llama Integration for JUNO Assist

This document explains how `mesolitica/Malaysian-Llama-3.2-3B-Instruct` is integrated into JUNO Assist without changing the ROS node architecture.

## 1. Integration Decision

The Hugging Face model is integrated inside the backend NLP layer, not inside the ROS nodes.

```text
ROS microphone/camera nodes
  ↓
RosJupiterInterface
  ↓
FastAPI command pipeline
  ↓
IntentClassifier
  ↓
ResponseGenerator
  ├── deterministic handlers for robot-safe actions
  └── MalaysianLlamaClient for open-ended replies
  ↓
RosJupiterInterface publishes /juno/tts
  ↓
tts_node.py speaks response
```

This preserves the existing robotics architecture because:

- ROS nodes still only publish or subscribe to robot I/O topics.
- The backend remains the orchestration layer.
- The model is not allowed to directly publish ROS messages, start timers, change robot mode, or write reminders.
- Deterministic handlers still control safety-sensitive or state-changing actions.

## 2. Files Added or Updated

| File | Purpose |
|---|---|
| `backend/src/nlp/llm_client.py` | Lazy Hugging Face client for Malaysian Llama. |
| `backend/src/nlp/response_generator.py` | Calls Malaysian Llama only as a fallback for open-ended replies. |
| `backend/src/core/config.py` | Adds environment-based LLM configuration. |
| `backend/src/api/app.py` | Adds `/api/ai/status` and exposes the AI assistant feature. |
| `backend/requirements-llm.txt` | Optional model runtime dependencies. |
| `backend/.env.example` | Example environment variables for local, ROS, and LLM modes. |

## 3. Why the Model Is Lazy-Loaded

The model is not loaded during backend startup. It loads only when:

1. `JUNO_LLM_ENABLED=true`, and
2. the command reaches the LLM fallback path.

This avoids slowing down the robot boot process or breaking a ROS demo on a machine without enough RAM/GPU.

## 4. Runtime Setup

From the backend directory:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-llm.txt
```

Enable the model:

```bash
export JUNO_LLM_ENABLED=true
export JUNO_LLM_MODEL_ID=mesolitica/Malaysian-Llama-3.2-3B-Instruct
export JUNO_LLM_DEVICE_MAP=auto
export JUNO_LLM_TORCH_DTYPE=auto
python main.py
```

Check whether the backend sees the model configuration:

```bash
curl http://localhost:8000/api/ai/status
```

## 5. ROS Mode with the Model Enabled

Use the same ROS launch flow as before. Only the backend environment changes.

```bash
cd backend
source ../devel/setup.bash
source .venv/bin/activate
export JUNO_ROBOT_INTERFACE=ros
export JUNO_LLM_ENABLED=true
export JUNO_LLM_MODEL_ID=mesolitica/Malaysian-Llama-3.2-3B-Instruct
python main.py
```

The ROS topics remain unchanged:

| Direction | Topic | Message Type |
|---|---|---|
| ROS to backend | `/speech/transcript` | `std_msgs/String` |
| ROS to backend | `/camera/image_raw` | `sensor_msgs/Image` |
| Backend to ROS | `/juno/tts` | `std_msgs/String` |
| Backend to ROS | `/juno/led_state` | `std_msgs/String` |

## 6. Behavioural Boundary

The model may generate conversational responses such as study advice, clarification, or encouragement. The model should not be used as the authority for robot actions.

Handled deterministically:

- Wake command
- Confirmation
- Sleep mode
- Schedule lookup
- Deadline lookup
- Timer start
- Reminder instruction
- Music playback
- Break recommendation

Handled by Malaysian Llama fallback:

- Open-ended questions not covered by the rule-based intent classifier
- General student-support replies
- Multilingual Malaysian-context conversational responses

## 7. Suggested Demo Commands

Start with deterministic commands:

```text
Hey, Juno
Yes
What do I have today?
Set a 25 minute timer.
```

Then test an open-ended command after enabling the model:

```text
I feel unproductive today. How should I plan my next study session?
```

Expected behaviour:

- The command passes through the same backend pipeline.
- The LLM generates a short spoken reply.
- The backend sends the generated text to `/juno/tts` in ROS mode.
