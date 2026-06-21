# Schedule CRUD, Persistence, and Notifications — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the schedule module full CRUD (add update + keep delete/create/read), make schedule items survive backend restarts, and proactively speak a notification 30 minutes before and at the moment each schedule item is due — without ever raising a SQLite "database is locked" error, and without one schedule item's notification blocking or skipping another's in the same check tick.

**Architecture:** `CalendarService` (`backend/src/calendar_module/calendar_service.py`) owns all SQLite access for `schedule_items`. We add an `update_schedule_item` method, two notification-tracking columns (`notified_30`, `notified_due`), a `get_items_needing_notification` scan method, and a `mark_notified` method. `app.py` gains a `PUT /api/schedule/{item_id}` route and a new `_schedule_notification_loop()` background task (same `asyncio.create_task` pattern already used for `_timer_loop`/`_emotion_monitor_loop`), which calls `tts.speak()` per due item. The dashboard gets a `putJson` helper and an edit mode on `SchedulePanel.jsx`.

**Tech Stack:** Python 3.11, FastAPI, sqlite3 (stdlib), pytest, React (Vite), vanilla `fetch`.

---

## Design notes carried over from the spec (read before starting)

- **No DB locking:** every connection opened by `CalendarService._connect()` will set `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`. Combined with the existing pattern of short-lived `with self._connect() as conn:` blocks (one connection per call, closed/committed immediately), concurrent reads/writes queue briefly instead of raising `OperationalError: database is locked`.
- **No notification hiccups on consecutive schedules:** `get_items_needing_notification` returns a **list** — every item/stage combination that currently qualifies, not just the first one found. The notification loop in `app.py` iterates that whole list every tick, speaking and marking each one independently inside its own `try/except`, so one failing item (e.g. a TTS error) can't block or skip the next item due in the same tick. The trigger condition is also **one-sided** (`now >= target - tolerance`, no upper bound) rather than a tightly bounded window — this means a delayed loop tick (e.g. system briefly busy) still eventually fires every pending notification exactly once, instead of silently missing a narrow window. The `notified_30`/`notified_due` flags are what guarantee "exactly once" per stage.
- Schedule items persist across restart; **reminders are out of scope** for this plan (separate action-plan owner) and keep being cleared on `reset_runtime_data()`.

---

### Task 1: Enable WAL mode + busy timeout on every connection

**Files:**
- Modify: `backend/src/calendar_module/calendar_service.py:19-20`
- Test: `backend/tests/test_schedule_module.py` (new file, created in this task)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_schedule_module.py` with this initial content:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py::test_connections_use_wal_journal_mode -v`
Expected: FAIL — `assert mode.lower() == "wal"` fails because the current journal mode is `delete` (the sqlite3 default).

- [ ] **Step 3: Implement WAL mode + busy timeout**

In `backend/src/calendar_module/calendar_service.py`, replace:

```python
    def _connect(self):
        return sqlite3.connect(self.db_path)
```

with:

```python
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        # WAL mode lets readers and writers proceed concurrently instead of
        # blocking each other; busy_timeout makes any remaining brief
        # contention retry instead of immediately raising "database is
        # locked" (relevant now that the notification loop polls this same
        # database from a background asyncio task alongside API requests).
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py::test_connections_use_wal_journal_mode -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add src/calendar_module/calendar_service.py tests/test_schedule_module.py
git commit -m "Enable WAL journal mode and busy timeout for calendar SQLite connections"
```

---

### Task 2: Add `notified_30` / `notified_due` columns

**Files:**
- Modify: `backend/src/calendar_module/calendar_service.py:61-65` (`_migrate_schedule_columns`)
- Test: `backend/tests/test_schedule_module.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_schedule_module.py`:

```python
def test_schedule_items_table_has_notification_columns(tmp_path):
    db_path = tmp_path / "juno_test.db"
    service = CalendarService(str(db_path))

    with service._connect() as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(schedule_items)").fetchall()}

    assert "notified_30" in columns
    assert "notified_due" in columns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py::test_schedule_items_table_has_notification_columns -v`
Expected: FAIL — the columns don't exist yet.

- [ ] **Step 3: Add the migration**

In `backend/src/calendar_module/calendar_service.py`, replace:

```python
    def _migrate_schedule_columns(self, conn: sqlite3.Connection) -> None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(schedule_items)").fetchall()}
        if "user_id" not in columns:
            conn.execute("ALTER TABLE schedule_items ADD COLUMN user_id INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_items_user ON schedule_items(user_id, date, time, id)")
```

