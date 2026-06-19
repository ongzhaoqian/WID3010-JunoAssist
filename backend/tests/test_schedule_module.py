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
