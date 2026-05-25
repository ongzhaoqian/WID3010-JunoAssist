"""SmolVLM-backed vision analysis for JUNO Assist.

This module keeps Hugging Face/torch imports lazy so the normal backend and
unit tests can still run without installing the heavier vision dependencies.
When the Vision Module is enabled and a camera frame is available, the model is
loaded on first use and asked to classify the user's visible state into JUNO's
five emotion labels.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Optional

import numpy as np

from src.core.models import EmotionState

JUNO_EMOTION_LABELS = [
    EmotionState.HAPPY,
    EmotionState.NEUTRAL,
    EmotionState.TIRED,
    EmotionState.STRESSED,
    EmotionState.FRUSTRATED,
]

_LABEL_TO_INDEX = {label: idx for idx, label in enumerate(JUNO_EMOTION_LABELS)}

DEFAULT_VISION_PROMPT = """
You are the compact vision-language model inside JUNO Assist, a student daily-assistant robot.
Analyse the webcam frame and estimate the user's visible state for supportive interaction.

Choose exactly one emotion label from:
happy, neutral, tired, stressed, frustrated, unknown.

Use visible cues such as facial expression, eye openness, posture, attentiveness, and obvious signs of strain.
Do not infer sensitive traits, identity, age, gender, ethnicity, health diagnosis, or private attributes.
If the frame is unclear, no person is visible, or emotion is ambiguous, choose neutral or unknown with low confidence.