with:

```python
    def _migrate_schedule_columns(self, conn: sqlite3.Connection) -> None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(schedule_items)").fetchall()}
        if "user_id" not in columns:
            conn.execute("ALTER TABLE schedule_items ADD COLUMN user_id INTEGER")
        if "notified_30" not in columns:
            conn.execute("ALTER TABLE schedule_items ADD COLUMN notified_30 INTEGER DEFAULT 0")
        if "notified_due" not in columns:
            conn.execute("ALTER TABLE schedule_items ADD COLUMN notified_due INTEGER DEFAULT 0")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_items_user ON schedule_items(user_id, date, time, id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_items_notify ON schedule_items(notified_30, notified_due)")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py::test_schedule_items_table_has_notification_columns -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add src/calendar_module/calendar_service.py tests/test_schedule_module.py
git commit -m "Add notification tracking columns to schedule_items"
```

---

### Task 3: `update_schedule_item` (the missing CRUD operation)

**Files:**
- Modify: `backend/src/calendar_module/calendar_service.py` (add method after `delete_schedule_item`, currently ending at line 173)
- Test: `backend/tests/test_schedule_module.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_schedule_module.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py -k "changes_only_provided_fields or wrong_owner" -v`
Expected: FAIL — `AttributeError: 'CalendarService' object has no attribute 'update_schedule_item'`.

(`test_update_schedule_item_resets_notification_flags` also calls `mark_notified`, which doesn't exist until Task 4 — skip running that one for now; it's revisited at the end of Task 4.)

- [ ] **Step 3: Implement `update_schedule_item`**

In `backend/src/calendar_module/calendar_service.py`, add this method directly after `delete_schedule_item` (which currently ends at line 173):

```python
    def update_schedule_item(
        self,
        item_id: int,
        *,
        title: str | None = None,
        date: str | None = None,
        time: str | None = None,
        type: str | None = None,
        priority: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any] | None:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT title, date, time, type, priority FROM schedule_items WHERE id = ? AND user_id = ?",
                (item_id, resolved_user_id),
            ).fetchone()
            if row is None:
                return None

            updated_title = title.strip() if title is not None else row[0]
            updated_date = date if date is not None else row[1]
            updated_time = time if time is not None else row[2]
            updated_type = (type.strip().lower() if type else row[3]) if type is not None else row[3]
            updated_priority = (priority.strip().lower() if priority else row[4]) if priority is not None else row[4]

            conn.execute(
                """
                UPDATE schedule_items
                SET title = ?, date = ?, time = ?, type = ?, priority = ?,
                    notified_30 = 0, notified_due = 0
                WHERE id = ? AND user_id = ?
                """,
                (updated_title, updated_date, updated_time, updated_type, updated_priority, item_id, resolved_user_id),
            )

        return {
            "id": item_id,
            "title": updated_title,
            "date": updated_date,
            "formatted_date": self.format_display_date(updated_date),
            "time": updated_time,
            "type": updated_type,
            "priority": updated_priority,
            "user_id": resolved_user_id,
        }
```

This resets `notified_30`/`notified_due` to `0` on every edit — if the user changes the time, any prior notification state for the old time no longer applies, and the item should be eligible for fresh notifications at the new time.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py -k "changes_only_provided_fields or wrong_owner" -v`
Expected: PASS (2 passed). `test_update_schedule_item_resets_notification_flags` still fails until Task 4 — that's expected, leave it for now.

- [ ] **Step 5: Commit**

```bash
cd backend
git add src/calendar_module/calendar_service.py tests/test_schedule_module.py
git commit -m "Add update_schedule_item for full schedule CRUD"
```

---

### Task 4: Notification scan (`get_items_needing_notification`) + `mark_notified`

**Files:**
- Modify: `backend/src/calendar_module/calendar_service.py` (imports at line 1-4, add methods after `update_schedule_item`)
- Test: `backend/tests/test_schedule_module.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_schedule_module.py`:

```python
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

    # Checking again at the same moment must not re-fire the 30-minute stage.
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
    assert third["id"] not in fired_ids  # 5 minutes out, outside the 15s tolerance

    for d in due_items:
        service.mark_notified(d["id"], d["stage"])

    later = now + timedelta(minutes=5)
    due_items_later = service.get_items_needing_notification(later, tolerance_seconds=15)
    fired_ids_later = {d["id"] for d in due_items_later if d["stage"] == "due"}

    # Only the third item's due stage should fire now; the already-notified
    # first/second items must not fire again.
    assert fired_ids_later == {third["id"]}


