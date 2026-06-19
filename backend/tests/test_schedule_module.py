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
