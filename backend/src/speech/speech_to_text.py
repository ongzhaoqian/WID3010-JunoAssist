from __future__ import annotations

from typing import Any, Optional

from src.core.config import settings


class SpeechToText:
    """Optional local Whisper Tiny speech-to-text service.

    The normal robot path uses the ROS transcriber node and sends recognised
    text to the backend through ``/speech/transcript``. This class is kept as a
    backend-side utility for non-ROS tests or future direct audio uploads. It is
    lazy-loaded so the backend can still start without PyTorch/Transformers.
    """

    def __init__(
        self,
        model_id: str = settings.asr_model_id,
        sample_rate: int = settings.asr_sample_rate,
        task: str = settings.asr_task,
        language: str = settings.asr_language,
        device: str = settings.asr_device,
    ) -> None:
        self.model_id = model_id
        self.sample_rate = sample_rate
        self.task = task
        self.language = language or ""
        self.device = self._parse_device(device)
        self._pipeline: Optional[Any] = None
        self._load_error: Optional[str] = None

    def transcribe(self, audio_input=None) -> str:
        if isinstance(audio_input, str):
            return " ".join(audio_input.strip().split())
        if audio_input is None:
            return ""
        if not self._ensure_loaded():
            return ""

        payload = audio_input
        # Numpy arrays/lists are passed with the expected sample rate. File paths
        # can still be passed directly to the Transformers pipeline.
        if not isinstance(audio_input, (str, bytes)):
            payload = {"array": audio_input, "sampling_rate": self.sample_rate}

        generate_kwargs: dict[str, str] = {}
        if self.task in {"translate", "transcribe"}:
            generate_kwargs["task"] = self.task
        if self.language:
            generate_kwargs["language"] = self.language

        try:
            if generate_kwargs:
                result = self._pipeline(payload, generate_kwargs=generate_kwargs)
            else:
                result = self._pipeline(payload)
        except TypeError:
            result = self._pipeline(payload)
        except Exception:
            return ""

        if isinstance(result, dict):
            return " ".join(str(result.get("text", "")).strip().split())
        return " ".join(str(result).strip().split())

    def status(self) -> dict:
        return {
            "enabled": settings.asr_enabled,
            "model_id": self.model_id,
            "task": self.task,
            "language": self.language or None,
            "sample_rate": self.sample_rate,
            "device": self.device,
            "loaded": self._pipeline is not None,
            "load_error": self._load_error,
            "output_topic": "/speech/transcript",
        }

    def _ensure_loaded(self) -> bool:
        if not settings.asr_enabled:
            return False
        if self._pipeline is not None:
            return True
        if self._load_error is not None:
            return False
        try:
            from transformers import pipeline

            self._pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model_id,
                device=self.device,
            )
            return True
        except Exception as exc:  # pragma: no cover - optional dependency/model dependent
            self._load_error = str(exc)
            return False

    @staticmethod
    def _parse_device(value: str):
        value = str(value or "-1").strip()
        try:
            return int(value)
        except ValueError:
            return value