def test_notification_skips_items_without_date_or_time(tmp_path):
    db_path = tmp_path / "juno_test.db"
    service = CalendarService(str(db_path))
    service.set_active_user(1)
    service.add_schedule_item("No date set", user_id=1)

    due_items = service.get_items_needing_notification(datetime(2026, 6, 19, 9, 0), tolerance_seconds=15)

    assert due_items == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py -k notification -v`
Expected: FAIL — `AttributeError: 'CalendarService' object has no attribute 'get_items_needing_notification'`.

- [ ] **Step 3: Implement the methods**

In `backend/src/calendar_module/calendar_service.py`, change the import line at the top from:

```python
from datetime import datetime
```

to:

```python
from datetime import datetime, timedelta
```

Then add these two methods directly after `update_schedule_item`:

```python
    def get_items_needing_notification(
        self, now: datetime, tolerance_seconds: float = 15.0
    ) -> list[dict[str, Any]]:
        """Return every (item, stage) pair currently due for a spoken notification.

        Each schedule item can independently need a "30 minutes before" and/or
        "at the due time" notification; both are returned as separate entries
        so the caller can announce and mark each one without one blocking the
        other when several items are due in the same check tick.

        The trigger condition is one-sided (now >= target - tolerance, with no
        upper bound) rather than a tight window. This means a delayed check
        tick still eventually surfaces every pending notification exactly
        once; the notified_30/notified_due flags (set via mark_notified) are
        what make each stage fire only once per item.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, title, date, time, type, priority, notified_30, notified_due
                FROM schedule_items
                WHERE date IS NOT NULL AND date != ''
                  AND time IS NOT NULL AND time != ''
                  AND (notified_30 = 0 OR notified_due = 0)
                """
            ).fetchall()

        tolerance = timedelta(seconds=tolerance_seconds)
        due_items: list[dict[str, Any]] = []
        for row in rows:
            item_id, user_id, title, date, time_value, item_type, priority, notified_30, notified_due = row
            try:
                due_at = datetime.strptime(f"{date} {time_value}", "%Y-%m-%d %H:%M")
            except ValueError:
                continue

            base = {
                "id": item_id,
                "user_id": user_id,
                "title": title,
                "date": date,
                "time": time_value,
                "type": item_type,
                "priority": priority,
            }

            if not notified_30 and now >= (due_at - timedelta(minutes=30) - tolerance):
                due_items.append({**base, "stage": "30"})
            if not notified_due and now >= (due_at - tolerance):
                due_items.append({**base, "stage": "due"})

        return due_items

    def mark_notified(self, item_id: int, stage: str) -> None:
        column = "notified_30" if stage == "30" else "notified_due"
        with self._connect() as conn:
            conn.execute(f"UPDATE schedule_items SET {column} = 1 WHERE id = ?", (item_id,))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py -k "notification or update_schedule_item" -v`
Expected: PASS (all notification tests, plus the now-unblocked `test_update_schedule_item_resets_notification_flags` from Task 3).

- [ ] **Step 5: Commit**

```bash
cd backend
git add src/calendar_module/calendar_service.py tests/test_schedule_module.py
git commit -m "Add schedule notification scan with consecutive-schedule-safe tolerance windows"
```

---

### Task 5: Stop wiping schedule items on backend restart

**Files:**
- Modify: `backend/src/calendar_module/calendar_service.py:54-59` (`reset_runtime_data`)
- Modify: `backend/tests/test_dashboard_productivity_api.py:475-489` (existing test that currently asserts the opposite behavior)

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_dashboard_productivity_api.py`, replace the existing test:

```python
def test_database_refresh_on_start_clears_runtime_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "juno_test.db"
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(db_path))

    client = authenticated_client(create_app())
    created = client.post(
        "/api/schedule",
        json={"title": "Temporary row", "date": "2026-05-20", "time": "10:00", "type": "study", "priority": "medium"},
    )
    assert created.status_code == 200
    assert client.get("/api/schedule/today").json()

    # A fresh app startup should clear previous runtime rows by default.
    refreshed_client = authenticated_client(create_app())
    assert refreshed_client.get("/api/schedule/today").json() == []
```

with:

