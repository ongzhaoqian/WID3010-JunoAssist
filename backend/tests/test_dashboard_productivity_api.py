from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.models import EmotionState, RobotMode
from src.core.state import robot_state
from src.nlp.intent_classifier import IntentClassifier


def test_schedule_item_can_be_added_and_removed(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(tmp_path / "juno_test.db"))
    client = TestClient(create_app())

    created = client.post(
        "/api/schedule",
        json={
            "title": "Revision block",
            "date": "2026-05-20",
            "time": "15:30",
            "type": "study",
            "priority": "high",
        },
    )
    assert created.status_code == 200
    item = created.json()
    assert item["title"] == "Revision block"

    schedule = client.get("/api/schedule/today").json()
    assert any(row["id"] == item["id"] for row in schedule)

    deleted = client.delete(f"/api/schedule/{item['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_timer_accepts_minutes_and_seconds():
    client = TestClient(create_app())
    response = client.post("/api/timer/start", json={"minutes": 1, "seconds": 30})

    assert response.status_code == 200
    payload = response.json()
    assert payload["remaining_seconds"] == 90
    assert "1 minute and 30 seconds" in payload["message"]


def test_voice_timer_flow_asks_then_starts_duration():
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)
    robot_state.set_awaiting_timer_duration(False)

    ask = client.post("/api/command", json={"text": "start study timer"})
    assert ask.status_code == 200
    assert ask.json()["status"]["awaiting_timer_duration"] is True

    answer = client.post("/api/command", json={"text": "1 minute 15 seconds"})
    assert answer.status_code == 200
    payload = answer.json()
    assert payload["timer"]["remaining_seconds"] == 75
    assert payload["status"]["awaiting_timer_duration"] is False


def test_music_play_uses_current_emotion_and_spotify_embed():
    client = TestClient(create_app())
    robot_state.set_emotion(EmotionState.STRESSED)

    response = client.post("/api/music/play")
    assert response.status_code == 200
    payload = response.json()
    assert payload["emotion"] == "stressed"
    assert "open.spotify.com/embed" in payload["embed_url"]

    status = client.get("/api/music/status")
    assert status.status_code == 200
    assert status.json()["status"] == "playing"


def test_timer_duration_parser_supports_minutes_and_seconds():
    classifier = IntentClassifier()
    assert classifier.extract_timer_duration_seconds("25 minutes") == 1500
    assert classifier.extract_timer_duration_seconds("1 minute 30 seconds") == 90
    assert classifier.extract_timer_duration_seconds("90 seconds") == 90
    assert classifier.extract_timer_duration_seconds("2:30") == 150
    assert classifier.extract_timer_duration_seconds("25") == 1500


def test_voice_schedule_add_accepts_structured_transcription(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(tmp_path / "juno_test.db"))
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)

    response = client.post(
        "/api/command",
        json={
            "text": "add schedule date 2026-05-20 time 15:30 purpose deep learning revision priority high"
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "add_schedule"
    assert payload["schedule_item"]["title"] == "Deep learning revision"
    assert payload["schedule_item"]["date"] == "2026-05-20"
    assert payload["schedule_item"]["formatted_date"] == "20 May, 2026"
    assert payload["schedule_item"]["time"] == "15:30"
    assert payload["schedule_item"]["priority"] == "high"
    assert "20 May, 2026" in payload["response"]


def test_voice_timer_flow_can_be_cancelled():
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)
    robot_state.set_awaiting_timer_duration(False)

    ask = client.post("/api/command", json={"text": "start study timer"})
    assert ask.status_code == 200
    assert ask.json()["status"]["awaiting_timer_duration"] is True

    cancel = client.post("/api/command", json={"text": "cancel"})
    assert cancel.status_code == 200
    payload = cancel.json()
    assert payload["status"]["awaiting_timer_duration"] is False
    assert "timer" in payload["response"].lower()


def test_voice_timer_flow_cancels_after_repeated_unclear_answers():
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)
    robot_state.set_awaiting_timer_duration(True)

    first = client.post("/api/command", json={"text": "umm maybe"})
    assert first.status_code == 200
    assert first.json()["status"]["awaiting_timer_duration"] is True

    second = client.post("/api/command", json={"text": "still not sure"})
    assert second.status_code == 200
    assert second.json()["status"]["awaiting_timer_duration"] is False


def test_timer_duration_parser_supports_flexible_spoken_formats():
    classifier = IntentClassifier()
    assert classifier.extract_timer_duration_seconds("twenty five minutes") == 1500
    assert classifier.extract_timer_duration_seconds("one minute thirty seconds") == 90
    assert classifier.extract_timer_duration_seconds("1h 30m") == 5400
    assert classifier.extract_timer_duration_seconds("half an hour") == 1800
    assert classifier.extract_timer_duration_seconds("quarter of an hour") == 900
    assert classifier.extract_timer_duration_seconds("one and a half hours") == 5400


def test_speech_emotion_overrides_visual_emotion_for_break_request():
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)
    robot_state.set_emotion(EmotionState.HAPPY, source="vision", confidence=0.60)

    response = client.post("/api/command", json={"text": "I am stressed"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"]["current_emotion"] == "stressed"
    assert payload["status"]["emotion_source"] == "speech"
    assert "stressed" in payload["response"].lower()
