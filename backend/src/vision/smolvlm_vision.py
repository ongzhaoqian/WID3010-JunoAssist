"""SmolVLM-backed visual emotion analysis for JUNO Assist.

SmolVLM is a compact image-text-to-text model, not a specialist facial
emotion classifier. This wrapper therefore treats the model as a visual
reasoning component: it asks for structured evidence, parses both JSON and
messy prose, calibrates weak ``neutral`` answers, and exposes confidence and
reasoning details to the dashboard.

The important behaviour for the robot demo is that the model should not silently
fall back to ``neutral`` with an arbitrary confidence when the model output is
unclear. Low-confidence neutral answers are surfaced as ``unknown`` unless there
are clear calm/relaxed cues, while non-neutral visual cues can override a vague
neutral JSON response.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any, Optional

import numpy as np

from src.core.config import settings
from src.core.models import EmotionState
from src.vision.emotion_labels import EKMAN_EMOTIONS

JUNO_EMOTION_LABELS = list(EKMAN_EMOTIONS)


_LABEL_TO_INDEX = {label: idx for idx, label in enumerate(JUNO_EMOTION_LABELS)}
_LABEL_VALUES = {label.value for label in JUNO_EMOTION_LABELS}

DEFAULT_VISION_PROMPT = """
You are JUNO Assist's compact vision-language module. Estimate the user's CURRENT VISIBLE STATE from this webcam frame for supportive human-robot interaction.

Allowed labels only: anger, disgust, fear, happiness, sadness, surprise, neutral, unknown.

Decision rules:
- Use only visible expression/posture cues such as eyes, eyebrows, mouth, facial tension, head angle, posture, and attentiveness.
- Do not infer identity, age, gender, ethnicity, diagnosis, or private traits.
- Do not default to neutral. Use neutral only when the person looks calm, relaxed, or normally attentive.
- If the face is unclear, no person is visible, the image is too dark, or cues conflict strongly, use unknown with low confidence.
- For subtle cues, still choose the most likely non-neutral label when there is evidence: scowl/clenched jaw -> anger; wrinkled nose/dislike -> disgust; wide eyes/worried look -> fear; smile/bright expression -> happiness; droopy eyes/downturned mouth -> sadness; raised eyebrows/open mouth -> surprise.

Return ONLY valid compact JSON with this exact schema:
{"emotion":"fear","confidence":0.62,"scores":{"anger":0.05,"disgust":0.02,"fear":0.55,"happiness":0.03,"sadness":0.12,"surprise":0.05,"neutral":0.18},"visual_cues":["furrowed brow","tense mouth"],"description":"brief reason"}