```python
def test_schedule_persists_while_reminders_reset_on_restart(tmp_path, monkeypatch):
    db_path = tmp_path / "juno_test.db"
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(db_path))

    client = authenticated_client(create_app())
    created = client.post(
        "/api/schedule",
        json={"title": "Temporary row", "date": "2026-05-20", "time": "10:00", "type": "study", "priority": "medium"},
    )
    assert created.status_code == 200
    assert client.get("/api/schedule/today").json()

    reminder = client.post(
        "/api/reminders",
        json={"title": "Old reminder", "date": "2026-05-20", "time": "10:00"},
    )
    assert reminder.status_code == 200
    assert client.get("/api/reminders").json()

    # A fresh app startup intentionally keeps schedule items (action plan
    # requirement: "Schedule persists across restarts") but still clears
    # reminders, matching the existing demo-reset behavior for that table.
    refreshed_client = authenticated_client(create_app())
    assert refreshed_client.get("/api/schedule/today").json()
    assert refreshed_client.get("/api/reminders").json() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_dashboard_productivity_api.py::test_schedule_persists_while_reminders_reset_on_restart -v`
Expected: FAIL — `assert refreshed_client.get("/api/schedule/today").json()` fails because the schedule item was wiped (current behavior).

- [ ] **Step 3: Stop clearing `schedule_items`**

In `backend/src/calendar_module/calendar_service.py`, replace:

```python
    def reset_runtime_data(self) -> None:
        """Clear all user-scoped schedule/reminder rows for a fresh backend session."""
        with self._connect() as conn:
            conn.execute("DELETE FROM schedule_items")
            conn.execute("DELETE FROM reminders")
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('schedule_items', 'reminders')")
```

with:

```python
    def reset_runtime_data(self) -> None:
        """Clear reminder rows for a fresh backend session.

        Schedule items intentionally persist across restarts (action plan
        requirement); only reminders are reset here.
        """
        with self._connect() as conn:
            conn.execute("DELETE FROM reminders")
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'reminders'")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_dashboard_productivity_api.py::test_schedule_persists_while_reminders_reset_on_restart -v`
Expected: PASS

Then run the full productivity test file to make sure nothing else broke:

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_dashboard_productivity_api.py -v`
Expected: all PASS, including `test_startup_does_not_load_sample_schedule_dataset` (still valid — a brand-new db has no schedule rows to begin with).

- [ ] **Step 5: Commit**

```bash
cd backend
git add src/calendar_module/calendar_service.py tests/test_dashboard_productivity_api.py
git commit -m "Persist schedule items across backend restarts; keep reminders reset"
```

---

### Task 6: `ScheduleItemUpdateRequest` model

**Files:**
- Modify: `backend/src/core/models.py:141-147`

- [ ] **Step 1: Add the model**

In `backend/src/core/models.py`, directly after the existing `ScheduleItemRequest` class:

```python
class ScheduleItemRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    date: Optional[str] = None
    time: Optional[str] = None
    type: str = Field(default="study", max_length=40)
    priority: str = Field(default="medium", max_length=20)


class ScheduleItemUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    date: Optional[str] = None
    time: Optional[str] = None
    type: Optional[str] = Field(default=None, max_length=40)
    priority: Optional[str] = Field(default=None, max_length=20)
```

(All fields optional, since `PUT` here means partial update — only supplied fields change.)

- [ ] **Step 2: Verify the module still imports cleanly**

Run: `cd backend && PYTHONPATH=. venv/bin/python -c "from src.core.models import ScheduleItemUpdateRequest; print(ScheduleItemUpdateRequest())"`
Expected: prints `title=None date=None time=None type=None priority=None` with no errors.

- [ ] **Step 3: Commit**

```bash
cd backend
git add src/core/models.py
git commit -m "Add ScheduleItemUpdateRequest for partial schedule edits"
```

---

### Task 7: Notification check interval setting + phrase bank entries

**Files:**
- Modify: `backend/src/core/config.py:38` (add a setting next to `emotion_update_seconds`)
- Modify: `backend/src/nlp/phrase_bank.py:179-184` (add two new template keys)

- [ ] **Step 1: Add the setting**

In `backend/src/core/config.py`, directly after the line `emotion_update_seconds: float = float(os.getenv("JUNO_EMOTION_UPDATE_SECONDS", "3.0"))`, add:

```python
    # How often the background loop scans for schedule items due a spoken
    # notification (30 minutes before, and at, the scheduled time). Also used
    # as the tolerance window so a check tick never misses a notification.
    schedule_notification_check_seconds: float = float(os.getenv("JUNO_SCHEDULE_NOTIFICATION_CHECK_SECONDS", "15.0"))
