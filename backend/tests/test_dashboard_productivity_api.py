import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.models import EmotionState, RobotMode
from src.core.state import robot_state
from src.nlp.intent_classifier import IntentClassifier


@pytest.fixture(autouse=True)
def reset_robot_state():
    """Reset shared robot_state between tests to prevent state leakage."""
    robot_state.delete_timer()
    robot_state.set_mode(RobotMode.IDLE)
    robot_state.set_awaiting_timer_duration(False)
    robot_state.set_awaiting_timer_minutes(False)
    robot_state.set_awaiting_timer_seconds(False)
    yield
    robot_state.delete_timer()


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
    assert ask.json()["status"]["awaiting_timer_minutes"] is True

    minutes_reply = client.post("/api/command", json={"text": "1"})
    assert minutes_reply.status_code == 200
    assert minutes_reply.json()["status"]["awaiting_timer_seconds"] is True

    seconds_reply = client.post("/api/command", json={"text": "15"})
    assert seconds_reply.status_code == 200
    payload = seconds_reply.json()
    assert payload["timer"]["remaining_seconds"] == 75
    assert payload["status"]["awaiting_timer_duration"] is False
    assert payload["status"]["awaiting_timer_minutes"] is False
    assert payload["status"]["awaiting_timer_seconds"] is False


def test_music_play_uses_current_emotion_and_spotify_embed():
    client = TestClient(create_app())
    robot_state.set_emotion(EmotionState.STRESSED)

    response = client.post("/api/music/play")
    assert response.status_code == 200
    payload = response.json()
    assert payload["emotion"] == "fear"
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
    assert ask.json()["status"]["awaiting_timer_minutes"] is True

    cancel = client.post("/api/command", json={"text": "cancel"})
    assert cancel.status_code == 200
    payload = cancel.json()
    assert payload["status"]["awaiting_timer_minutes"] is False
    assert payload["status"]["awaiting_timer_seconds"] is False
    assert "timer" in payload["response"].lower()


def test_voice_timer_flow_cancels_after_repeated_unclear_answers():
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)
    robot_state.set_awaiting_timer_duration(True)

    first = client.post("/api/command", json={"text": "zero minutes"})
    assert first.status_code == 200
    assert first.json()["status"]["awaiting_timer_duration"] is True

    second = client.post("/api/command", json={"text": "zero seconds"})
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


def test_timer_duration_parser_handles_noisy_asr_number_phrases():
    classifier = IntentClassifier()
    assert classifier.extract_timer_duration_seconds("for twenty five minutes") == 1500
    assert classifier.extract_timer_duration_seconds("i want five minutes") == 300
    assert classifier.extract_timer_duration_seconds("five minutes and thirty seconds") == 330
    assert classifier.extract_timer_duration_seconds("one minute and five") == 65
    assert classifier.extract_timer_duration_seconds("two minutes five") == 125
    assert classifier.extract_timer_duration_seconds("5 and 30") == 330
    assert classifier.extract_timer_duration_seconds("twenty five") == 1500
    assert classifier.extract_spoken_number("zero seconds") == 0
    assert classifier.extract_spoken_number("make it thirty") == 30


