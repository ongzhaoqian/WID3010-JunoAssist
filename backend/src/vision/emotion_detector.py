from __future__ import annotations

import os
import random
from typing import Any, Optional, Tuple

import numpy as np

from src.core.config import settings
from src.core.models import EmotionState
from .emotion_fusion import EMAFusion, HysteresisStateMachine
from .emotion_labels import EKMAN_EMOTIONS, JUNO_EMOTIONS, one_hot, normalise_distribution, ekman_to_juno_label
from .facial_expression_classifier import FaceExpressionClassifier, FacialEmotionAnalysis
from .smolvlm_vision import SmolVLMVisionModel, VisionAnalysis

# Mock path now follows the same Ekman taxonomy as the real classifier.
_MOCK_WEIGHTS = [
    EmotionState.NEUTRAL,
    EmotionState.NEUTRAL,
    EmotionState.HAPPINESS,
    EmotionState.SADNESS,
    EmotionState.FEAR,
    EmotionState.ANGER,
    EmotionState.SURPRISE,
]

# Legacy CNN order used by common FER2013 Mini-Xception examples.
_LEGACY_FER_ORDER = (
    EmotionState.ANGER,
    EmotionState.DISGUST,
    EmotionState.FEAR,
    EmotionState.HAPPINESS,
    EmotionState.SADNESS,
    EmotionState.SURPRISE,
    EmotionState.NEUTRAL,
)


def detect_face(frame: np.ndarray, net) -> Tuple[Optional[np.ndarray], float]:
    """Returns (face_roi, confidence) or (None, 0.0)."""
    import cv2
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104, 177, 123))
    net.setInput(blob)
    detections = net.forward()

    best_conf, best_roi = 0.0, None
    for i in range(detections.shape[2]):
        conf = float(detections[0, 0, i, 2])
        if conf < 0.70:
            continue
        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
        x1, y1, x2, y2 = box.astype(int)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if (x2 - x1) * (y2 - y1) < 1000:
            continue
        if conf > best_conf:
            best_conf = conf
            best_roi = frame[y1:y2, x1:x2]
    return best_roi, best_conf


def preprocess_face(face_roi: np.ndarray) -> np.ndarray:
    """Prepare face ROI for legacy Mini-Xception: 64×64 grayscale."""
    import cv2
    face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    face_resized = cv2.resize(face_gray, (64, 64))
    face_norm = face_resized.astype("float32") / 255.0
    return np.expand_dims(np.expand_dims(face_norm, -1), 0)


