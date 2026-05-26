"""
Tests for vision/emotion_smoothing.py (legacy smoother) and
vision/emotion_fusion.py (upgraded EMA + Hysteresis smoother).

Run from backend/: python -m pytest tests/test_emotion_smoothing.py -v
"""
import numpy as np
import pytest

from src.core.models import EmotionState


# ── Legacy EmotionSmoother (keep — still imported by emotion_smoothing.py) ───

def test_emotion_smoother_returns_majority():
    from src.vision.emotion_smoothing import EmotionSmoother
    smoother = EmotionSmoother(window_size=5)
    smoother.add(EmotionState.TIRED)
    smoother.add(EmotionState.NEUTRAL)
    smoother.add(EmotionState.NEUTRAL)
    assert smoother.current() == EmotionState.NEUTRAL


def test_emotion_smoother_empty_returns_unknown():
    from src.vision.emotion_smoothing import EmotionSmoother
    smoother = EmotionSmoother(window_size=5)
    assert smoother.current() == EmotionState.UNKNOWN


# ── EMAFusion ─────────────────────────────────────────────────────────────────

def test_ema_initialises_to_neutral():
    from src.vision.emotion_fusion import EMAFusion
    from src.vision.emotion_labels import LABEL_TO_INDEX
    ema = EMAFusion()
    neutral_idx = LABEL_TO_INDEX[EmotionState.NEUTRAL]
    assert ema.P_t[neutral_idx] == pytest.approx(1.0)
    assert ema.P_t.sum() == pytest.approx(1.0)


def test_ema_skip_does_not_change_distribution():
    from src.vision.emotion_fusion import EMAFusion
    ema = EMAFusion()
    before = ema.P_t.copy()
    result = ema.skip()
    assert np.allclose(result, before)
    assert np.allclose(ema.P_t, before)  # internal state also unchanged


def test_ema_update_moves_toward_input():
    from src.vision.emotion_fusion import EMAFusion
    from src.vision.emotion_labels import LABEL_TO_INDEX, one_hot
    ema = EMAFusion(alpha=0.30)
    P_sadness = one_hot(EmotionState.SADNESS)
    sadness_idx = LABEL_TO_INDEX[EmotionState.SADNESS]
    sadness_before = float(ema.P_t[sadness_idx])
    ema.update(P_sadness)
    assert ema.P_t[sadness_idx] > sadness_before


def test_ema_update_correct_weighted_blend():
    from src.vision.emotion_fusion import EMAFusion
    from src.vision.emotion_labels import LABEL_TO_INDEX, one_hot, empty_distribution
    ema = EMAFusion(alpha=0.30)
    P_sadness = one_hot(EmotionState.SADNESS)
    result = ema.update(P_sadness)
    expected = 0.3 * P_sadness + 0.7 * empty_distribution(neutral=True)
    assert np.allclose(result, expected, atol=1e-5)
    assert result[LABEL_TO_INDEX[EmotionState.SADNESS]] == pytest.approx(0.30)
    assert result[LABEL_TO_INDEX[EmotionState.NEUTRAL]] == pytest.approx(0.70)


def test_ema_update_returns_copy_not_reference():
    from src.vision.emotion_fusion import EMAFusion
    from src.vision.emotion_labels import one_hot
    ema = EMAFusion()
    P_input = one_hot(EmotionState.SADNESS)
    result = ema.update(P_input)
    result[0] = 99.0   # mutate the returned array
    assert ema.P_t[0] != 99.0  # internal state must be unaffected


def test_ema_reset_restores_neutral():
    from src.vision.emotion_fusion import EMAFusion
    from src.vision.emotion_labels import LABEL_TO_INDEX, one_hot
    ema = EMAFusion()
    ema.update(one_hot(EmotionState.HAPPINESS))
    ema.reset()
    assert ema.P_t[LABEL_TO_INDEX[EmotionState.NEUTRAL]] == pytest.approx(1.0)


# ── HysteresisStateMachine ────────────────────────────────────────────────────

def test_hysteresis_starts_neutral():
    from src.vision.emotion_fusion import HysteresisStateMachine
    hsm = HysteresisStateMachine()
    assert hsm.current_state == EmotionState.NEUTRAL


def test_hysteresis_no_transition_before_dwell():
    from src.vision.emotion_fusion import HysteresisStateMachine, DWELL_FRAMES
    hsm = HysteresisStateMachine()
    from src.vision.emotion_labels import one_hot
    P_tired = one_hot(EmotionState.SADNESS)
    for _ in range(DWELL_FRAMES - 1):
        hsm.update(P_tired)
    # 44 frames of Tired — state must still be Neutral
    assert hsm.current_state == EmotionState.NEUTRAL
    assert hsm.dwell_count == DWELL_FRAMES - 1


def test_hysteresis_transitions_at_dwell():
    from src.vision.emotion_fusion import HysteresisStateMachine, DWELL_FRAMES
    hsm = HysteresisStateMachine()
    from src.vision.emotion_labels import one_hot
    P_tired = one_hot(EmotionState.SADNESS)
    for _ in range(DWELL_FRAMES):
        hsm.update(P_tired)
    # Exactly DWELL_FRAMES frames of Tired — must have transitioned
    assert hsm.current_state == EmotionState.TIRED