```

- [ ] **Step 2: Add the phrase bank entries**

In `backend/src/nlp/phrase_bank.py`, directly after the `"reminder_removed"` entry (currently ending at line 183, right before the closing `})`), add:

```python
        "schedule_reminder_30": [
            "Upcoming: {title} in 30 minutes.",
            "Heads up, {title} starts in 30 minutes.",
        ],
        "schedule_reminder_due": [
            "{title} starts now.",
            "It is time for {title}.",
        ],
```

So the surrounding block reads:

```python
        "reminder_removed": [
            "Reminder removed.",
            "Done. I have removed that reminder.",
        ],
        "schedule_reminder_30": [
            "Upcoming: {title} in 30 minutes.",
            "Heads up, {title} starts in 30 minutes.",
        ],
        "schedule_reminder_due": [
            "{title} starts now.",
            "It is time for {title}.",
        ],
    })
```

- [ ] **Step 3: Verify with a quick interactive check**

Run: `cd backend && PYTHONPATH=. venv/bin/python -c "from src.nlp.phrase_bank import PhraseBank; pb = PhraseBank(seed=1); print(pb.say('schedule_reminder_30', title='Deep Learning revision')); print(pb.say('schedule_reminder_due', title='Deep Learning revision'))"`
Expected: prints two sentences, each containing "Deep Learning revision".

- [ ] **Step 4: Commit**

```bash
cd backend
git add src/core/config.py src/nlp/phrase_bank.py
git commit -m "Add schedule notification interval setting and spoken phrase templates"
```

---

### Task 8: `PUT /api/schedule/{item_id}` endpoint

**Files:**
- Modify: `backend/src/api/app.py:20` (import) and `backend/src/api/app.py:959-966` (insert new route after the existing `DELETE /api/schedule/{item_id}`)
- Test: `backend/tests/test_schedule_module.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_schedule_module.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py -k "full_crud_cycle or reject_other_users" -v`
Expected: FAIL — `client.put(...)` returns 405 Method Not Allowed (no `PUT` route registered yet).

- [ ] **Step 3: Add the route**

In `backend/src/api/app.py`, change the import line:

```python
from src.core.models import AuthRequest, CommandRequest, ReminderRequest, ScheduleItemRequest, TimerRequest, MusicPlayRequest, VisionModeRequest, FitnessProfileRequest, FitnessSessionRequest, RobotMode, Intent, EmotionState, VisionEmotionMode
```

to:

```python
from src.core.models import AuthRequest, CommandRequest, ReminderRequest, ScheduleItemRequest, ScheduleItemUpdateRequest, TimerRequest, MusicPlayRequest, VisionModeRequest, FitnessProfileRequest, FitnessSessionRequest, RobotMode, Intent, EmotionState, VisionEmotionMode
```

Then, directly after the existing `delete_schedule_item` route:

```python
    @app.delete("/api/schedule/{item_id}")
    def delete_schedule_item(item_id: int, user: dict = Depends(_require_user)):
        deleted = calendar_service.delete_schedule_item(item_id, user_id=user["id"])
        if not deleted:
            raise HTTPException(status_code=404, detail="Schedule item not found")
        robot_state.set_response("Schedule item removed.")
        return {"deleted": True, "id": item_id}
```

add:

```python
    @app.put("/api/schedule/{item_id}")
    def update_schedule_item(item_id: int, request: ScheduleItemUpdateRequest, user: dict = Depends(_require_user)):
        item = calendar_service.update_schedule_item(
            item_id,
            title=request.title,
            date=request.date,
            time=request.time,
            type=request.type,
            priority=request.priority,
            user_id=user["id"],
        )
        if item is None:
            raise HTTPException(status_code=404, detail="Schedule item not found")
        robot_state.set_response(
            phrase_bank.say(
                "schedule_added",
                purpose=item["title"],
                date=item.get("formatted_date") or item.get("date") or "not specified",
                time=item.get("time") or "not specified",
                priority=item.get("priority") or "medium",
            )
        )
        return item
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py -k "full_crud_cycle or reject_other_users" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add src/api/app.py tests/test_schedule_module.py
git commit -m "Add PUT /api/schedule/{item_id} endpoint for schedule edits"
```

---

### Task 9: Background notification loop

**Files:**
- Modify: `backend/src/api/app.py:1-9` (add `datetime` import), `backend/src/api/app.py:719-720` (register the task), and add a new `_schedule_notification_loop` function next to `_timer_loop`
- Test: `backend/tests/test_schedule_module.py`

- [ ] **Step 1: Write the failing test**

This test verifies the building blocks the loop relies on (`CalendarService.get_items_needing_notification`/`mark_notified`) through the real `/api/schedule` write path, confirming the wiring is sound before the loop itself is added. Append to `backend/tests/test_schedule_module.py`:

```python
def test_notification_check_reflects_items_created_through_the_api(tmp_path, monkeypatch):
    db_path = tmp_path / "juno_test.db"
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(db_path))

    client = authenticated_client(create_app())
    created = client.post(
        "/api/schedule",
        json={"title": "Lab session", "date": "2026-06-19", "time": "09:00", "type": "study", "priority": "medium"},
    )
    item_id = created.json()["id"]

    # Drive a CalendarService bound to the same db file to simulate exactly
    # one notification-loop tick at the due time.
    service = CalendarService(str(db_path))
    due_items = service.get_items_needing_notification(datetime(2026, 6, 19, 9, 0), tolerance_seconds=15)
    assert any(d["id"] == item_id and d["stage"] == "due" for d in due_items)

    for d in due_items:
        service.mark_notified(d["id"], d["stage"])

    due_items_again = service.get_items_needing_notification(datetime(2026, 6, 19, 9, 0), tolerance_seconds=15)
    assert due_items_again == []