Return only valid JSON in this exact shape:
{"emotion":"neutral","confidence":0.55,"description":"brief visual reason"}
""".strip()


@dataclass
class VisionAnalysis:
    emotion: EmotionState
    confidence: float
    description: str = ""
    raw_output: str = ""
    available: bool = True
    error: Optional[str] = None

    def probabilities(self) -> np.ndarray:
        """Convert the analysis result into JUNO-5 probabilities.

        The old emotion pipeline expects a five-class probability vector ordered
        as [happy, neutral, tired, stressed, frustrated]. SmolVLM returns text,
        so we convert the chosen label and confidence into a soft distribution.
        """
        probs = np.full(len(JUNO_EMOTION_LABELS), 0.0, dtype=np.float32)
        if self.emotion not in _LABEL_TO_INDEX:
            probs[_LABEL_TO_INDEX[EmotionState.NEUTRAL]] = 1.0
            return probs

        confidence = min(max(float(self.confidence), 0.05), 0.95)
        if len(JUNO_EMOTION_LABELS) > 1:
            remainder = (1.0 - confidence) / (len(JUNO_EMOTION_LABELS) - 1)
            probs.fill(remainder)
        probs[_LABEL_TO_INDEX[self.emotion]] = confidence
        total = float(probs.sum())
        if total > 0:
            probs /= total
        return probs


class SmolVLMVisionModel:
    """Lazy wrapper around HuggingFaceTB/SmolVLM-256M-Instruct."""

    def __init__(
        self,
        model_id: str = "HuggingFaceTB/SmolVLM-256M-Instruct",
        device: str = "auto",
        max_new_tokens: int = 64,
        prompt: str = DEFAULT_VISION_PROMPT,
    ) -> None:
        self.model_id = model_id
        self.device_preference = device or "auto"
        self.max_new_tokens = int(max_new_tokens or 64)
        self.prompt = prompt or DEFAULT_VISION_PROMPT
        self.processor = None
        self.model = None
        self.torch = None
        self.device = "cpu"
        self.load_error: Optional[str] = None

    @property
    def loaded(self) -> bool:
        return self.processor is not None and self.model is not None

    def _select_device(self) -> str:
        preference = (self.device_preference or "auto").strip().lower()
        if preference not in {"", "auto"}:
            return preference

        torch = self.torch
        if torch is not None and torch.cuda.is_available():
            return "cuda"
        if torch is not None and getattr(torch.backends, "mps", None) is not None:
            try:
                if torch.backends.mps.is_available():
                    return "mps"
            except Exception:
                pass
        return "cpu"

    def load(self) -> bool:
        if self.loaded:
            return True
        try:
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor

            self.torch = torch
            self.device = self._select_device()
            dtype = torch.float16 if self.device == "cuda" else torch.float32

            self.processor = AutoProcessor.from_pretrained(self.model_id)
            try:
                self.model = AutoModelForImageTextToText.from_pretrained(
                    self.model_id,
                    torch_dtype=dtype,
                    low_cpu_mem_usage=True,
                )
            except TypeError:
                # Older/newer Transformers builds may not accept all kwargs.
                self.model = AutoModelForImageTextToText.from_pretrained(self.model_id)

            self.model.to(self.device)
            self.model.eval()
            self.load_error = None
            return True
        except Exception as exc:  # pragma: no cover - depends on optional local deps
            self.load_error = f"{type(exc).__name__}: {exc}"
            self.processor = None
            self.model = None
            return False

    def analyse(self, frame: Any) -> VisionAnalysis:
        if frame is None:
            return VisionAnalysis(
                emotion=EmotionState.UNKNOWN,
                confidence=0.0,
                description="No camera frame was available for SmolVLM analysis.",
                available=False,
            )

        if not self.load():
            return VisionAnalysis(
                emotion=EmotionState.UNKNOWN,
                confidence=0.0,
                description="SmolVLM vision model is unavailable.",
                available=False,
                error=self.load_error,
            )

        try:
            image = self._frame_to_pil(frame)
            raw_output = self._generate(image)
            return self._parse_output(raw_output)
        except Exception as exc:  # pragma: no cover - model/runtime dependent
            return VisionAnalysis(
                emotion=EmotionState.UNKNOWN,
                confidence=0.0,
                description="SmolVLM analysis failed for the current frame.",
                raw_output="",
                available=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    def _frame_to_pil(self, frame: Any):
        from PIL import Image

        if isinstance(frame, Image.Image):
            image = frame.convert("RGB")
        else:
            arr = np.asarray(frame)
            if arr.ndim == 2:
                image = Image.fromarray(arr).convert("RGB")
            elif arr.ndim == 3 and arr.shape[2] >= 3:
                # Camera frames from OpenCV/ROS are normally BGR. Convert to RGB.
                rgb = arr[:, :, :3][:, :, ::-1]
                image = Image.fromarray(rgb.astype("uint8")).convert("RGB")
            else:
                raise ValueError(f"Unsupported frame shape for SmolVLM: {arr.shape}")

        # Keep inference lightweight for a robot demo. SmolVLM supports larger
        # images, but a 768px long side is enough for emotion-state prompting.
        max_side = 768
        w, h = image.size
        if max(w, h) > max_side:
            scale = max_side / float(max(w, h))
            image = image.resize((max(1, int(w * scale)), max(1, int(h * scale))))
        return image

    def _generate(self, image) -> str:
        assert self.processor is not None
        assert self.model is not None
        assert self.torch is not None

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": self.prompt},
                ],
            }
        ]

        try:
            inputs = self.processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            )
        except Exception:
            # Compatibility fallback for processor builds that expect images
            # outside the chat template.
            text_prompt = self.processor.apply_chat_template(
                [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": self.prompt}]}],
                add_generation_prompt=True,
                tokenize=False,
            )
            inputs = self.processor(text=text_prompt, images=[image], return_tensors="pt")

        inputs = {
            key: value.to(self.device) if hasattr(value, "to") else value
            for key, value in inputs.items()
        }

        with self.torch.inference_mode():
            outputs = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens, do_sample=False)

        input_len = inputs["input_ids"].shape[-1] if "input_ids" in inputs else 0
        generated = outputs[0][input_len:]
        decoded = self.processor.decode(generated, skip_special_tokens=True)
        return decoded.strip()

    def _parse_output(self, raw_output: str) -> VisionAnalysis:
        text = (raw_output or "").strip()
        emotion = EmotionState.UNKNOWN
        confidence = 0.40
        description = ""

        json_match = re.search(r"\{.*?\}", text, flags=re.DOTALL)
        if json_match:
            try:
                payload = json.loads(json_match.group(0))
                emotion = _normalise_emotion(payload.get("emotion"))
                confidence = _normalise_confidence(payload.get("confidence"), default=confidence)
                description = str(payload.get("description") or "").strip()
                return VisionAnalysis(emotion=emotion, confidence=confidence, description=description, raw_output=text)
            except Exception:
                pass

        # Fallback parser if the model returns prose instead of JSON.
        lowered = text.lower()
        for label in ["frustrated", "stressed", "tired", "happy", "neutral", "unknown"]:
            if re.search(rf"\b{label}\b", lowered):
                emotion = _normalise_emotion(label)
                break

        conf_match = re.search(r"(?:confidence|score)\D*(0?\.\d+|1(?:\.0+)?|\d{1,3})", lowered)
        if conf_match:
            confidence = _normalise_confidence(conf_match.group(1), default=confidence)

        description = text[:180]
        return VisionAnalysis(emotion=emotion, confidence=confidence, description=description, raw_output=text)


def _normalise_emotion(value: Any) -> EmotionState:
    label = str(value or "unknown").strip().lower()
    label = re.sub(r"[^a-z]", "", label)
    aliases = {
        "calm": EmotionState.NEUTRAL,
        "focused": EmotionState.NEUTRAL,
        "normal": EmotionState.NEUTRAL,
        "sleepy": EmotionState.TIRED,
        "fatigued": EmotionState.TIRED,
        "exhausted": EmotionState.TIRED,
        "anxious": EmotionState.STRESSED,
        "stress": EmotionState.STRESSED,
        "angry": EmotionState.FRUSTRATED,
        "annoyed": EmotionState.FRUSTRATED,
        "confused": EmotionState.FRUSTRATED,
    }
    if label in aliases:
        return aliases[label]
    for state in EmotionState:
        if state.value == label:
            return state
    return EmotionState.UNKNOWN


def _normalise_confidence(value: Any, default: float = 0.40) -> float:
    try:
        confidence = float(value)
    except Exception:
        return default
    if confidence > 1.0:
        confidence /= 100.0
    return min(max(confidence, 0.0), 1.0)
