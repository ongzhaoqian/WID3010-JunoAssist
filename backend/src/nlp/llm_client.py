from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from src.core.config import settings
from src.core.models import EmotionState, Intent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMGenerationContext:
    """Context passed from the command pipeline into the language model.

    The model is intentionally kept behind the NLP boundary. It receives only
    text/context and returns a response string; it does not access ROS topics,
    robot hardware, timers, or database writes directly.
    """

    user_text: str
    intent: Intent
    emotion: EmotionState
    schedule_summary: str = ""


class MalaysianLlamaClient:
    """Lazy Hugging Face client for Mesolitica Malaysian Llama.

    The model is loaded only when a response is requested and LLM use is enabled.
    This keeps the FastAPI backend and ROS bridge lightweight during normal robot
    startup, while still allowing the assistant to use the Hugging Face model for
    open-ended student-support replies.
    """

    def __init__(
        self,
        model_id: str = settings.llm_model_id,
        enabled: bool = settings.llm_enabled,
        max_new_tokens: int = settings.llm_max_new_tokens,
        temperature: float = settings.llm_temperature,
        top_p: float = settings.llm_top_p,
        device_map: str = settings.llm_device_map,
        torch_dtype: str = settings.llm_torch_dtype,
    ) -> None:
        self.model_id = model_id
        self.enabled = enabled
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.device_map = device_map
        self.torch_dtype = torch_dtype
        self._tokenizer = None
        self._model = None
        self._load_error: Optional[str] = None

    @property
    def is_available(self) -> bool:
        return self.enabled and self._load_error is None

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "model_id": self.model_id,
            "loaded": self._model is not None and self._tokenizer is not None,
            "load_error": self._load_error,
            "max_new_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "device_map": self.device_map,
            "torch_dtype": self.torch_dtype,
        }

    def generate(self, context: LLMGenerationContext) -> Optional[str]:
        """Generate a concise assistant reply, returning None on fallback.

        Returning None lets the existing deterministic ResponseGenerator keep the
        robot demo reliable if the model is disabled, unavailable, or too heavy
        for the current machine.
        """

        if not self.enabled:
            return None

        if not self._ensure_loaded():
            return None

        messages = self._build_messages(context)

        try:
            import torch

            inputs = self._tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
                tokenize=True,
            )

            # With device_map="auto", Accelerate may shard the model. For a
            # single-device load, moving inputs to model.device is sufficient.
            model_device = getattr(self._model, "device", None)
            if model_device is not None:
                inputs = inputs.to(model_device)

            generation_kwargs = {
                "input_ids": inputs,
                "max_new_tokens": self.max_new_tokens,
                "do_sample": self.temperature > 0,
                "temperature": self.temperature if self.temperature > 0 else None,
                "top_p": self.top_p,
                "pad_token_id": self._tokenizer.eos_token_id,
                "eos_token_id": self._tokenizer.eos_token_id,
            }
            generation_kwargs = {k: v for k, v in generation_kwargs.items() if v is not None}

            with torch.inference_mode():
                outputs = self._model.generate(**generation_kwargs)

            generated_tokens = outputs[0][inputs.shape[-1] :]
            text = self._tokenizer.decode(generated_tokens, skip_special_tokens=True)
            return self._clean_response(text)
        except Exception as exc:  # pragma: no cover - model runtime dependent
            logger.warning("Malaysian Llama generation failed: %s", exc)
            return None

    def _ensure_loaded(self) -> bool:
        if self._model is not None and self._tokenizer is not None:
            return True

        if self._load_error is not None:
            return False

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            dtype = self._resolve_torch_dtype(torch)
            model_kwargs = {
                "device_map": self.device_map,
            }
            if dtype is not None:
                model_kwargs["torch_dtype"] = dtype

            logger.info("Loading Hugging Face model: %s", self.model_id)
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self._model = AutoModelForCausalLM.from_pretrained(self.model_id, **model_kwargs)
            self._model.eval()
            return True
        except Exception as exc:  # pragma: no cover - optional dependency/model dependent
            self._load_error = str(exc)
            logger.warning("Could not load Malaysian Llama model: %s", exc)
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
        logger.warning("Unknown JUNO_LLM_TORCH_DTYPE=%s; using auto", self.torch_dtype)
        return "auto"

    def _build_messages(self, context: LLMGenerationContext) -> list[dict[str, str]]:
        system_prompt = (
            "You are JUNO Assist, a friendly personal daily assistant robot for university students in Malaysia. "
            "Reply in clear, concise UK English unless the user uses Malay, Mandarin, Tamil, or Malaysian English. "
            "Keep replies under three sentences. Do not claim to perform robot actions, set timers, add reminders, "
            "or access schedules unless the backend context says it has already happened. "
            "For wellbeing, give gentle productivity support only and do not diagnose mental health conditions."
        )

        user_prompt = (
            f"User message: {context.user_text}\n"
            f"Detected intent: {context.intent.value}\n"
            f"Visible emotion estimate: {context.emotion.value}\n"
            f"Schedule context: {context.schedule_summary or 'No additional schedule context.'}\n\n"
            "Write JUNO's spoken response."
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _clean_response(self, text: str) -> str:
        cleaned = " ".join(text.strip().split())
        if not cleaned:
            return ""

        # Prevent unusually long generations from reaching the TTS node.
        words = cleaned.split()
        if len(words) > settings.llm_max_response_words:
            cleaned = " ".join(words[: settings.llm_max_response_words]).rstrip(" ,;:") + "."
        return cleaned
