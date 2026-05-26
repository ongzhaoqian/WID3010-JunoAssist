import numpy as np

from src.core.models import EmotionState
from src.vision.emotion_detector import EmotionDetector
from src.vision.smolvlm_vision import SmolVLMVisionModel, VisionAnalysis


def test_low_confidence_neutral_is_not_reported_as_real_emotion():
    model = SmolVLMVisionModel()
    parsed = model._parse_output('{"emotion":"neutral","confidence":0.40,"description":"ambiguous frame"}')
    assert parsed.emotion == EmotionState.UNKNOWN
    assert parsed.confidence <= 0.25


def test_visual_cues_override_vague_neutral_json():
    model = SmolVLMVisionModel()
    parsed = model._parse_output(
        '{"emotion":"neutral","confidence":0.40,"description":"furrowed brow and tense mouth are visible"}'
    )
    assert parsed.emotion == EmotionState.STRESSED
    assert parsed.confidence > 0.40


def test_nested_scores_json_selects_highest_emotion():
    model = SmolVLMVisionModel()
    parsed = model._parse_output(
        '{"scores":{"happy":0.05,"neutral":0.15,"tired":0.10,"stressed":0.62,"frustrated":0.08},'
        '"visual_cues":["furrowed brow"],"description":"tense expression"}'
    )
    assert parsed.emotion == EmotionState.STRESSED
    probs = parsed.probabilities()
    assert np.isclose(probs.sum(), 1.0)
    from src.vision.emotion_labels import LABEL_TO_INDEX
    assert probs[LABEL_TO_INDEX[EmotionState.STRESSED]] == probs.max()


class _FakeUnavailableSmol:
    loaded = False

    def analyse(self, frame):
        return VisionAnalysis(
            emotion=EmotionState.UNKNOWN,
            confidence=0.0,
            description="model unavailable",
            available=False,
            error="missing dependency",
        )


class _FakeStressedSmol:
    loaded = True

    def analyse(self, frame):
        return VisionAnalysis(
            emotion=EmotionState.STRESSED,
            confidence=0.68,
            description="furrowed brow and tense mouth",
            raw_output='{"emotion":"stressed","confidence":0.68}',
        )


def test_detector_does_not_fall_back_to_neutral_when_smolvlm_unavailable():
    detector = EmotionDetector(use_real=False)
    detector.use_real = True
    detector.backend_name = "smolvlm"
    detector._smolvlm = _FakeUnavailableSmol()

    result = detector.predict_from_frame(frame=np.ones((32, 32, 3), dtype=np.uint8) * 100)
    assert result == EmotionState.UNKNOWN
    assert detector.last_confidence == 0.0
    assert detector.last_error == "missing dependency"


def test_detector_fast_switches_clear_non_neutral_smolvlm_prediction():
    detector = EmotionDetector(use_real=False)
    detector.use_real = True
    detector.backend_name = "smolvlm"
    detector._smolvlm = _FakeStressedSmol()

    result = detector.predict_from_frame(frame=np.ones((32, 32, 3), dtype=np.uint8) * 100)
    assert result == EmotionState.STRESSED
    assert detector.last_confidence == 0.68