```

- [ ] **Step 2: Run test to verify it passes already**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py::test_notification_check_reflects_items_created_through_the_api -v`
Expected: PASS (this exercises `CalendarService`, already implemented in Task 4 — confirming the loop's building blocks work through the real API before wiring the loop itself in Step 3).

- [ ] **Step 3: Implement the loop**

In `backend/src/api/app.py`, change the import line:

```python
from typing import Optional
```

to:

```python
from datetime import datetime
from typing import Optional
```

Then, directly after the existing `_timer_loop` function:

```python
    async def _timer_loop():
        while True:
            completed = robot_state.decrement_timer()
            if completed:
                response = phrase_bank.say("timer_finished", label=completed.get("label") or "study timer")
                robot_state.set_response(response)
                robot.set_led_state("timer_complete")
                tts.speak(response)
            await asyncio.sleep(1)
```

add:

```python
    async def _schedule_notification_loop():
        while True:
            try:
                due_items = calendar_service.get_items_needing_notification(
                    datetime.now(), tolerance_seconds=settings.schedule_notification_check_seconds
                )
            except Exception:
                due_items = []
            for due_item in due_items:
                try:
                    if due_item["stage"] == "30":
                        message = phrase_bank.say("schedule_reminder_30", title=due_item["title"])
                    else:
                        message = phrase_bank.say("schedule_reminder_due", title=due_item["title"])
                    robot_state.set_response(message)
                    tts.speak(message)
                    calendar_service.mark_notified(due_item["id"], due_item["stage"])
                except Exception:
                    # One item's failure (e.g. a TTS error) must not block or
                    # skip the next item due in the same tick.
                    continue
            await asyncio.sleep(settings.schedule_notification_check_seconds)
```

Then register it in `startup_event`, changing:

```python
        asyncio.create_task(_emotion_monitor_loop())
        asyncio.create_task(_timer_loop())
        if settings.use_ros_robot:
            asyncio.create_task(_ros_speech_command_loop())
```

to:

```python
        asyncio.create_task(_emotion_monitor_loop())
        asyncio.create_task(_timer_loop())
        asyncio.create_task(_schedule_notification_loop())
        if settings.use_ros_robot:
            asyncio.create_task(_ros_speech_command_loop())
```

- [ ] **Step 4: Run the full schedule test file**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py -v`
Expected: all PASS.

- [ ] **Step 5: Manual smoke check that the loop starts without error**

Run:
```bash
cd backend && JUNO_DATABASE_PATH=/tmp/juno_smoke.db PYTHONPATH=. venv/bin/python -c "
from fastapi.testclient import TestClient
from src.api.app import create_app
with TestClient(create_app()) as client:
    pass
print('startup_event ran without raising')
"
```
Expected: prints `startup_event ran without raising` (the `TestClient` context manager triggers FastAPI's startup event, which now also creates the notification loop task, with no exceptions).

- [ ] **Step 6: Commit**

```bash
cd backend
git add src/api/app.py tests/test_schedule_module.py
git commit -m "Add background schedule notification loop (30-min and due-time)"
```

---

### Task 10: Concurrency check — no "database is locked" under simultaneous writes

**Files:**
- Test: `backend/tests/test_schedule_module.py`

- [ ] **Step 1: Write the test**

Append to `backend/tests/test_schedule_module.py`:

```python
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
```

- [ ] **Step 2: Run the test**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py::test_concurrent_schedule_writes_do_not_raise_locked_error -v`
Expected: PASS — with WAL mode and `busy_timeout=5000` from Task 1, this should already pass. If it fails with `sqlite3.OperationalError: database is locked`, re-check that `_connect()` sets both pragmas (Task 1, Step 3) before continuing.

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/test_schedule_module.py
git commit -m "Add concurrency test verifying no SQLite locking under parallel schedule writes"
```

---

### Task 11: Persistence-across-restart integration test (full app, not just the service)

**Files:**
- Test: `backend/tests/test_schedule_module.py`

- [ ] **Step 1: Write the test**

Append to `backend/tests/test_schedule_module.py`:

```python
def test_schedule_persists_across_app_restart(tmp_path, monkeypatch):
    db_path = tmp_path / "juno_test.db"
    monkeypatch.setenv("JUNO_DATABASE_PATH", str(db_path))

    first_client = authenticated_client(create_app())
    created = first_client.post(
        "/api/schedule",
        json={"title": "Persisted task", "date": "2026-06-21", "time": "11:00"},
    )
    assert created.status_code == 200

    second_client = authenticated_client(create_app())
    items = second_client.get("/api/schedule/today").json()
    assert any(i["title"] == "Persisted task" for i in items)
```

- [ ] **Step 2: Run the test**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest tests/test_schedule_module.py::test_schedule_persists_across_app_restart -v`
Expected: PASS (Task 5 already made this true; this test exercises it through a second, independent `create_app()` call rather than the service directly).

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/test_schedule_module.py
git commit -m "Add integration test for schedule persistence across app restarts"
```

---

### Task 12: Frontend `putJson` helper

**Files:**
- Modify: `dashboard/src/lib/api.js:60-67` (insert after `deleteJson`)

- [ ] **Step 1: Add the helper**

In `dashboard/src/lib/api.js`, directly after:

```javascript
export async function deleteJson(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: authHeaders()
  });

  return parseJsonResponse(response);
}
```

add:

```javascript
export async function putJson(path, data = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: authHeaders({
      "Content-Type": "application/json"
    }),
    body: JSON.stringify(data)
  });

  return parseJsonResponse(response);
}
```

- [ ] **Step 2: Verify the dashboard still builds**

Run: `cd dashboard && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
cd dashboard
git add src/lib/api.js
git commit -m "Add putJson helper for schedule edit requests"
```

---

### Task 13: Frontend edit UI in `SchedulePanel.jsx`

**Files:**
- Modify: `dashboard/src/components/SchedulePanel.jsx` (full rewrite)

- [ ] **Step 1: Replace the file contents**

Replace the entire contents of `dashboard/src/components/SchedulePanel.jsx` with:

```jsx
import { useState } from "react";
import { deleteJson, postJson, putJson } from "../lib/api";
import Card from "./Card";

