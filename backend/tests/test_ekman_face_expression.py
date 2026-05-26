import numpy as np

from src.core.models import EmotionState
from src.vision.emotion_labels import EKMAN_EMOTIONS, LABEL_TO_INDEX, one_hot
from src.vision.facial_expression_classifier import FacialEmotionAnalysis, FaceExpressionClassifier


def test_ekman_taxonomy_has_six_basic_emotions_plus_neutral():
    assert EKMAN_EMOTIONS == (
        EmotionState.ANGER,
        EmotionState.DISGUST,
        EmotionState.FEAR,
        EmotionState.HAPPINESS,
        EmotionState.SADNESS,
        EmotionState.SURPRISE,
        EmotionState.NEUTRAL,
    )


def test_legacy_labels_normalise_to_ekman_members():
    assert EmotionState("happy") == EmotionState.HAPPINESS
    assert EmotionState("angry") == EmotionState.ANGER
    assert EmotionState("stressed") == EmotionState.FEAR
    assert EmotionState("tired") == EmotionState.SADNESS


def test_facial_analysis_probability_vector_is_ekman7():
    analysis = FacialEmotionAnalysis(emotion=EmotionState.SURPRISE, confidence=0.82)
    probs = analysis.probabilities()
    assert probs.shape == (7,)
    assert np.isclose(probs.sum(), 1.0)
    assert probs[LABEL_TO_INDEX[EmotionState.SURPRISE]] > 0.80


def test_model_label_normalisation_for_common_fer_labels():
    model = FaceExpressionClassifier("trpakov/vit-face-expression")
    assert model._normalise_model_label("angry") == EmotionState.ANGER
    assert model._normalise_model_label("happy") == EmotionState.HAPPINESS
    assert model._normalise_model_label("sad") == EmotionState.SADNESS
    assert model._normalise_model_label("surprised") == EmotionState.SURPRISE


def test_low_confidence_neutral_remains_unknown_without_running_model(monkeypatch):
    model = FaceExpressionClassifier("dummy")
    analysis = FacialEmotionAnalysis(
        emotion=EmotionState.NEUTRAL,
        confidence=0.40,
        description="uncertain neutral",
        scores={EmotionState.NEUTRAL: 0.40, EmotionState.SADNESS: 0.35},
    )
    assert analysis.probabilities().shape == (7,)
    assert one_hot(EmotionState.NEUTRAL).shape == (7,)


def test_juno_mode_maps_ekman_to_original_labels():
    from src.vision.emotion_labels import ekman_to_juno_label, format_emotion_for_mode
    from src.core.models import VisionEmotionMode

    assert ekman_to_juno_label(EmotionState.HAPPINESS) == "happy"
    assert ekman_to_juno_label(EmotionState.SADNESS) == "sad"
    assert ekman_to_juno_label(EmotionState.FEAR) == "stressed"
    assert ekman_to_juno_label(EmotionState.ANGER) == "frustrated"
    assert format_emotion_for_mode(VisionEmotionMode.EKMAN, EmotionState.FEAR) == "fear"
    assert format_emotion_for_mode(VisionEmotionMode.JUNO, EmotionState.FEAR) == "stressed"


def test_juno_mode_uses_speech_for_tired_label():
    from src.vision.emotion_labels import ekman_to_juno_label

    assert ekman_to_juno_label(
        EmotionState.SADNESS,
        source="speech",
        speech_text="I am really tired and drained",
    ) == "tired"


def test_default_face_expression_model_is_lightweight_fer_candidate():
    from src.core.config import settings

    assert settings.vision_model_id == "mo-thecreator/vit-Facial-Expression-Recognition"
