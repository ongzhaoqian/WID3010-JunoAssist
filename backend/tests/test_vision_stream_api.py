from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.state import robot_state


def test_camera_and_vision_model_have_separate_controls():
    robot_state.set_camera_enabled(False)
    robot_state.set_vision_model_enabled(False)
    client = TestClient(create_app())

    initial = client.get("/api/vision/status")
    assert initial.status_code == 200
    payload = initial.json()
    assert payload["camera_enabled"] is False
    assert payload["vision_model_enabled"] is False
    assert payload["camera_topic"] == "/camera/image_raw"

    camera_started = client.post("/api/vision/camera/start")
    assert camera_started.status_code == 200
    assert camera_started.json()["camera_enabled"] is True
    assert camera_started.json()["vision_model_enabled"] is False

    model_started = client.post("/api/vision/model/start")
    assert model_started.status_code == 200
    assert model_started.json()["camera_enabled"] is True
    assert model_started.json()["vision_model_enabled"] is True

    model_stopped = client.post("/api/vision/model/stop")
    assert model_stopped.status_code == 200
    assert model_stopped.json()["camera_enabled"] is True
    assert model_stopped.json()["vision_model_enabled"] is False

    camera_stopped = client.post("/api/vision/camera/stop")
    assert camera_stopped.status_code == 200
    assert camera_stopped.json()["camera_enabled"] is False


def test_legacy_vision_start_stop_routes_control_model_only():
    robot_state.set_camera_enabled(False)
    robot_state.set_vision_model_enabled(False)
    client = TestClient(create_app())

    started = client.post("/api/vision/start")
    assert started.status_code == 200
    assert started.json()["camera_enabled"] is False
    assert started.json()["vision_model_enabled"] is True
    assert started.json()["enabled"] is True

    stopped = client.post("/api/vision/stop")
    assert stopped.status_code == 200
    assert stopped.json()["camera_enabled"] is False
    assert stopped.json()["vision_model_enabled"] is False
    assert stopped.json()["enabled"] is False


def test_camera_frame_returns_no_content_without_mock_frame():
    client = TestClient(create_app())
    response = client.get("/api/vision/camera/frame.jpg")
    assert response.status_code == 204


def test_vision_mode_can_switch_between_juno_and_ekman():
    from src.core.models import EmotionState, VisionEmotionMode

    robot_state.set_vision_emotion_mode(VisionEmotionMode.JUNO)
    robot_state.set_emotion(EmotionState.FEAR, source="vision", confidence=0.8)
    client = TestClient(create_app())

    initial = client.get("/api/vision/status").json()
    assert initial["vision_emotion_mode"] == "juno"
    assert initial["display_emotion"] == "stressed"
    assert initial["raw_ekman_emotion"] == "fear"

    switched = client.post("/api/vision/mode", json={"mode": "ekman"})
    assert switched.status_code == 200
    payload = switched.json()
    assert payload["vision_emotion_mode"] == "ekman"
    assert payload["display_emotion"] == "scared"
    assert payload["juno_emotion"] == "stressed"

    back = client.post("/api/vision/mode", json={"mode": "juno"}).json()
    assert back["display_emotion"] == "stressed"


def test_stress_class_emotion_sets_break_suggestion():
    from src.core.models import EmotionState, VisionEmotionMode

    robot_state.set_vision_emotion_mode(VisionEmotionMode.JUNO)
    robot_state.set_emotion(EmotionState.FEAR, source="vision", confidence=0.82)

    stress_payload = robot_state.snapshot()
    assert stress_payload["display_emotion"] == "stressed"
    assert stress_payload["break_suggested"] is True

    robot_state.set_emotion(EmotionState.HAPPINESS, source="vision", confidence=0.9)
    happy_payload = robot_state.snapshot()
    assert happy_payload["display_emotion"] == "happy"
    assert happy_payload["break_suggested"] is False