const PRIORITIES = ["low", "medium", "high"];
const TYPES = ["class", "meeting", "study", "assignment", "test", "quiz", "personal"];

const EMPTY_FORM = {
  title: "",
  date: "",
  time: "",
  type: "study",
  priority: "medium"
};

export default function SchedulePanel({ schedule, onScheduleChanged }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState(null);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function startEdit(item) {
    setEditingId(item.id);
    setForm({
      title: item.title || "",
      date: item.date || "",
      time: item.time || "",
      type: item.type || "study",
      priority: item.priority || "medium"
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function submitForm(event) {
    event.preventDefault();
    if (!form.title.trim()) return;

    const payload = {
      ...form,
      title: form.title.trim(),
      date: form.date || null,
      time: form.time || null
    };

    setSaving(true);
    try {
      if (editingId) {
        await putJson(`/api/schedule/${editingId}`, payload);
      } else {
        await postJson("/api/schedule", payload);
      }
      setEditingId(null);
      setForm(EMPTY_FORM);
      await onScheduleChanged?.();
    } finally {
      setSaving(false);
    }
  }

  async function removeItem(itemId) {
    await deleteJson(`/api/schedule/${itemId}`);
    if (editingId === itemId) {
      cancelEdit();
    }
    await onScheduleChanged?.();
  }

  return (
    <Card title="Upcoming Schedule">
      <form onSubmit={submitForm} className="mb-5 rounded-[1.75rem] border border-white/20 bg-white/[0.08] p-4">
        <p className="mb-3 text-sm font-medium text-slate-200">
          {editingId ? "Edit schedule item" : "Add a new schedule item"}
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          <input
            className="input-glass rounded-2xl px-3 py-2 text-sm md:col-span-2"
            placeholder="e.g. Deep Learning revision"
            value={form.title}
            onChange={(event) => updateField("title", event.target.value)}
          />
          <input
            type="date"
            className="input-glass rounded-2xl px-3 py-2 text-sm"
            value={form.date}
            onChange={(event) => updateField("date", event.target.value)}
          />
          <input
            type="time"
            className="input-glass rounded-2xl px-3 py-2 text-sm"
            value={form.time}
            onChange={(event) => updateField("time", event.target.value)}
          />
          <select
            className="input-glass rounded-2xl px-3 py-2 text-sm"
            value={form.type}
            onChange={(event) => updateField("type", event.target.value)}
          >
            {TYPES.map((type) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
          <select
            className="input-glass rounded-2xl px-3 py-2 text-sm"
            value={form.priority}
            onChange={(event) => updateField("priority", event.target.value)}
          >
            {PRIORITIES.map((priority) => (
              <option key={priority} value={priority}>{priority} priority</option>
            ))}
          </select>
        </div>
        <div className="mt-3 flex gap-2">
          <button
            type="submit"
            disabled={saving}
            className="btn-primary px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
          >
            {saving ? "Saving..." : editingId ? "Save changes" : "Add Schedule Item"}
          </button>
          {editingId ? (
            <button
              type="button"
              onClick={cancelEdit}
              className="rounded-full border border-white/20 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-slate-200 hover:bg-white/[0.15]"
            >
              Cancel
            </button>
          ) : null}
        </div>
      </form>

      <div className="space-y-3">
        {schedule.length === 0 ? (
          <p className="text-slate-300/75">No schedule items loaded.</p>
        ) : (
          schedule.map((item) => (
            <div key={item.id} className="flex items-start justify-between gap-3 rounded-2xl border border-white/20 bg-white/[0.08] p-3">
              <div>
                <p className="font-semibold text-white">{item.title}</p>
                <p className="text-sm capitalize text-slate-300/75">
                  {item.formatted_date || item.date || "No date"} · {item.time || "No time"} · {item.type || "schedule"} · {item.priority} priority
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  onClick={() => startEdit(item)}
                  className="rounded-full border border-sky-300/30 bg-sky-400/10 px-3 py-1.5 text-sm font-medium text-sky-100 hover:bg-sky-400/20"
                >
                  Edit
                </button>
                <button
                  onClick={() => removeItem(item.id)}
                  className="rounded-full border border-rose-300/30 bg-rose-400/10 px-3 py-1.5 text-sm font-medium text-rose-100 hover:bg-rose-400/20"
                >
                  Remove
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
```

- [ ] **Step 2: Verify the dashboard still builds**

Run: `cd dashboard && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 3: Manual UI check**

Run: `cd dashboard && npm run dev` (and `cd backend && PYTHONPATH=. venv/bin/python main.py` in a separate terminal), then in the browser: log in, add a schedule item, click "Edit" on it, change the time, click "Save changes", and confirm the row updates without creating a duplicate. Click "Remove" to confirm deletion still works.
Expected: edit flow updates the existing row in place; no duplicate rows; remove still works.

- [ ] **Step 4: Commit**

```bash
cd dashboard
git add src/components/SchedulePanel.jsx
git commit -m "Add edit mode to SchedulePanel for full schedule CRUD"
```

---

### Task 14: Full regression pass

**Files:** none (verification only)

- [ ] **Step 1: Run the entire backend test suite**

Run: `cd backend && PYTHONPATH=. venv/bin/pytest -q`
Expected: all tests pass, including the pre-existing suite (`test_dashboard_productivity_api.py`, `test_intent_classifier.py`, etc.) and the new `test_schedule_module.py`.

- [ ] **Step 2: Run the dashboard production build**

Run: `cd dashboard && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 3: Confirm action plan checklist items for the Schedule section**

Cross-check against `docs/action_plan.md` lines 120-142 ("Vanness — Schedule") and the "Pre-Submission Checklist" (lines 175-186):
- [ ] Schedule survives backend restart — covered by Task 5 + Task 11
- [ ] Full CRUD (create/read/update/delete) — covered by Task 3, Task 8
- [ ] 30-minute and at-time notifications — covered by Task 4, Task 9
- [ ] No database locking under concurrent access — covered by Task 1, Task 10

- [ ] **Step 4: No commit needed for this task (verification only)**
