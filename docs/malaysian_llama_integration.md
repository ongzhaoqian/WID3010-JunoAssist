# Malaysian Llama + LoRA Integration for JUNO Assist

This document explains how `mesolitica/Malaysian-Llama-3.2-3B-Instruct` and the LoRA adapter `mackwongyy/malaysian-feedback-lora-5k-data` are integrated into JUNO Assist while preserving the ROS node architecture.

## 1. Integration Decision

Malaysian Llama is a text-generation model, not a direct audio speech-to-text model. Therefore, Moonshine has been removed from the ROS language package, and the speech pipeline is now designed around text normalisation:

```text
External/Jupiter ASR, Whisper/Vosk, or manual transcript publisher
  ↓
/speech/raw_transcript
  ↓
src/language_pkg/scripts/transcriber.py
  ↓
Normalises Malaysian-context utterances into standard British English
  ↓
/speech/transcript
  ↓
FastAPI RosJupiterInterface
  ↓
Backend command pipeline
  ↓
IntentClassifier + deterministic handlers + ResponseGenerator
  ↓
/juno/tts
  ↓
tts_node.py speaks in a British English voice where available
```

The model is also integrated in the backend NLP layer for two purposes:

1. **Input normalisation before intent classification** — Malay, Mandarin, Tamil, Manglish, or Malaysian dialectal phrasing can be converted into standard British English before the rule-based intent classifier runs.
2. **Open-ended response generation** — questions not covered by deterministic robot actions can be answered in concise British English.

## 2. Behavioural Boundary

The LLM is not allowed to directly control ROS topics, robot mode, timers, reminders, LEDs, or the dashboard. Robot-state changes remain deterministic.

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

Handled by Malaysian Llama + LoRA:

- Normalising Malaysian-context input into British English
- Open-ended student-support replies
- Conversational clarification and productivity suggestions

## 3. Files Added or Updated

| File | Purpose |
|---|---|
| `backend/src/nlp/llm_client.py` | Lazy Hugging Face client for the base model and LoRA adapter. |
| `backend/src/nlp/input_normalizer.py` | Converts Malaysian-context user input into standard British English before intent classification. |
| `backend/src/nlp/response_generator.py` | Calls the LLM only for open-ended fallback replies. |
| `backend/src/core/config.py` | Adds environment-based base model, adapter, generation, and normalisation settings. |
| `backend/src/api/app.py` | Routes dashboard and ROS speech input through the shared normalisation + command pipeline. |
| `backend/requirements-llm.txt` | Optional model runtime dependencies, including `peft`. |
| `src/language_pkg/scripts/transcriber.py` | Replaces Moonshine with a text normalisation node that publishes `/speech/transcript`. |
| `src/language_pkg/scripts/tts_node.py` | Selects a British English voice in `pyttsx3` or falls back to `espeak -v en-gb`. |
| `src/juno_bringup/launch/juno_robot.launch` | Keeps ROS node boundaries intact while changing the language node role. |

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

Enable the model and adapter:

```bash
export JUNO_LLM_ENABLED=true
export JUNO_LLM_MODEL_ID=mesolitica/Malaysian-Llama-3.2-3B-Instruct
export JUNO_LLM_ADAPTER_ID=mackwongyy/malaysian-feedback-lora-5k-data
export JUNO_LLM_DEVICE_MAP=auto
export JUNO_LLM_TORCH_DTYPE=auto
python main.py
```

Check whether the backend sees the model and adapter configuration:

```bash
curl http://localhost:8000/api/ai/status
```

Expected status fields include:

```json
{
  "model_id": "mesolitica/Malaysian-Llama-3.2-3B-Instruct",
  "adapter_id": "mackwongyy/malaysian-feedback-lora-5k-data",
  "output_policy": "standard British English"
}
```

## 5. ROS Mode

Use the same ROS launch flow as before:

```bash
roscore
catkin_make
source devel/setup.bash
roslaunch juno_bringup juno_robot.launch
```

For a lightweight demo, publish raw candidate text manually:

```bash
rosrun language_pkg example_transcriptor.py
```

Or publish directly:

```bash
rostopic pub /speech/raw_transcript std_msgs/String "data: 'Apa jadual saya hari ini?'"
```

The language node publishes the British English transcript to:

```text
/speech/transcript
```

The backend then consumes `/speech/transcript` as before.

## 6. Optional ROS-Side LLM Normalisation

By default, the backend performs LLM normalisation to avoid loading the model twice. If you want the ROS language node itself to perform normalisation, enable:

```bash
export JUNO_ROS_LLM_NORMALISE=true
export JUNO_LLM_MODEL_ID=mesolitica/Malaysian-Llama-3.2-3B-Instruct
export JUNO_LLM_ADAPTER_ID=mackwongyy/malaysian-feedback-lora-5k-data
```

Only enable this on hardware with enough memory, because loading the same model in both ROS and backend processes can be expensive.

## 7. British English TTS

`tts_node.py` now attempts to select a British English voice from `pyttsx3`. If no such voice is available, it falls back to:

```bash
espeak -v en-gb
```

The TTS node does not translate by itself. It speaks the British English text generated by the backend or the normalisation node.

## 8. Suggested Demo Commands

```text
Hey, Juno
Yes
Apa jadual saya hari ini?
Set a 25 minute timer.
Saya rasa blur hari ini, macam mana nak mula study?
Juno, go to sleep.
```

Expected behaviour:

- Malaysian-context utterances are normalised into standard British English.
- The backend command pipeline remains unchanged.
- Deterministic robot actions remain safe and predictable.
- Spoken output is in British English.