class EmotionDetector:
    """Core vision detector for JUNO Assist.

    Default production path: a lightweight facial-expression image classifier
    fine-tuned for Ekman-7 emotions. SmolVLM remains available only as an
    opt-in fallback (`JUNO_VISION_BACKEND=smolvlm`) for experiments, because it
    is a general vision-language model and was not reliable for calibrated face
    emotion classification in the robot loop.
    """

    def __init__(self, use_real: bool = False) -> None:
        self.ema = EMAFusion()
        self.hsm = HysteresisStateMachine()
        self.use_real = use_real
        self.backend_name = settings.vision_backend if use_real else "mock"
        self.last_analysis: Optional[VisionAnalysis | FacialEmotionAnalysis] = None
        self.last_confidence: float = 0.0
        self.last_description: str = ""
        self.last_raw_output: str = ""
        self.last_error: Optional[str] = None
        self._face_net = None
        self._cnn_model = None
        self._smolvlm: Optional[SmolVLMVisionModel] = None
        self._facial_classifier: Optional[FaceExpressionClassifier] = None
        self._has_valid_signal = False

        if use_real and self.backend_name in {"fer", "face_expression", "ekman", "vit"}:
            self.backend_name = "face_expression"
            self._facial_classifier = FaceExpressionClassifier(
                model_id=settings.vision_model_id,
                device=settings.vision_device,
            )
        elif use_real and self.backend_name == "smolvlm":
            self._smolvlm = SmolVLMVisionModel(
                model_id=settings.vision_model_id,
                device=settings.vision_device,
                max_new_tokens=settings.vision_max_new_tokens,
            )
        elif use_real and self.backend_name in {"legacy_cnn", "cnn", "opencv"}:
            self._load_legacy_cnn_models()
        elif use_real and self.backend_name not in {"mock", "face_expression", "fer", "ekman", "vit", "smolvlm", "legacy_cnn", "cnn", "opencv"}:
            print(f"[EmotionDetector] Unknown JUNO_VISION_BACKEND={self.backend_name!r}; falling back to mock.")
            self.backend_name = "mock"
            self.use_real = False

    @property
    def model_loaded(self) -> bool:
        if self.backend_name == "face_expression" and self._facial_classifier is not None:
            return self._facial_classifier.loaded
        if self.backend_name == "smolvlm" and self._smolvlm is not None:
            return self._smolvlm.loaded
        if self.backend_name in {"legacy_cnn", "cnn", "opencv"}:
            return self._face_net is not None and self._cnn_model is not None
        return False

    @property
    def model_id(self) -> str:
        if self.backend_name in {"face_expression", "smolvlm"}:
            return settings.vision_model_id
        if self.backend_name in {"legacy_cnn", "cnn", "opencv"}:
            return os.getenv("EMOTION_MODEL_PATH", "models/emotion_model.h5")
        return "mock"

    def _load_legacy_cnn_models(self) -> None:
        try:
            import cv2
            from tensorflow.keras.models import load_model
            proto = "models/deploy.prototxt"
            caffe = "models/res10_300x300_ssd_iter_140000.caffemodel"
            model_path = os.getenv("EMOTION_MODEL_PATH", "models/emotion_model.h5")
            if os.path.exists(proto) and os.path.exists(caffe):
                self._face_net = cv2.dnn.readNetFromCaffe(proto, caffe)
                print("[EmotionDetector] Face detection model loaded.")
            if os.path.exists(model_path):
                self._cnn_model = load_model(model_path, compile=False)
                print("[EmotionDetector] Legacy emotion classification model loaded.")
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            print(f"[EmotionDetector] Legacy CNN load failed: {exc}. Falling back to mock.")
            self.backend_name = "mock"
            self.use_real = False

    def analyse_frame(self, frame: Any = None) -> dict:
        emotion = self.predict_from_frame(frame)
        scores = getattr(self.last_analysis, "scores", {}) if self.last_analysis is not None else {}
        return {
            "emotion": emotion.value if isinstance(emotion, EmotionState) else str(emotion),
            "raw_ekman_emotion": emotion.value if isinstance(emotion, EmotionState) else str(emotion),
            "juno_emotion": ekman_to_juno_label(emotion, scores=scores, source="vision"),
            "confidence": self.last_confidence,
            "description": self.last_description,
            "raw_output": self.last_raw_output,
            "scores": {key.value: float(value) for key, value in scores.items()},
            "ekman_labels": [emotion.value for emotion in EKMAN_EMOTIONS],
            "juno_labels": list(JUNO_EMOTIONS),
            "labels": [emotion.value for emotion in EKMAN_EMOTIONS],
            "backend": self.backend_name,
            "model_id": self.model_id,
            "model_loaded": self.model_loaded,
            "error": self.last_error,
        }

    def predict_from_frame(self, frame: Any = None) -> EmotionState:
        if self.use_real and frame is not None and self.backend_name == "face_expression" and self._facial_classifier is not None:
            return self._predict_with_face_expression(frame)

        if self.use_real and frame is not None and self.backend_name == "smolvlm" and self._smolvlm is not None:
            return self._predict_with_smolvlm(frame)

        if (
            self.use_real
            and frame is not None
            and self.backend_name in {"legacy_cnn", "cnn", "opencv"}
            and self._face_net is not None
            and self._cnn_model is not None
        ):
            return self._predict_with_legacy_cnn(frame)

        P = self._mock_predict()
        self.last_confidence = float(P.max())
        self.last_description = "Mock Ekman emotion used because the real vision model is unavailable or disabled."
        self.last_raw_output = ""
        self.last_error = None
        P_t = self.ema.update(P)
        return self.hsm.update(P_t)

    def _predict_with_face_expression(self, frame: Any) -> EmotionState:
        assert self._facial_classifier is not None
        analysis = self._facial_classifier.analyse(frame)
        return self._apply_analysis(analysis)

    def _predict_with_smolvlm(self, frame: Any) -> EmotionState:
        assert self._smolvlm is not None
        analysis = self._smolvlm.analyse(frame)
        return self._apply_analysis(analysis)

    def _apply_analysis(self, analysis: VisionAnalysis | FacialEmotionAnalysis) -> EmotionState:
        self.last_analysis = analysis
        self.last_confidence = float(analysis.confidence)
        self.last_description = analysis.description
        self.last_raw_output = analysis.raw_output
        self.last_error = analysis.error

        if not analysis.available or analysis.emotion == EmotionState.UNKNOWN:
            return EmotionState.UNKNOWN

        if analysis.confidence < settings.vision_min_confidence:
            self.last_description = self.last_description or "Vision prediction was below the minimum confidence threshold."
            return EmotionState.UNKNOWN

        P = analysis.probabilities()
        fast_switch = (
            analysis.emotion != EmotionState.NEUTRAL
            and analysis.confidence >= settings.vision_fast_switch_confidence
        )
        if not self._has_valid_signal or fast_switch:
            self.ema.P_t = P.copy()
            self.hsm.candidate = analysis.emotion
            self.hsm.current_state = analysis.emotion
            self.hsm.dwell_count = 0
            self._has_valid_signal = True
            return analysis.emotion

        self._has_valid_signal = True
        P_t = self.ema.update(P)
        return self.hsm.update(P_t)

    def _predict_with_legacy_cnn(self, frame: Any) -> EmotionState:
        face_roi, _ = detect_face(frame, self._face_net)
        if face_roi is not None:
            tensor = preprocess_face(face_roi)
            raw = np.asarray(self._cnn_model.predict(tensor, verbose=0)[0], dtype=np.float32)
            scores = {emotion: float(raw[idx]) for idx, emotion in enumerate(_LEGACY_FER_ORDER[: len(raw)])}
            P = normalise_distribution(scores)
            self.last_confidence = float(P.max())
            self.last_description = "Legacy CNN emotion classification mapped to Ekman labels."
            self.last_raw_output = str(scores)
            self.last_error = None
            P_t = self.ema.update(P)
        else:
            self.last_description = "No face was confidently detected by the legacy CNN path."
            self.last_confidence = 0.0
            P_t = self.ema.skip()
        return self.hsm.update(P_t)

    def _mock_predict(self) -> np.ndarray:
        mock_emotion = random.choice(_MOCK_WEIGHTS)
        return one_hot(mock_emotion, confidence=0.88)