The scores should sum roughly to 1. Confidence should reflect how clear the visible cues are, not how common the emotion is.
""".strip()


@dataclass
class VisionAnalysis:
    emotion: EmotionState
    confidence: float
    description: str = ""
    raw_output: str = ""
    available: bool = True
    error: Optional[str] = None
    scores: dict[EmotionState, float] = field(default_factory=dict)
    visual_cues: tuple[str, ...] = ()

    def probabilities(self) -> np.ndarray:
        """Convert the analysis result into JUNO-5 probabilities.

        SmolVLM returns text, not logits. If the model produced a score object,
        use that directly after normalisation. Otherwise distribute the stated
        confidence around the selected label.
        """
        if self.scores:
            probs = np.array(
                [max(0.0, float(self.scores.get(label, 0.0))) for label in JUNO_EMOTION_LABELS],
                dtype=np.float32,
            )
            total = float(probs.sum())
            if total > 0:
                return probs / total

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
        max_new_tokens: int = 96,
        prompt: str = DEFAULT_VISION_PROMPT,
    ) -> None:
        self.model_id = model_id
        self.device_preference = device or "auto"
        self.max_new_tokens = int(max_new_tokens or 96)
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
        if preference in {"-1", "cpu"}:
            return "cpu"
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

        quality_problem = self._frame_quality_issue(frame)
        if quality_problem:
            return VisionAnalysis(
                emotion=EmotionState.UNKNOWN,
                confidence=0.0,
                description=quality_problem,
                available=False,
            )

        if not self.load():
            return VisionAnalysis(
                emotion=EmotionState.UNKNOWN,
                confidence=0.0,
                description="SmolVLM vision model is unavailable. Check the optional vision dependencies and model download.",
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

    def _frame_quality_issue(self, frame: Any) -> str | None:
        """Return a reason when the frame is clearly unusable.

        This avoids reporting a fake neutral state when the camera is black,
        disconnected, or returning only metadata-like noise.
        """
        try:
            arr = np.asarray(frame)
            if arr.size == 0:
                return "Camera frame was empty."
            if arr.ndim < 2:
                return "Camera frame had an unsupported shape."
            sample = arr.astype("float32")
            if sample.ndim == 3 and sample.shape[2] >= 3:
                sample = sample[:, :, :3]
            mean = float(sample.mean())
            std = float(sample.std())
            if mean < 4.0:
                return "Camera frame was too dark for reliable emotion estimation."
            if std < 2.0:
                return "Camera frame had too little visual variation for reliable emotion estimation."
        except Exception:
            return None
        return None

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

        # Keep inference lightweight for a robot demo.
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
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                use_cache=True,
            )

        input_len = inputs["input_ids"].shape[-1] if "input_ids" in inputs else 0
        generated = outputs[0][input_len:]
        decoded = self.processor.decode(generated, skip_special_tokens=True)
        return decoded.strip()

    def _parse_output(self, raw_output: str) -> VisionAnalysis:
        text = (raw_output or "").strip()
        if not text:
            return VisionAnalysis(
                emotion=EmotionState.UNKNOWN,
                confidence=0.0,
                description="SmolVLM returned an empty response.",
                raw_output=text,
                available=True,
            )

        payload = self._extract_json_payload(text)
        if payload is not None:
            emotion = _normalise_emotion(
                payload.get("emotion")
                or payload.get("label")
                or payload.get("state")
                or payload.get("visible_state")
            )
            scores = _normalise_scores(
                payload.get("scores")
                or payload.get("probabilities")
                or payload.get("emotion_scores")
            )
            scored_emotion, scored_confidence = _best_scored_emotion(scores)
            if emotion == EmotionState.UNKNOWN and scored_emotion is not None:
                emotion = scored_emotion

            confidence = _normalise_confidence(
                payload.get("confidence") or payload.get("score") or payload.get("probability"),
                default=scored_confidence if scored_confidence is not None else 0.0,
            )
            cues = _normalise_cues(payload.get("visual_cues") or payload.get("cues") or payload.get("evidence"))
            description = str(
                payload.get("description")
                or payload.get("reason")
                or payload.get("rationale")
                or ", ".join(cues)
                or ""
            ).strip()
            return self._calibrate_analysis(
                VisionAnalysis(
                    emotion=emotion,
                    confidence=confidence,
                    description=description,
                    raw_output=text,
                    scores=scores,
                    visual_cues=tuple(cues),
                )
            )

        # Fallback parser if the model returns prose instead of JSON.
        lowered = text.lower()
        emotion = EmotionState.UNKNOWN
        for label in ["anger", "angry", "disgust", "disgusted", "fear", "fearful", "happiness", "happy", "sadness", "sad", "surprise", "surprised", "neutral", "unknown", "frustrated", "stressed", "tired"]:
            if re.search(rf"\b{label}\b", lowered):
                emotion = _normalise_emotion(label)
                break

        conf_match = re.search(r"(?:confidence|score|probability)\D*(0?\.\d+|1(?:\.0+)?|\d{1,3})\s*%?", lowered)
        confidence = _normalise_confidence(conf_match.group(1), default=0.0) if conf_match else 0.0
        description = text[:220]
        return self._calibrate_analysis(
            VisionAnalysis(
                emotion=emotion,
                confidence=confidence,
                description=description,
                raw_output=text,
            )
        )

    def _extract_json_payload(self, text: str) -> dict[str, Any] | None:
        # Prefer the first valid JSON object, because VLMs sometimes wrap it in prose.
        # Use raw_decode instead of a naive regex so nested objects such as
        # {"scores": {"happy": 0.1, ...}} are handled correctly.
        decoder = json.JSONDecoder()
        for match in re.finditer(r"\{", text):
            try:
                payload, _ = decoder.raw_decode(text[match.start():])
            except Exception:
                continue
            if isinstance(payload, dict):
                return payload
        return None

    def _calibrate_analysis(self, analysis: VisionAnalysis) -> VisionAnalysis:
        """Avoid unhelpful ``neutral, 40%`` outputs and recover from vague prose."""
        context = " ".join(
            part for part in [analysis.raw_output, analysis.description, " ".join(analysis.visual_cues)] if part
        )
        cue_emotion, cue_confidence, cue_reason = _infer_from_visual_cues(context)

        if cue_emotion and cue_emotion != EmotionState.NEUTRAL:
            if analysis.emotion in {EmotionState.UNKNOWN, EmotionState.NEUTRAL} or (cue_emotion != analysis.emotion and cue_confidence > analysis.confidence + 0.10):
                return VisionAnalysis(
                    emotion=cue_emotion,
                    confidence=max(analysis.confidence, cue_confidence),
                    description=analysis.description or cue_reason,
                    raw_output=analysis.raw_output,
                    scores=analysis.scores,
                    visual_cues=analysis.visual_cues,
                )

        # Do not show a low-confidence neutral answer as if it were a real emotion.
        if analysis.emotion == EmotionState.NEUTRAL and analysis.confidence <= settings.vision_neutral_uncertain_confidence:
            if not _has_clear_neutral_cue(context):
                return VisionAnalysis(
                    emotion=EmotionState.UNKNOWN,
                    confidence=min(analysis.confidence, 0.25),
                    description=analysis.description or "Visual cues were too weak to classify confidently.",
                    raw_output=analysis.raw_output,
                    scores=analysis.scores,
                    visual_cues=analysis.visual_cues,
                )

        if analysis.emotion == EmotionState.UNKNOWN and cue_emotion:
            return VisionAnalysis(
                emotion=cue_emotion,
                confidence=max(analysis.confidence, cue_confidence),
                description=analysis.description or cue_reason,
                raw_output=analysis.raw_output,
                scores=analysis.scores,
                visual_cues=analysis.visual_cues,
            )

        return analysis


def _normalise_emotion(value: Any) -> EmotionState:
    label = str(value or "unknown").strip().lower()
    label = re.sub(r"[^a-z]", "", label)
    aliases = {
        "happy": EmotionState.HAPPINESS,
        "happiness": EmotionState.HAPPINESS,
        "joy": EmotionState.HAPPINESS,
        "joyful": EmotionState.HAPPINESS,
        "anger": EmotionState.ANGER,
        "angry": EmotionState.ANGER,
        "frustrated": EmotionState.ANGER,
        "disgust": EmotionState.DISGUST,
        "disgusted": EmotionState.DISGUST,
        "fear": EmotionState.FEAR,
        "fearful": EmotionState.FEAR,
        "stressed": EmotionState.FEAR,
        "sad": EmotionState.SADNESS,
        "sadness": EmotionState.SADNESS,
        "surprise": EmotionState.SURPRISE,
        "surprised": EmotionState.SURPRISE,
        "calm": EmotionState.NEUTRAL,
        "focused": EmotionState.NEUTRAL,
        "relaxed": EmotionState.NEUTRAL,
        "attentive": EmotionState.NEUTRAL,
        "normal": EmotionState.NEUTRAL,
        "sleepy": EmotionState.SADNESS,
        "fatigued": EmotionState.SADNESS,
        "exhausted": EmotionState.SADNESS,
        "drained": EmotionState.SADNESS,
        "anxious": EmotionState.FEAR,
        "stress": EmotionState.FEAR,
        "worried": EmotionState.FEAR,
        "tense": EmotionState.FEAR,
        "mad": EmotionState.ANGER,
        "annoyed": EmotionState.ANGER,
        "irritated": EmotionState.ANGER,
        "confused": EmotionState.SURPRISE,
        "smiling": EmotionState.HAPPINESS,
    }
    if label in aliases:
        return aliases[label]
    for state in EmotionState:
        if state.value == label:
            return state
    return EmotionState.UNKNOWN


def _normalise_confidence(value: Any, default: float = 0.0) -> float:
    try:
        if isinstance(value, str):
            cleaned = value.strip().replace("%", "")
            confidence = float(cleaned)
        else:
            confidence = float(value)
    except Exception:
        return default
    if confidence > 1.0:
        confidence /= 100.0
    return min(max(confidence, 0.0), 1.0)


def _normalise_scores(value: Any) -> dict[EmotionState, float]:
    if not isinstance(value, dict):
        return {}
    scores: dict[EmotionState, float] = {}
    for key, raw_score in value.items():
        emotion = _normalise_emotion(key)
        if emotion not in _LABEL_TO_INDEX:
            continue
        scores[emotion] = max(scores.get(emotion, 0.0), _normalise_confidence(raw_score, default=0.0))
    total = sum(scores.values())
    if total > 0:
        scores = {emotion: score / total for emotion, score in scores.items()}
    return scores


def _best_scored_emotion(scores: dict[EmotionState, float]) -> tuple[EmotionState | None, float | None]:
    if not scores:
        return None, None
    emotion, score = max(scores.items(), key=lambda item: item[1])
    return emotion, float(score)


def _normalise_cues(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


_CUE_KEYWORDS: dict[EmotionState, tuple[tuple[str, float], ...]] = {
    EmotionState.HAPPINESS: (
        ("smile", 0.32), ("smiling", 0.36), ("cheerful", 0.28), ("bright expression", 0.25),
        ("laugh", 0.25), ("upturned mouth", 0.25),
    ),
    EmotionState.SADNESS: (
        ("tired", 0.35), ("sleepy", 0.35), ("droopy", 0.28), ("drooping", 0.28),
        ("yawn", 0.36), ("eyes closed", 0.30), ("half closed eyes", 0.28),
        ("slumped", 0.25), ("head down", 0.22), ("low energy", 0.25), ("fatigued", 0.35),
        ("exhausted", 0.35),
    ),
    EmotionState.FEAR: (
        ("fear", 0.34), ("fearful", 0.34), ("stressed", 0.30), ("stress", 0.25), ("tense", 0.28), ("tension", 0.28),
        ("furrowed", 0.30), ("furrowed brow", 0.36), ("worried", 0.32), ("anxious", 0.34),
        ("strained", 0.30), ("wide eyes", 0.20), ("pressed lips", 0.22), ("brow tension", 0.30),
    ),
    EmotionState.ANGER: (
        ("anger", 0.38), ("angry", 0.35), ("frustrated", 0.34), ("annoyed", 0.34), ("irritated", 0.34),
        ("scowl", 0.32), ("scowling", 0.32), ("clenched jaw", 0.30), ("grimace", 0.30),
        ("frown", 0.25), ("pursed lips", 0.24),
    ),
    EmotionState.DISGUST: (
        ("disgust", 0.36), ("disgusted", 0.36), ("wrinkled nose", 0.30),
        ("nose wrinkle", 0.30), ("grimace", 0.22), ("repulsed", 0.32),
    ),
    EmotionState.SURPRISE: (
        ("surprise", 0.36), ("surprised", 0.36), ("raised eyebrows", 0.30),
        ("wide eyes", 0.28), ("open mouth", 0.26), ("startled", 0.30),
    ),
    EmotionState.NEUTRAL: (
        ("neutral", 0.20), ("calm", 0.30), ("relaxed", 0.32), ("attentive", 0.25),
        ("normal", 0.18), ("no strong emotion", 0.22),
    ),
}


def _infer_from_visual_cues(text: str) -> tuple[EmotionState | None, float, str]:
    lowered = (text or "").lower()
    if not lowered:
        return None, 0.0, ""
    scores: dict[EmotionState, float] = {emotion: 0.0 for emotion in _CUE_KEYWORDS}
    matched: dict[EmotionState, list[str]] = {emotion: [] for emotion in _CUE_KEYWORDS}
    for emotion, cues in _CUE_KEYWORDS.items():
        for phrase, weight in cues:
            if phrase in lowered:
                scores[emotion] += weight
                matched[emotion].append(phrase)
    # Prefer non-neutral evidence when it is close to neutral evidence.
    non_neutral = {emotion: score for emotion, score in scores.items() if emotion != EmotionState.NEUTRAL}
    best_emotion, best_score = max(non_neutral.items(), key=lambda item: item[1])
    if best_score <= 0:
        neutral_score = scores[EmotionState.NEUTRAL]
        if neutral_score > 0:
            return EmotionState.NEUTRAL, min(0.72, 0.45 + neutral_score), "clear calm/neutral cue"
        return None, 0.0, ""
    confidence = min(0.85, 0.45 + best_score)
    return best_emotion, confidence, f"visual cue match: {', '.join(matched[best_emotion][:3])}"


def _has_clear_neutral_cue(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in ("calm", "relaxed", "attentive", "normal expression", "no strong emotion"))
