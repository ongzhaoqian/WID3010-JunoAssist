from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from src.core.config import settings
from src.core.models import EmotionState
from src.vision.emotion_labels import EKMAN_EMOTIONS, LABEL_TO_INDEX, normalise_distribution, normalise_emotion_label, one_hot


@dataclass
class FacialEmotionAnalysis:
    emotion: EmotionState
    confidence: float
    description: str = ""
    raw_output: str = ""
    available: bool = True
    error: Optional[str] = None
    scores: dict[EmotionState, float] = field(default_factory=dict)
    face_confidence: float = 0.0
    used_face_crop: bool = False

    def probabilities(self) -> np.ndarray:
        if self.scores:
            return normalise_distribution(self.scores)
        return one_hot(self.emotion, self.confidence)


class FaceExpressionClassifier:
    """Lightweight facial-expression classifier for Ekman-7 emotions.

    This replaces the general-purpose SmolVLM path for emotion recognition.
    It uses a Hugging Face image-classification model fine-tuned for facial
    expression recognition, then normalises model-specific labels into JUNO's
    Ekman taxonomy. A separate mode adapter maps the same Ekman scores back to
    JUNO's original happy/sad/tired/frustrated/stressed/neutral labels.
    """

    def __init__(self, model_id: str, device: str = "auto") -> None:
        self.model_id = model_id
        self.requested_device = device
        self.device = "cpu"
        self.processor = None
        self.model = None
        self.torch = None
        self.loaded = False
        self.load_error: str | None = None
        self._face_cascade = None

    def _select_device(self) -> str:
        if self.requested_device and self.requested_device != "auto":
            return self.requested_device
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except Exception:
            pass
        return "cpu"

    def load(self) -> bool:
        if self.loaded:
            return True
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModelForImageClassification

            self.torch = torch
            self.device = self._select_device()
            self.processor = AutoImageProcessor.from_pretrained(self.model_id)
            try:
                self.model = AutoModelForImageClassification.from_pretrained(
                    self.model_id,
                    low_cpu_mem_usage=True,
                )
            except TypeError:
                self.model = AutoModelForImageClassification.from_pretrained(self.model_id)
            self.model.to(self.device)
            self.model.eval()
            self.load_error = None
            self.loaded = True
            return True
        except Exception as exc:  # pragma: no cover - optional runtime dependencies/model download
            self.load_error = f"{type(exc).__name__}: {exc}"
            self.processor = None
            self.model = None
            self.loaded = False
            return False

    def analyse(self, frame: Any) -> FacialEmotionAnalysis:
        if frame is None:
            return FacialEmotionAnalysis(
                emotion=EmotionState.UNKNOWN,
                confidence=0.0,
                description="No camera frame was available for facial emotion analysis.",
                available=False,
            )

        quality_problem = self._frame_quality_issue(frame)
        if quality_problem:
            return FacialEmotionAnalysis(
                emotion=EmotionState.UNKNOWN,
                confidence=0.0,
                description=quality_problem,
                available=False,
            )

        if not self.load():
            return FacialEmotionAnalysis(
                emotion=EmotionState.UNKNOWN,
                confidence=0.0,
                description="Facial emotion model is unavailable. Check vision dependencies and model download.",
                available=False,
                error=self.load_error,
            )

        try:
            image, face_confidence, used_face_crop = self._frame_to_pil_face(frame)
            scores = self._predict_scores(image)
            emotion, confidence = self._best_emotion(scores)
            if confidence < settings.vision_min_confidence:
                return FacialEmotionAnalysis(
                    emotion=EmotionState.UNKNOWN,
                    confidence=confidence,
                    description=(
                        f"Facial expression evidence was below the confidence threshold "
                        f"({confidence:.2f} < {settings.vision_min_confidence:.2f})."
                    ),
                    scores=scores,
                    face_confidence=face_confidence,
                    used_face_crop=used_face_crop,
                )

            # Avoid the previous failure mode where uncertain neutral states were
            # displayed as a real neutral emotion at roughly 40% confidence.
            if emotion == EmotionState.NEUTRAL and confidence <= settings.vision_neutral_uncertain_confidence:
                return FacialEmotionAnalysis(
                    emotion=EmotionState.UNKNOWN,
                    confidence=confidence,
                    description="Neutral was the top label, but confidence was too low to report as a reliable emotion.",
                    scores=scores,
                    face_confidence=face_confidence,
                    used_face_crop=used_face_crop,
                )

            crop_note = "face crop" if used_face_crop else "full frame fallback"
            return FacialEmotionAnalysis(
                emotion=emotion,
                confidence=confidence,
                description=f"Ekman facial-expression classifier used {crop_note}.",
                raw_output=self._serialise_scores(scores),
                scores=scores,
                face_confidence=face_confidence,
                used_face_crop=used_face_crop,
            )
        except Exception as exc:  # pragma: no cover - runtime dependent
            return FacialEmotionAnalysis(
                emotion=EmotionState.UNKNOWN,
                confidence=0.0,
                description="Facial emotion analysis failed for the current frame.",
                available=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    def _predict_scores(self, image) -> dict[EmotionState, float]:
        assert self.processor is not None
        assert self.model is not None
        assert self.torch is not None

        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {key: value.to(self.device) if hasattr(value, "to") else value for key, value in inputs.items()}
        with self.torch.inference_mode():
            outputs = self.model(**inputs)
            probs = self.torch.nn.functional.softmax(outputs.logits, dim=-1)[0].detach().cpu().numpy()

        id2label = getattr(self.model.config, "id2label", {}) or {}
        scores: dict[EmotionState, float] = {}
        for idx, raw_prob in enumerate(probs):
            raw_label = id2label.get(idx, str(idx))
            emotion = self._normalise_model_label(raw_label)
            if emotion in LABEL_TO_INDEX:
                scores[emotion] = max(scores.get(emotion, 0.0), float(raw_prob))

        # Some community models expose only numeric labels. Prefer an explicit
        # environment-provided order so users can swap FER models without code
        # changes. If not provided, use the common FER2013 order.
        if not scores and len(probs) >= 7:
            fallback_labels = self._fallback_label_order()
            scores = {emotion: float(probs[idx]) for idx, emotion in enumerate(fallback_labels[: len(probs)])}

        total = sum(scores.values())
        if total > 0:
            scores = {emotion: score / total for emotion, score in scores.items()}
        return scores


    @staticmethod
    def _fallback_label_order() -> tuple[EmotionState, ...]:
        configured = getattr(settings, "vision_label_order", "") or ""
        labels: list[EmotionState] = []
        for raw_label in configured.split(","):
            raw_label = raw_label.strip()
            if not raw_label:
                continue
            emotion = FaceExpressionClassifier._normalise_model_label(raw_label)
            if emotion in LABEL_TO_INDEX:
                labels.append(emotion)
        if len(labels) >= 7:
            return tuple(labels)
        return (
            EmotionState.ANGER,
            EmotionState.DISGUST,
            EmotionState.FEAR,
            EmotionState.HAPPINESS,
            EmotionState.SADNESS,
            EmotionState.SURPRISE,
            EmotionState.NEUTRAL,
        )

    @staticmethod
    def _best_emotion(scores: dict[EmotionState, float]) -> tuple[EmotionState, float]:
        if not scores:
            return EmotionState.UNKNOWN, 0.0
        emotion, score = max(scores.items(), key=lambda item: item[1])
        return emotion, float(score)

    @staticmethod
    def _normalise_model_label(label: object) -> EmotionState:
        text = str(label or "unknown").strip().lower()
        text = text.replace("label_", "").replace(" ", "_").replace("-", "_")
        aliases = {
            "0": EmotionState.ANGER,
            "1": EmotionState.DISGUST,
            "2": EmotionState.FEAR,
            "3": EmotionState.HAPPINESS,
            "4": EmotionState.SADNESS,
            "5": EmotionState.SURPRISE,
            "6": EmotionState.NEUTRAL,
            "angry": EmotionState.ANGER,
            "anger": EmotionState.ANGER,
            "disgust": EmotionState.DISGUST,
            "disgusted": EmotionState.DISGUST,
            "fear": EmotionState.FEAR,
            "fearful": EmotionState.FEAR,
            "happy": EmotionState.HAPPINESS,
            "happiness": EmotionState.HAPPINESS,
            "sad": EmotionState.SADNESS,
            "sadness": EmotionState.SADNESS,
            "surprise": EmotionState.SURPRISE,
            "surprised": EmotionState.SURPRISE,
            "neutral": EmotionState.NEUTRAL,
        }
        if text in aliases:
            return aliases[text]
        return normalise_emotion_label(text)

    def _frame_to_pil_face(self, frame: Any):
        from PIL import Image
        arr = np.asarray(frame)
        if isinstance(frame, Image.Image):
            return frame.convert("RGB"), 1.0, False
        if arr.ndim == 2:
            rgb = np.stack([arr, arr, arr], axis=-1).astype("uint8")
        elif arr.ndim == 3 and arr.shape[2] >= 3:
            # ROS/OpenCV frames normally arrive as BGR.
            rgb = arr[:, :, :3][:, :, ::-1].astype("uint8")
        else:
            raise ValueError(f"Unsupported frame shape for facial emotion classifier: {arr.shape}")

        crop, face_confidence = self._extract_largest_face(rgb)
        used_crop = crop is not None
        if crop is None:
            if settings.vision_require_face:
                raise ValueError("No face was detected in the frame.")
            crop = self._centre_crop(rgb)
            face_confidence = 0.0

        image = Image.fromarray(crop).convert("RGB")
        return image, face_confidence, used_crop

    def _extract_largest_face(self, rgb: np.ndarray) -> tuple[np.ndarray | None, float]:
        try:
            import cv2
            if self._face_cascade is None:
                cascade_path = os_path_join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
                self._face_cascade = cv2.CascadeClassifier(cascade_path)
            if self._face_cascade.empty():
                return None, 0.0
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            faces = self._face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(48, 48))
            if len(faces) == 0:
                return None, 0.0
            x, y, w, h = max(faces, key=lambda box: int(box[2]) * int(box[3]))
            pad = int(max(w, h) * 0.18)
            y1 = max(0, y - pad)
            x1 = max(0, x - pad)
            y2 = min(rgb.shape[0], y + h + pad)
            x2 = min(rgb.shape[1], x + w + pad)
            area_ratio = float((w * h) / max(1, rgb.shape[0] * rgb.shape[1]))
            confidence = max(0.35, min(0.95, 0.35 + area_ratio * 2.0))
            return rgb[y1:y2, x1:x2], confidence
        except Exception:
            return None, 0.0

    @staticmethod
    def _centre_crop(rgb: np.ndarray) -> np.ndarray:
        h, w = rgb.shape[:2]
        side = min(h, w)
        y1 = max(0, (h - side) // 2)
        x1 = max(0, (w - side) // 2)
        return rgb[y1:y1 + side, x1:x1 + side]

    @staticmethod
    def _frame_quality_issue(frame: Any) -> str | None:
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

    @staticmethod
    def _serialise_scores(scores: dict[EmotionState, float]) -> str:
        parts = [f"{emotion.value}:{score:.3f}" for emotion, score in scores.items()]
        return "{" + ", ".join(parts) + "}"


def os_path_join(*parts: str) -> str:
    # Local helper avoids importing os at module level for test environments that
    # monkeypatch cv2.data. It also keeps the classifier easy to unit-test.
    import os
    return os.path.join(*parts)
