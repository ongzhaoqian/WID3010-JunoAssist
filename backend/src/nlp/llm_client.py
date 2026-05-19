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

    The model stays behind the NLP boundary. It receives only text/context and
    returns a response string; it does not access ROS topics, robot hardware,
    timers, or database writes directly.
    """

    user_text: str
    intent: Intent
    emotion: EmotionState
    schedule_summary: str = ""


class MalaysianLlamaClient:
    """Optional lazy Hugging Face text-generation client.

    The robot-friendly default path now uses Whisper Tiny for speech-to-text and
    deterministic backend logic for intents/responses. This client is retained
    only as an optional future text LLM boundary. It will not load anything
    unless JUNO_LLM_ENABLED=true and JUNO_LLM_MODEL_ID is configured.
    """

    def __init__(
        self,
        model_id: str = settings.llm_model_id,
        adapter_id: str = settings.llm_adapter_id,
        enabled: bool = settings.llm_enabled,
        max_new_tokens: int = settings.llm_max_new_tokens,
        normalise_max_new_tokens: int = settings.llm_normalise_max_new_tokens,
        temperature: float = settings.llm_temperature,
        top_p: float = settings.llm_top_p,
        device_map: str = settings.llm_device_map,
        torch_dtype: str = settings.llm_torch_dtype,
    ) -> None:
        self.model_id = model_id
        self.adapter_id = adapter_id
        self.enabled = enabled
        self.max_new_tokens = max_new_tokens
        self.normalise_max_new_tokens = normalise_max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.device_map = device_map
        self.torch_dtype = torch_dtype
        self._tokenizer = None
        self._model = None
        self._adapter_loaded = False
        self._load_error: Optional[str] = None

    @property
    def is_available(self) -> bool:
        return self.enabled and self._load_error is None

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "model_id": self.model_id,
            "adapter_id": self.adapter_id,
            "loaded": self._model is not None and self._tokenizer is not None,
            "adapter_loaded": self._adapter_loaded,
            "load_error": self._load_error,
            "max_new_tokens": self.max_new_tokens,
            "normalise_max_new_tokens": self.normalise_max_new_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "device_map": self.device_map,
            "torch_dtype": self.torch_dtype,
            "output_policy": "standard British English",
            "role": "optional_text_generation",
        }

    def generate(self, context: LLMGenerationContext) -> Optional[str]:
        """Generate a concise assistant reply, returning None on fallback."""

        if not self.enabled or not self._ensure_loaded():
            return None

        messages = self._build_response_messages(context)
        text = self._generate_from_messages(
            messages=messages,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
        )
        return self._clean_response(text) if text else None

    def normalise_to_british_english(self, text: str) -> Optional[str]:
        """Translate/normalise Malaysian-context input into British English.

        This is used before intent classification so commands in Malay,
        Mandarin, Tamil, Manglish, or common Malaysian dialectal phrasing can be
        mapped to the existing deterministic backend intents where possible.
        """

        original = " ".join(text.strip().split())
        if not original or not self.enabled or not self._ensure_loaded():
            return None

        messages = self._build_normalisation_messages(original)
        generated = self._generate_from_messages(
            messages=messages,
            max_new_tokens=self.normalise_max_new_tokens,
            temperature=0.0,
            top_p=1.0,
        )
        cleaned = self._clean_normalised_text(generated)
        return cleaned or None

    def _ensure_loaded(self) -> bool:
        if self._model is not None and self._tokenizer is not None:
            return True

        if self._load_error is not None:
            return False

        if not self.model_id:
            self._load_error = "No JUNO_LLM_MODEL_ID configured; using deterministic backend responses."
            logger.info(self._load_error)
            return False

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            dtype = self._resolve_torch_dtype(torch)
            model_kwargs = {"device_map": self.device_map}
            if dtype is not None:
                model_kwargs["torch_dtype"] = dtype

            logger.info("Loading optional Hugging Face text model: %s", self.model_id)
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            if self._tokenizer.pad_token_id is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token

            base_model = AutoModelForCausalLM.from_pretrained(self.model_id, **model_kwargs)

            if self.adapter_id:
                try:
                    from peft import PeftModel

                    logger.info("Loading optional LoRA adapter: %s", self.adapter_id)
                    self._model = PeftModel.from_pretrained(base_model, self.adapter_id)
                    self._adapter_loaded = True
                except Exception as adapter_exc:  # pragma: no cover - optional runtime dependency/model dependent
                    self._load_error = (
                        f"Text model loaded but LoRA adapter failed to load: {adapter_exc}"
                    )
                    logger.warning(self._load_error)
                    return False
            else:
                self._model = base_model

            self._model.eval()
            return True
        except Exception as exc:  # pragma: no cover - optional dependency/model dependent
            self._load_error = str(exc)
            logger.warning("Could not load optional text model: %s", exc)
            return False

    def _generate_from_messages(
        self,
        messages: list[dict[str, str]],
        max_new_tokens: int,
        temperature: float,
        top_p: float,
    ) -> Optional[str]:
        try:
            import torch

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

            generation_kwargs = {
                "input_ids": inputs,
                "max_new_tokens": max_new_tokens,
                "do_sample": temperature > 0,
                "temperature": temperature if temperature > 0 else None,
                "top_p": top_p,
                "pad_token_id": self._tokenizer.eos_token_id,
                "eos_token_id": self._tokenizer.eos_token_id,
            }
            generation_kwargs = {k: v for k, v in generation_kwargs.items() if v is not None}

            with torch.inference_mode():
                outputs = self._model.generate(**generation_kwargs)

            generated_tokens = outputs[0][inputs.shape[-1] :]
            return self._tokenizer.decode(generated_tokens, skip_special_tokens=True)
        except Exception as exc:  # pragma: no cover - model runtime dependent
            logger.warning("Optional text-model generation failed: %s", exc)
            return None

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

    def _build_response_messages(self, context: LLMGenerationContext) -> list[dict[str, str]]:
        system_prompt = (
            "You are JUNO Assist, a friendly personal daily assistant robot for university students in Malaysia. "
            "You can understand Malaysian-context input, including Malay, Mandarin, Tamil, Manglish, and common Malaysian dialectal phrasing. "
            "Always reply in standard British English only, using UK spelling and clear spoken phrasing. "
            "Do not reply in Malay, Mandarin, Tamil, dialect, or mixed language unless the user explicitly asks for a translation example. "
            "Keep replies under three sentences. Do not claim to perform robot actions, set timers, add reminders, "
            "or access schedules unless the backend context says it has already happened. "
            "For wellbeing, give gentle productivity support only and do not diagnose mental health conditions."
        )

        user_prompt = (
            f"Original user message: {context.user_text}\n"
            f"Detected intent: {context.intent.value}\n"
            f"Visible emotion estimate: {context.emotion.value}\n"
            f"Schedule context: {context.schedule_summary or 'No additional schedule context.'}\n\n"
            "Write JUNO's spoken response in standard British English."
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _build_normalisation_messages(self, text: str) -> list[dict[str, str]]:
        system_prompt = (
            "You are a language-normalisation layer for a Malaysian student assistant robot. "
            "Understand Malay, Mandarin, Tamil, Manglish, and common Malaysian dialectal phrasing. "
            "Convert the user utterance into one standard British English sentence for intent classification. "
            "Preserve the meaning, command intent, time expressions, names, and numbers. "
            "Return only the normalised sentence, with no quotation marks, no labels, and no explanation. "
            "For wake or confirmation phrases, return exactly 'Hey, Juno' or 'yes' when appropriate."
        )
        user_prompt = f"User utterance: {text}\nNormalised British English:"
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _clean_response(self, text: Optional[str]) -> str:
        if not text:
            return ""
        cleaned = " ".join(text.strip().split())
        if not cleaned:
            return ""

        words = cleaned.split()
        if len(words) > settings.llm_max_response_words:
            cleaned = " ".join(words[: settings.llm_max_response_words]).rstrip(" ,;:") + "."
        return cleaned

    def _clean_normalised_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        cleaned = " ".join(text.strip().split())
        cleaned = cleaned.strip('"\'` ')
        prefixes = [
            "Normalised British English:",
            "Normalized British English:",
            "British English:",
            "Output:",
        ]
        for prefix in prefixes:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix) :].strip()
        # Keep the intent classifier input compact and prevent generated commentary.
        first_line = cleaned.split("\n", 1)[0].strip()
        return first_line.strip('"\'` ')