def test_hysteresis_resets_dwell_on_candidate_change():
    from src.vision.emotion_fusion import HysteresisStateMachine, DWELL_FRAMES
    hsm = HysteresisStateMachine()
    from src.vision.emotion_labels import one_hot
    P_tired = one_hot(EmotionState.SADNESS)
    P_neutral = one_hot(EmotionState.NEUTRAL)

    if DWELL_FRAMES <= 1:
        # Fast-response configuration: one clear Tired frame is enough to commit.
        hsm.update(P_tired)
        assert hsm.current_state == EmotionState.TIRED
        hsm.update(P_neutral)
        assert hsm.candidate == EmotionState.NEUTRAL
        assert hsm.current_state == EmotionState.NEUTRAL
        return

    for _ in range(DWELL_FRAMES - 1):
        hsm.update(P_tired)
    assert hsm.dwell_count == DWELL_FRAMES - 1
    assert hsm.candidate == EmotionState.TIRED

    # Switch candidate to Neutral — dwell count must reset to 1
    hsm.update(P_neutral)
    assert hsm.dwell_count == 1
    assert hsm.candidate == EmotionState.NEUTRAL
    assert hsm.current_state == EmotionState.NEUTRAL  # no transition happened


def test_hysteresis_dwell_resets_after_commit():
    from src.vision.emotion_fusion import HysteresisStateMachine, DWELL_FRAMES
    hsm = HysteresisStateMachine()
    from src.vision.emotion_labels import one_hot
    P_tired = one_hot(EmotionState.SADNESS)
    for _ in range(DWELL_FRAMES):
        hsm.update(P_tired)
    assert hsm.current_state == EmotionState.TIRED
    # dwell_count must be 0 after a committed transition
    assert hsm.dwell_count == 0


def test_hysteresis_committed_state_does_not_flicker():
    from src.vision.emotion_fusion import HysteresisStateMachine, DWELL_FRAMES
    hsm = HysteresisStateMachine()
    from src.vision.emotion_labels import one_hot
    P_tired = one_hot(EmotionState.SADNESS)

    # Commit Tired
    for _ in range(DWELL_FRAMES):
        hsm.update(P_tired)
    assert hsm.current_state == EmotionState.TIRED

    # Feed 100 more Tired frames — state must remain Tired
    for _ in range(100):
        state = hsm.update(P_tired)
    assert state == EmotionState.TIRED


# ── EmotionDetector integration (mock path) ───────────────────────────────────

_VALID_STATES = {
    EmotionState.ANGER,
    EmotionState.DISGUST,
    EmotionState.FEAR,
    EmotionState.HAPPINESS,
    EmotionState.SADNESS,
    EmotionState.SURPRISE,
    EmotionState.NEUTRAL,
}


def test_mock_detector_returns_valid_emotion():
    from src.vision.emotion_detector import EmotionDetector
    detector = EmotionDetector()
    result = detector.predict_from_frame(frame=None)
    assert isinstance(result, EmotionState)
    assert result in _VALID_STATES


def test_mock_detector_never_returns_unknown():
    from src.vision.emotion_detector import EmotionDetector
    detector = EmotionDetector()
    for _ in range(20):
        result = detector.predict_from_frame(frame=None)
        assert result != EmotionState.UNKNOWN


def test_mock_detector_accepts_none_frame():
    """predict_from_frame must not raise when called with None (mock mode, no camera)."""
    from src.vision.emotion_detector import EmotionDetector
    detector = EmotionDetector()
    try:
        detector.predict_from_frame(frame=None)
    except Exception as exc:
        pytest.fail(f"predict_from_frame(None) raised: {exc}")


def test_mock_detector_hsm_prevents_rapid_state_change():
    """After committing a state via direct EMA+HSM drive, fewer than DWELL_FRAMES
    calls to predict_from_frame cannot change it — because the new candidate's dwell
    count starts at 0 and needs DWELL_FRAMES more frames to commit a different state.
    This test is deterministic (bypasses random mock) to avoid flakiness.

    Why DWELL_FRAMES + 1 iterations:
      EMA iteration 0: Neutral still leads (P_t[Neutral]=0.70 > P_t[Tired]=0.30).
      HSM candidate stays Neutral for 1 iteration, then switches to Tired at iteration 1.
      So the HSM only counts DWELL_FRAMES consecutive Tired frames from iteration 1,
      requiring DWELL_FRAMES + 1 total iterations to commit the transition.
    """
    from src.vision.emotion_fusion import DWELL_FRAMES
    from src.vision.emotion_detector import EmotionDetector

    detector = EmotionDetector()

    from src.vision.emotion_labels import one_hot
    P_tired = one_hot(EmotionState.SADNESS)
    for _ in range(DWELL_FRAMES + 1):
        detector.ema.update(P_tired)
        committed = detector.hsm.update(detector.ema.P_t)
    assert committed == EmotionState.TIRED

    # The HSM is now committed to Tired with dwell_count=0.
    # Making 3 predict_from_frame calls (with random inputs) cannot change current_state
    # because any new candidate would need DWELL_FRAMES=45 consecutive frames to commit.
    for _ in range(3):
        result = detector.predict_from_frame(frame=None)
        assert result in _VALID_STATES  # valid output, no crash
