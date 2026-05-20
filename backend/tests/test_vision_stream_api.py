from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.state import robot_state


def test_vision_status_start_stop_cycle():
    robot_state.set_vision_enabled(False)
    client = TestClient(create_app())

    initial = client.get("/api/vision/status")
    assert initial.status_code == 200
    assert initial.json()["enabled"] is False
    assert initial.json()["camera_topic"] == "/camera/image_raw"

    started = client.post("/api/vision/start")
    assert started.status_code == 200
    assert started.json()["enabled"] is True

    stopped = client.post("/api/vision/stop")
    assert stopped.status_code == 200
    assert stopped.json()["enabled"] is False


def test_camera_frame_returns_no_content_without_mock_frame():
    client = TestClient(create_app())
    response = client.get("/api/vision/camera/frame.jpg")
    assert response.status_code == 204