def test_speech_emotion_overrides_visual_emotion_for_break_request():
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)
    robot_state.set_emotion(EmotionState.HAPPY, source="vision", confidence=0.60)

    response = client.post("/api/command", json={"text": "I am stressed"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"]["current_emotion"] == "fear"
    assert payload["status"]["emotion_source"] == "speech"
    assert "stressed" in payload["response"].lower()


def test_dashboard_reminder_uses_schedule_like_columns_and_can_be_deleted(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(tmp_path / "juno_test.db"))
    client = TestClient(create_app())

    created = client.post(
        "/api/reminders",
        json={
            "title": "Submit project report",
            "date": "2026-05-22",
            "time": "21:00",
            "type": "assignment",
            "priority": "high",
        },
    )
    assert created.status_code == 200
    item = created.json()
    assert item["title"] == "Submit project report"
    assert item["date"] == "2026-05-22"
    assert item["formatted_date"] == "22 May, 2026"
    assert item["time"] == "21:00"
    assert item["type"] == "assignment"
    assert item["priority"] == "high"
    assert item["due_date"] == "2026-05-22"
    assert item["due_time"] == "21:00"

    reminders = client.get("/api/reminders").json()
    assert any(row["id"] == item["id"] and row["type"] == "assignment" for row in reminders)

    deleted = client.delete(f"/api/reminders/{item['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_voice_can_add_and_then_read_updated_reminder_list(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(tmp_path / "juno_test.db"))
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)

    add = client.post(
        "/api/command",
        json={"text": "remind me to submit project report date 2026-05-22 time 21:00 priority high"},
    )
    assert add.status_code == 200
    add_payload = add.json()
    assert add_payload["intent"] == "add_reminder"
    assert add_payload["reminder"]["title"] == "Submit project report"

    check = client.post("/api/command", json={"text": "what are my reminders"})
    assert check.status_code == 200
    check_payload = check.json()
    assert check_payload["intent"] == "check_reminders"
    assert "Submit project report" in check_payload["response"]
    assert any(item["title"] == "Submit project report" for item in check_payload["reminders"])


def test_voice_schedule_reads_dashboard_added_items(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(tmp_path / "juno_test.db"))
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)

    created = client.post(
        "/api/schedule",
        json={
            "title": "Dashboard-added consultation",
            "date": "2026-05-23",
            "time": "10:30",
            "type": "meeting",
            "priority": "medium",
        },
    )
    assert created.status_code == 200

    response = client.post("/api/command", json={"text": "what is my schedule today"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "check_schedule"
    assert "Dashboard-added consultation" in payload["response"]


def test_timer_completion_payload_is_emitted_once():
    robot_state.set_timer(1, "Study timer")
    completed = robot_state.decrement_timer()
    assert completed is not None
    snapshot = robot_state.snapshot()
    assert snapshot["timer_remaining_seconds"] == 0
    assert snapshot["last_timer_completed_label"] == "Study timer"
    assert snapshot["timer_completed_counter"] >= 1
    assert robot_state.decrement_timer() is None


def test_voice_stop_command_stops_music_without_speaking_acknowledgement():
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)
    robot_state.set_awaiting_timer_duration(True)

    client.post("/api/music/play")
    response = client.post("/api/command", json={"text": "stop"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "stop"
    assert payload["music"]["status"] == "stopped"
    assert payload["status"]["awaiting_timer_duration"] is False


def test_voice_schedule_add_accepts_natural_date_and_time(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(tmp_path / "juno_test.db"))
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)

    response = client.post(
        "/api/command",
        json={"text": "add schedule on 25 May at nine pm purpose project discussion priority high"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "add_schedule"
    assert payload["schedule_item"]["time"] == "21:00"
    assert payload["schedule_item"]["title"] == "Project discussion"


def test_dashboard_timer_pause_resume_and_stop_endpoints():
    client = TestClient(create_app())

    start = client.post("/api/timer/start", json={"minutes": 0, "seconds": 45})
    assert start.status_code == 200
    assert start.json()["status"]["timer_remaining_seconds"] == 45

    pause = client.post("/api/timer/pause")
    assert pause.status_code == 200
    pause_payload = pause.json()
    assert pause_payload["paused"] is True
    assert pause_payload["status"]["timer_paused"] is True
    assert pause_payload["status"]["timer_paused_remaining"] == 45

    resume = client.post("/api/timer/resume")
    assert resume.status_code == 200
    resume_payload = resume.json()
    assert resume_payload["resumed"] is True
    assert resume_payload["status"]["timer_paused"] is False
    assert resume_payload["status"]["timer_remaining_seconds"] == 45

    stop = client.post("/api/timer/stop")
    assert stop.status_code == 200
    stop_payload = stop.json()
    assert stop_payload["stopped"] is True
    assert stop_payload["status"]["timer_remaining_seconds"] == 0
    assert stop_payload["status"]["timer_paused"] is False


def test_voice_stop_timer_uses_fuzzy_stop_commands():
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)
    robot_state.set_timer(120, "Study timer")

    response = client.post("/api/command", json={"text": "end the countdown now"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"]["timer_remaining_seconds"] == 0
    assert payload["status"]["timer_paused"] is False
    assert payload.get("timer_action") == "stopped"


def test_voice_pause_and_resume_timer_commands():
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)
    robot_state.set_timer(90, "Study timer")

    pause = client.post("/api/command", json={"text": "pause timer"})
    assert pause.status_code == 200
    pause_payload = pause.json()
    assert pause_payload["status"]["timer_paused"] is True
    assert pause_payload.get("timer_action") == "paused"

    resume = client.post("/api/command", json={"text": "resume timer"})
    assert resume.status_code == 200
    resume_payload = resume.json()
    assert resume_payload["status"]["timer_paused"] is False
    assert resume_payload["status"]["timer_remaining_seconds"] == 90
    assert resume_payload.get("timer_action") == "resumed"


def test_stop_speaking_does_not_delete_running_timer():
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)
    robot_state.set_timer(60, "Study timer")

    response = client.post("/api/command", json={"text": "stop speaking"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "stop"
    assert payload["status"]["timer_remaining_seconds"] == 60


def test_robot_sleep_requests_dashboard_close_and_runtime_powerdown(monkeypatch):
    from src.system.dashboard_lifecycle import DashboardLifecycleManager

    monkeypatch.setattr(DashboardLifecycleManager, "close_dashboard", lambda self: {"closed": True})
    monkeypatch.setattr(DashboardLifecycleManager, "cleanup_powerdown_processes", lambda self: None)
    client = TestClient(create_app())
    robot_state.set_mode(RobotMode.ACTIVE)
    robot_state.mark_dashboard_open()

    response = client.post("/api/robot/sleep")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"]["mode"] == "idle"
    assert payload["status"]["dashboard_should_close"] is True
    assert payload["status"]["dashboard_open"] is False


def test_dashboard_open_endpoint_reuses_dashboard_state(monkeypatch):
    from src.system.dashboard_lifecycle import DashboardLifecycleManager

    monkeypatch.setattr(DashboardLifecycleManager, "open_or_focus", lambda self, url: {"opened": False, "focused": True, "url": url})
    client = TestClient(create_app())
    robot_state.request_dashboard_close()

    response = client.post("/api/dashboard/open")

    assert response.status_code == 200
    status = response.json()["status"]
    assert status["dashboard_should_close"] is False
    assert status["dashboard_open"] is True


def test_fitness_profile_session_and_stats(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(tmp_path / "juno_test.db"))
    client = TestClient(create_app())

    profile = client.post("/api/fitness/profile", json={"height_m": 1.7, "weight_kg": 60}).json()
    assert profile["height_m"] == 1.7
    assert profile["weight_kg"] == 60
    assert profile["complete"] is True

    session = client.post("/api/fitness/sessions", json={"score_67": 67, "source": "test", "duration_seconds": 60})
    assert session.status_code == 200
    payload = session.json()
    assert payload["score_67"] == 67
    assert payload["calories_burned"] is not None

    latest = client.get("/api/fitness/stats?scope=latest").json()
    assert latest["score_67"] == 67
    assert latest["session_count"] == 1
    assert latest["calories_burned"] == payload["calories_burned"]

    client.post("/api/fitness/sessions", json={"score_67": 33, "source": "test", "duration_seconds": 30})
    cumulative = client.get("/api/fitness/stats?scope=cumulative").json()
    assert cumulative["score_67"] == 100
    assert cumulative["session_count"] == 2
    assert cumulative["calories_burned"] > latest["calories_burned"]


def test_fitness_session_without_profile_marks_calories_pending(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(tmp_path / "juno_test.db"))
    client = TestClient(create_app())

    response = client.post("/api/fitness/sessions", json={"score_67": 10})
    assert response.status_code == 200
    assert response.json()["calories_burned"] is None

    stats = client.get("/api/fitness/stats?scope=latest").json()
    assert stats["needs_profile"] is True
    assert stats["calories_burned"] is None



def test_database_refresh_on_start_clears_runtime_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "juno_test.db"
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(db_path))

    client = TestClient(create_app())
    created = client.post(
        "/api/schedule",
        json={"title": "Temporary row", "date": "2026-05-20", "time": "10:00", "type": "study", "priority": "medium"},
    )
    assert created.status_code == 200
    assert client.get("/api/schedule/today").json()

    # A fresh app startup should clear previous runtime rows by default.
    refreshed_client = TestClient(create_app())
    assert refreshed_client.get("/api/schedule/today").json() == []


def test_startup_does_not_load_sample_schedule_dataset(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(tmp_path / "juno_test.db"))
    client = TestClient(create_app())

    schedule = client.get("/api/schedule/today")
    assert schedule.status_code == 200
    assert schedule.json() == []

    reminders = client.get("/api/reminders")
    assert reminders.status_code == 200
    assert reminders.json() == []

    fitness_stats = client.get("/api/fitness/stats?scope=cumulative")
    assert fitness_stats.status_code == 200
    assert fitness_stats.json()["session_count"] == 0
