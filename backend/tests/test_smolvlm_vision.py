import numpy as np

from src.core.models import EmotionState
from src.vision.smolvlm_vision import SmolVLMVisionModel, VisionAnalysis


def test_smolvlm_json_output_parser():
    model = SmolVLMVisionModel()
    parsed = model._parse_output('{"emotion":"stressed","confidence":0.82,"description":"furrowed brow"}')
    assert parsed.emotion == EmotionState.STRESSED
    assert parsed.confidence == 0.82
    assert "furrowed" in parsed.description


def test_smolvlm_prose_output_parser():
    model = SmolVLMVisionModel()
    parsed = model._parse_output('The user appears tired. Confidence: 72%.')
    assert parsed.emotion == EmotionState.TIRED
    assert parsed.confidence >= 0.72


def test_vision_analysis_probability_vector_sums_to_one():
    analysis = VisionAnalysis(emotion=EmotionState.HAPPY, confidence=0.80)
    probs = analysis.probabilities()
    assert probs.shape == (7,)
    assert np.isclose(probs.sum(), 1.0)
    from src.vision.emotion_labels import LABEL_TO_INDEX
    assert probs[LABEL_TO_INDEX[EmotionState.HAPPINESS]] > 0.75


def test_smolvlm_unavailable_without_frame():
    model = SmolVLMVisionModel()
    analysis = model.analyse(None)
    assert analysis.available is False
    assert analysis.emotion == EmotionState.UNKNOWN
