from __future__ import annotations

import os
import random
from typing import Any, Optional, Tuple

import numpy as np

from src.core.config import settings
from src.core.models import EmotionState
from .emotion_fusion import EMAFusion, HysteresisStateMachine
from .smolvlm_vision import SmolVLMVisionModel, VisionAnalysis

# ── Mock predictor weights ────────────────────────────────────────────────────

_MOCK_WEIGHTS = [
    EmotionState.NEUTRAL,
    EmotionState.NEUTRAL,
    EmotionState.NEUTRAL,
    EmotionState.TIRED,
    EmotionState.STRESSED,
    EmotionState.HAPPY,
    EmotionState.FRUSTRATED,
]

# One-hot Juno-5 vectors — index order must match emotion_fusion._LABELS exactly:
# [Happy=0, Neutral=1, Tired=2, Stressed=3, Frustrated=4]
_JUNO_ONE_HOT: dict = {
    EmotionState.HAPPY:      np.array([1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32),
    EmotionState.NEUTRAL:    np.array([0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32),
    EmotionState.TIRED:      np.array([0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32),
    EmotionState.STRESSED:   np.array([0.0, 0.0, 0.0, 1.0, 0.0], dtype=np.float32),
    EmotionState.FRUSTRATED: np.array([0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32),
}

# ── FER-7 → Juno-5 projection matrix ─────────────────────────────────────────
# Rows = Juno-5 [Happy, Neutral, Tired, Stressed, Frustrated]
# Cols = FER-7  [Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral]
MAPPING_MATRIX = np.array([
    [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],  # Happy     ← Happy (1:1)
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.8],  # Neutral   ← Neutral(0.8) + Surprise(0.2)
    [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],  # Tired     ← Sad (low-arousal negative affect)
    [0.3, 0.1, 0.6, 0.0, 0.0, 0.0, 0.0],  # Stressed  ← Fear(0.6)+Angry(0.3)+Disgust(0.1)
    [0.7, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0],  # Frustrated← Angry(0.7)+Disgust(0.3)
], dtype=np.float32)


def _remap(P_raw: np.ndarray) -> np.ndarray:
    """Project 7-class FER softmax onto 5 Juno emotion classes."""
    P_juno = MAPPING_MATRIX @ P_raw
    total = P_juno.sum()
    if total > 0:
        P_juno /= total
    return P_juno


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
    """Prepare face ROI for Mini-Xception: 64×64 grayscale, shape (1, 64, 64, 1)."""
    import cv2
    face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    face_resized = cv2.resize(face_gray, (64, 64))
    face_norm = face_resized.astype("float32") / 255.0
    return np.expand_dims(np.expand_dims(face_norm, -1), 0)


class EmotionDetector:
    """Core vision detector for JUNO Assist.

    Production path: HuggingFaceTB/SmolVLM-256M-Instruct analyses the camera
    frame with a compact image-text prompt and returns a JUNO emotion label.
    The text result is converted into a five-class probability vector, then the
    existing EMA + hysteresis smoother prevents rapid emotion flicker.

    Fallbacks remain available:
    - ``JUNO_VISION_BACKEND=mock`` for lightweight demos/tests.
    - ``JUNO_VISION_BACKEND=legacy_cnn`` for the older OpenCV + CNN experiment.
    """

    def __init__(self, use_real: bool = False) -> None:
        self.ema = EMAFusion()
        self.hsm = HysteresisStateMachine()
        self.use_real = use_real
        self.backend_name = settings.vision_backend if use_real else "mock"
        self.last_analysis: Optional[VisionAnalysis] = None
        self.last_confidence: float = 0.0
        self.last_description: str = ""
        self.last_raw_output: str = ""
        self.last_error: Optional[str] = None
        self._face_net = None
        self._cnn_model = None
        self._smolvlm: Optional[SmolVLMVisionModel] = None

        if use_real and self.backend_name == "smolvlm":
            self._smolvlm = SmolVLMVisionModel(
                model_id=settings.vision_model_id,
                device=settings.vision_device,
                max_new_tokens=settings.vision_max_new_tokens,
            )
        elif use_real and self.backend_name in {"legacy_cnn", "cnn", "opencv"}:
            self._load_legacy_cnn_models()
        elif use_real and self.backend_name not in {"mock", "smolvlm", "legacy_cnn", "cnn", "opencv"}:
            print(f"[EmotionDetector] Unknown JUNO_VISION_BACKEND={self.backend_name!r}; falling back to mock.")
            self.backend_name = "mock"
            self.use_real = False

    @property
    def model_loaded(self) -> bool:
        if self.backend_name == "smolvlm" and self._smolvlm is not None:
            return self._smolvlm.loaded
        if self.backend_name in {"legacy_cnn", "cnn", "opencv"}:
            return self._face_net is not None and self._cnn_model is not None
        return False

    @property
    def model_id(self) -> str:
        if self.backend_name == "smolvlm":
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
                print("[EmotionDetector] Emotion classification model loaded.")
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            print(f"[EmotionDetector] Legacy CNN load failed: {exc}. Falling back to mock.")
            self.backend_name = "mock"
            self.use_real = False

    def analyse_frame(self, frame: Any = None) -> dict:
        emotion = self.predict_from_frame(frame)
        return {
            "emotion": emotion.value if isinstance(emotion, EmotionState) else str(emotion),
            "confidence": self.last_confidence,
            "description": self.last_description,
            "raw_output": self.last_raw_output,
            "backend": self.backend_name,
            "model_id": self.model_id,
            "model_loaded": self.model_loaded,
            "error": self.last_error,
        }

    def predict_from_frame(self, frame: Any = None) -> EmotionState:
        if self.use_real and frame is not None and self.backend_name == "smolvlm" and self._smolvlm is not None:
            return self._predict_with_smolvlm(frame)

        if (self.use_real
                and frame is not None
                and self.backend_name in {"legacy_cnn", "cnn", "opencv"}
                and self._face_net is not None
                and self._cnn_model is not None):
            return self._predict_with_legacy_cnn(frame)

        P_juno = self._mock_predict()
        self.last_confidence = float(P_juno.max())
        self.last_description = "Mock vision emotion used because the real vision model is unavailable or disabled."
        self.last_raw_output = ""
        self.last_error = None
        P_t = self.ema.update(P_juno)
        return self.hsm.update(P_t)

    def _predict_with_smolvlm(self, frame: Any) -> EmotionState:
        analysis = self._smolvlm.analyse(frame)
        self.last_analysis = analysis
        self.last_confidence = float(analysis.confidence)
        self.last_description = analysis.description
        self.last_raw_output = analysis.raw_output
        self.last_error = analysis.error

        if not analysis.available or analysis.emotion == EmotionState.UNKNOWN:
            P_t = self.ema.skip()
        else:
            P_juno = analysis.probabilities()
            # If confidence is too low, bias toward the previous smoothed state.
            if analysis.confidence < settings.vision_min_confidence:
                P_t = self.ema.skip()
            else:
                P_t = self.ema.update(P_juno)
        return self.hsm.update(P_t)

    def _predict_with_legacy_cnn(self, frame: Any) -> EmotionState:
        face_roi, _ = detect_face(frame, self._face_net)
        if face_roi is not None:
            tensor = preprocess_face(face_roi)
            P_raw = self._cnn_model.predict(tensor, verbose=0)[0]
            P_juno = _remap(P_raw)
            self.last_confidence = float(P_juno.max())
            self.last_description = "Legacy CNN emotion classification."
            self.last_raw_output = str(P_juno.tolist())
            self.last_error = None
            P_t = self.ema.update(P_juno)
        else:
            self.last_description = "No face was confidently detected by the legacy CNN path."
            self.last_confidence = 0.0
            P_t = self.ema.skip()
        return self.hsm.update(P_t)

    def _mock_predict(self) -> np.ndarray:
        mock_emotion = random.choice(_MOCK_WEIGHTS)
        return _JUNO_ONE_HOT[mock_emotion].copy()
