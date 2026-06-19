import threading
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.calendar_module.calendar_service import CalendarService


def authenticated_client(app):
    client = TestClient(app)
    login = client.post(
        "/api/auth/login",
        json={"username": "mackwongyy@gmail.com", "password": "12345678"},
    )
    assert login.status_code == 200, login.text
    client.headers.update({"Authorization": f"Bearer {login.json()['token']}"})
    return client


def test_connections_use_wal_journal_mode(tmp_path):
    db_path = tmp_path / "juno_test.db"
    service = CalendarService(str(db_path))

    with service._connect() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

    assert mode.lower() == "wal"


def test_schedule_items_table_has_notification_columns(tmp_path):
    db_path = tmp_path / "juno_test.db"
    service = CalendarService(str(db_path))

    with service._connect() as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(schedule_items)").fetchall()}

    assert "notified_30" in columns
    assert "notified_due" in columns


def test_update_schedule_item_changes_only_provided_fields(tmp_path):
    db_path = tmp_path / "juno_test.db"
    service = CalendarService(str(db_path))
    service.set_active_user(1)
    item = service.add_schedule_item(
        "Deep Learning revision", date="2026-06-20", time="14:00", type="study", priority="medium", user_id=1
    )

    updated = service.update_schedule_item(item["id"], time="16:00", priority="high", user_id=1)

    assert updated is not None
    assert updated["title"] == "Deep Learning revision"
    assert updated["date"] == "2026-06-20"
    assert updated["time"] == "16:00"
    assert updated["priority"] == "high"

    with service._connect() as conn:
        row = conn.execute("SELECT time, priority FROM schedule_items WHERE id = ?", (item["id"],)).fetchone()
    assert row == ("16:00", "high")


def test_update_schedule_item_returns_none_for_wrong_owner(tmp_path):
    db_path = tmp_path / "juno_test.db"
    service = CalendarService(str(db_path))
    service.set_active_user(1)
    item = service.add_schedule_item("Owner's task", date="2026-06-20", time="09:00", user_id=1)

    result = service.update_schedule_item(item["id"], priority="high", user_id=2)

    assert result is None


def test_update_schedule_item_resets_notification_flags(tmp_path):
    db_path = tmp_path / "juno_test.db"
    service = CalendarService(str(db_path))
    service.set_active_user(1)
    item = service.add_schedule_item("Group meeting", date="2026-06-20", time="09:00", user_id=1)
    service.mark_notified(item["id"], "30")
    service.mark_notified(item["id"], "due")

    service.update_schedule_item(item["id"], time="10:00", user_id=1)

    with service._connect() as conn:
        row = conn.execute(
            "SELECT notified_30, notified_due FROM schedule_items WHERE id = ?", (item["id"],)
        ).fetchone()
    assert row == (0, 0)


def test_notification_fires_30_minutes_before_and_at_due_time_once_each(tmp_path):
    db_path = tmp_path / "juno_test.db"
    service = CalendarService(str(db_path))
    service.set_active_user(1)
    item = service.add_schedule_item("Deep Learning revision", date="2026-06-19", time="10:00", user_id=1)

    due_at = datetime(2026, 6, 19, 10, 0)
    just_before_30 = due_at - timedelta(minutes=30, seconds=5)

    due_items = service.get_items_needing_notification(just_before_30, tolerance_seconds=15)
    assert any(d["id"] == item["id"] and d["stage"] == "30" for d in due_items)
    for d in due_items:
        service.mark_notified(d["id"], d["stage"])

    due_items_again = service.get_items_needing_notification(just_before_30, tolerance_seconds=15)
    assert not any(d["stage"] == "30" for d in due_items_again)

    due_items_at_due = service.get_items_needing_notification(due_at, tolerance_seconds=15)
    assert any(d["id"] == item["id"] and d["stage"] == "due" for d in due_items_at_due)
    for d in due_items_at_due:
        service.mark_notified(d["id"], d["stage"])

    due_items_final = service.get_items_needing_notification(due_at, tolerance_seconds=15)
    assert due_items_final == []


