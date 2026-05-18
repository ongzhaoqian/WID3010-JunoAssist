#!/usr/bin/env python3
"""ROS language-normalisation node for JUNO Assist.

This file intentionally no longer uses Moonshine. Malaysian Llama is a text
model, not an audio ASR model, so this node expects an upstream speech source
such as Jupiter's built-in ASR, Whisper, Vosk, or a manual rostopic publisher to
publish candidate text to /speech/raw_transcript. It then optionally uses
mesolitica/Malaysian-Llama-3.2-3B-Instruct with the LoRA adapter
mackwongyy/malaysian-feedback-lora-5k-data to normalise Malaysian-context
utterances into standard British English before publishing /speech/transcript.

The output topic stays the same so the backend RosJupiterInterface remains
unchanged.
"""

from __future__ import annotations

import os
from typing import Optional

import rospy
from std_msgs.msg import Float32MultiArray, String


class MalaysianLlamaLanguageNode:
    """Publishes British-English normalised transcripts to /speech/transcript."""

    def __init__(self) -> None:
        rospy.init_node("malaysian_llama_language_normalizer", anonymous=True)

        self.input_topic = rospy.get_param(
            "~input_text_topic", os.getenv("JUNO_TRANSCRIBER_INPUT_TOPIC", "/speech/raw_transcript")
        )
        self.output_topic = rospy.get_param(
            "~output_text_topic", os.getenv("JUNO_TRANSCRIBER_OUTPUT_TOPIC", "/speech/transcript")
        )
        self.audio_topic = rospy.get_param("~audio_topic", "/audio/raw")
        self.normalise_enabled = self._env_bool("JUNO_ROS_LLM_NORMALISE", False)
        self.model_id = os.getenv("JUNO_LLM_MODEL_ID", "mesolitica/Malaysian-Llama-3.2-3B-Instruct")
        self.adapter_id = os.getenv("JUNO_LLM_ADAPTER_ID", "mackwongyy/malaysian-feedback-lora-5k-data")
        self.device_map = os.getenv("JUNO_LLM_DEVICE_MAP", "auto")
        self.torch_dtype = os.getenv("JUNO_LLM_TORCH_DTYPE", "auto")
        self.max_new_tokens = int(os.getenv("JUNO_LLM_NORMALISE_MAX_NEW_TOKENS", "48"))

        self._tokenizer = None
        self._model = None
        self._load_error: Optional[str] = None
        self._audio_warning_sent = False

        self.publisher = rospy.Publisher(self.output_topic, String, queue_size=10)
        self.text_subscriber = rospy.Subscriber(self.input_topic, String, self.text_callback)
        self.audio_subscriber = rospy.Subscriber(self.audio_topic, Float32MultiArray, self.audio_callback)

        rospy.loginfo("JUNO language node ready.")
        rospy.loginfo("Input text topic: %s", self.input_topic)
        rospy.loginfo("Output transcript topic: %s", self.output_topic)
        rospy.loginfo("LLM normalisation enabled in ROS node: %s", self.normalise_enabled)
        if self.normalise_enabled:
            rospy.loginfo("Base model: %s", self.model_id)
            rospy.loginfo("LoRA adapter: %s", self.adapter_id)

    def text_callback(self, msg: String) -> None:
        raw_text = " ".join(str(msg.data).strip().split())
        if not raw_text:
            return

        british_english_text = self.normalise_to_british_english(raw_text)
        rospy.loginfo("Transcript: %s", british_english_text)
        self.publisher.publish(String(data=british_english_text))

    def audio_callback(self, _msg: Float32MultiArray) -> None:
        if self._audio_warning_sent:
            return
        self._audio_warning_sent = True
        rospy.logwarn(
            "Received /audio/raw, but Malaysian Llama is a text model and cannot transcribe audio directly. "
            "Publish candidate ASR text to %s; this node will normalise it to British English and publish %s.",
            self.input_topic,
            self.output_topic,
        )

    def normalise_to_british_english(self, text: str) -> str:
        if not self.normalise_enabled:
            return text
        if not self._ensure_loaded():
            rospy.logwarn("LLM normalisation unavailable; relaying raw transcript.")
            return text

        try:
            import torch

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a language-normalisation layer for a Malaysian student assistant robot. "
                        "Understand Malay, Mandarin, Tamil, Manglish, and common Malaysian dialectal phrasing. "
                        "Convert the utterance into one standard British English sentence for intent classification. "
                        "Preserve meaning, command intent, time expressions, names, and numbers. "
                        "Return only the normalised sentence, with no labels and no explanation. "
                        "For wake or confirmation phrases, return exactly 'Hey, Juno' or 'yes' when appropriate."
                    ),
                },
                {"role": "user", "content": f"User utterance: {text}\nNormalised British English:"},
            ]

            inputs = self._tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
                tokenize=True,
            )
            target_device = getattr(self._model, "device", None)
            if target_device is None:
                try:
                    target_device = next(self._model.parameters()).device
                except StopIteration:
                    target_device = None
            if target_device is not None:
                inputs = inputs.to(target_device)

            with torch.inference_mode():
                output = self._model.generate(
                    input_ids=inputs,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=False,
                    pad_token_id=self._tokenizer.eos_token_id,
                    eos_token_id=self._tokenizer.eos_token_id,
                )
            generated_tokens = output[0][inputs.shape[-1] :]
            generated = self._tokenizer.decode(generated_tokens, skip_special_tokens=True)
            return self._clean(generated) or text
        except Exception as exc:  # pragma: no cover - depends on ROS/model runtime
            rospy.logerr("LLM normalisation failed: %s", exc)
            return text

    def _ensure_loaded(self) -> bool:
        if self._model is not None and self._tokenizer is not None:
            return True
        if self._load_error:
            return False

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from peft import PeftModel

            dtype = self._resolve_torch_dtype(torch)
            kwargs = {"device_map": self.device_map}
            if dtype is not None:
                kwargs["torch_dtype"] = dtype

            rospy.loginfo("Loading Malaysian Llama base model: %s", self.model_id)
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            if self._tokenizer.pad_token_id is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token

            base_model = AutoModelForCausalLM.from_pretrained(self.model_id, **kwargs)
            rospy.loginfo("Loading LoRA adapter: %s", self.adapter_id)
            self._model = PeftModel.from_pretrained(base_model, self.adapter_id)
            self._model.eval()
            return True
        except Exception as exc:  # pragma: no cover - depends on runtime dependencies/model availability
            self._load_error = str(exc)
            rospy.logerr("Could not load Malaysian Llama + LoRA adapter: %s", exc)
            return False

    def _resolve_torch_dtype(self, torch_module):
        value = (self.torch_dtype or "auto").lower().strip()
        if value in {"", "auto"}:
            return "auto"
        if value in {"float16", "fp16", "half"}:
            return torch_module.float16
        if value in {"bfloat16", "bf16"}:
            return torch_module.bfloat16
        if value in {"float32", "fp32"}:
            return torch_module.float32
        rospy.logwarn("Unknown JUNO_LLM_TORCH_DTYPE=%s; using auto", self.torch_dtype)
        return "auto"

    def _clean(self, text: str) -> str:
        cleaned = " ".join(text.strip().split()).strip('"\'` ')
        for prefix in (
            "Normalised British English:",
            "Normalized British English:",
            "British English:",
            "Output:",
        ):
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix) :].strip()
        return cleaned.split("\n", 1)[0].strip('"\'` ')

    @staticmethod
    def _env_bool(name: str, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}

    def run(self) -> None:
        rospy.spin()


if __name__ == "__main__":
    try:
        MalaysianLlamaLanguageNode().run()
    except rospy.ROSInterruptException:
        pass