def test_notification_handles_multiple_consecutive_schedules_in_same_tick(tmp_path):
    db_path = tmp_path / "juno_test.db"
    service = CalendarService(str(db_path))
    service.set_active_user(1)
    first = service.add_schedule_item("Morning class", date="2026-06-19", time="09:00", user_id=1)
    second = service.add_schedule_item("Group meeting", date="2026-06-19", time="09:00", user_id=1)
    third = service.add_schedule_item("Lab session", date="2026-06-19", time="09:05", user_id=1)

    now = datetime(2026, 6, 19, 9, 0)
    due_items = service.get_items_needing_notification(now, tolerance_seconds=15)
    fired_ids = {d["id"] for d in due_items if d["stage"] == "due"}

    assert first["id"] in fired_ids
    assert second["id"] in fired_ids
    assert third["id"] not in fired_ids

    for d in due_items:
        service.mark_notified(d["id"], d["stage"])

    later = now + timedelta(minutes=5)
    due_items_later = service.get_items_needing_notification(later, tolerance_seconds=15)
    fired_ids_later = {d["id"] for d in due_items_later if d["stage"] == "due"}

    assert fired_ids_later == {third["id"]}


def test_notification_skips_items_without_date_or_time(tmp_path):
    db_path = tmp_path / "juno_test.db"
    service = CalendarService(str(db_path))
    service.set_active_user(1)
    service.add_schedule_item("No date set", user_id=1)

    due_items = service.get_items_needing_notification(datetime(2026, 6, 19, 9, 0), tolerance_seconds=15)

    assert due_items == []


def test_schedule_full_crud_cycle(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(tmp_path / "juno_test.db"))
    client = authenticated_client(create_app())

    created = client.post(
        "/api/schedule",
        json={"title": "Deep Learning revision", "date": "2026-06-20", "time": "14:00", "type": "study", "priority": "medium"},
    )
    assert created.status_code == 200
    item_id = created.json()["id"]

    today_items = client.get("/api/schedule/today").json()
    assert any(i["id"] == item_id for i in today_items)

    updated = client.put(f"/api/schedule/{item_id}", json={"time": "16:00", "priority": "high"})
    assert updated.status_code == 200
    assert updated.json()["time"] == "16:00"
    assert updated.json()["priority"] == "high"
    assert updated.json()["title"] == "Deep Learning revision"

    deleted = client.delete(f"/api/schedule/{item_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    assert client.get("/api/schedule/today").json() == []


def test_schedule_update_and_delete_reject_other_users_item(tmp_path, monkeypatch):
    db_path = tmp_path / "juno_test.db"
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(db_path))
    app = create_app()

    owner_client = authenticated_client(app)
    created = owner_client.post(
        "/api/schedule",
        json={"title": "Owner's task", "date": "2026-06-20", "time": "09:00"},
    )
    item_id = created.json()["id"]

    other_client = TestClient(app)
    signup = other_client.post(
        "/api/auth/signup", json={"username": "intruder@example.com", "password": "password123"}
    )
    assert signup.status_code == 200
    other_client.headers.update({"Authorization": f"Bearer {signup.json()['token']}"})

    update_attempt = other_client.put(f"/api/schedule/{item_id}", json={"priority": "high"})
    assert update_attempt.status_code == 404

    delete_attempt = other_client.delete(f"/api/schedule/{item_id}")
    assert delete_attempt.status_code == 404


def test_notification_check_reflects_items_created_through_the_api(tmp_path, monkeypatch):
    db_path = tmp_path / "juno_test.db"
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(db_path))

    client = authenticated_client(create_app())
    created = client.post(
        "/api/schedule",
        json={"title": "Lab session", "date": "2026-06-19", "time": "09:00", "type": "study", "priority": "medium"},
    )
    item_id = created.json()["id"]

    service = CalendarService(str(db_path))
    due_items = service.get_items_needing_notification(datetime(2026, 6, 19, 9, 0), tolerance_seconds=15)
    assert any(d["id"] == item_id and d["stage"] == "due" for d in due_items)

    for d in due_items:
        service.mark_notified(d["id"], d["stage"])

    due_items_again = service.get_items_needing_notification(datetime(2026, 6, 19, 9, 0), tolerance_seconds=15)
    assert due_items_again == []


def test_concurrent_schedule_writes_do_not_raise_locked_error(tmp_path):
    db_path = tmp_path / "juno_test.db"
    service = CalendarService(str(db_path))
    service.set_active_user(1)
    errors: list[Exception] = []

    def worker(index: int) -> None:
        try:
            for i in range(10):
                item = service.add_schedule_item(f"Task {index}-{i}", date="2026-06-19", time="08:00", user_id=1)
                service.update_schedule_item(item["id"], priority="high", user_id=1)
                service.get_today_schedule(user_id=1)
        except Exception as exc:  # pragma: no cover - failure path under test
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(service.get_today_schedule(user_id=1)) == 80
