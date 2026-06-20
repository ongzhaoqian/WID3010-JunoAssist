from __future__ import annotations
import sqlite3
from datetime import datetime, timedelta
from typing import Any


class CalendarService:
    def __init__(self, db_path: str = "juno_assist.db") -> None:
        self.db_path = db_path
        self.current_user_id: int | None = None
        self._initialise()

    def set_active_user(self, user_id: int | None) -> None:
        self.current_user_id = int(user_id) if user_id else None

    def _resolve_user_id(self, user_id: int | None = None) -> int | None:
        return int(user_id) if user_id else self.current_user_id

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

    def _initialise(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT NOT NULL,
                    date TEXT,
                    time TEXT,
                    type TEXT,
                    priority TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT NOT NULL,
                    date TEXT,
                    time TEXT,
                    type TEXT DEFAULT 'reminder',
                    priority TEXT,
                    completed INTEGER DEFAULT 0
                )
                """
            )
            self._migrate_schedule_columns(conn)
            self._migrate_reminder_columns(conn)

    def reset_runtime_data(self) -> None:
        """Clear reminder rows for a fresh backend session.

        Schedule items intentionally persist across restarts (action plan
        requirement); only reminders are reset here.
        """
        with self._connect() as conn:
            conn.execute("DELETE FROM reminders")
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'reminders'")

    def _migrate_schedule_columns(self, conn: sqlite3.Connection) -> None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(schedule_items)").fetchall()}
        if "user_id" not in columns:
            conn.execute("ALTER TABLE schedule_items ADD COLUMN user_id INTEGER")
        if "notified_30" not in columns:
            conn.execute("ALTER TABLE schedule_items ADD COLUMN notified_30 INTEGER DEFAULT 0")
        if "notified_due" not in columns:
            conn.execute("ALTER TABLE schedule_items ADD COLUMN notified_due INTEGER DEFAULT 0")
        if "completed" not in columns:
            conn.execute("ALTER TABLE schedule_items ADD COLUMN completed INTEGER DEFAULT 0")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_items_user ON schedule_items(user_id, date, time, id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_items_notify ON schedule_items(notified_30, notified_due)")

    def _migrate_reminder_columns(self, conn: sqlite3.Connection) -> None:
        """Bring old reminder tables up to the schedule-like schema.

        Earlier builds stored reminders as title/due_date/due_time/priority only.
        The dashboard and speech layer now expect the same logical columns as
        schedules: title, date, time, type, priority. Existing due_* values are
        copied into the new fields when present so old reminders remain visible.
        """
        columns = {row[1] for row in conn.execute("PRAGMA table_info(reminders)").fetchall()}
        required = {
            "date": "TEXT",
            "time": "TEXT",
            "type": "TEXT DEFAULT 'reminder'",
            "priority": "TEXT",
            "completed": "INTEGER DEFAULT 0",
            "user_id": "INTEGER",
        }
        for column, definition in required.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE reminders ADD COLUMN {column} {definition}")

        refreshed_columns = {row[1] for row in conn.execute("PRAGMA table_info(reminders)").fetchall()}
        if "due_date" in refreshed_columns:
            conn.execute("UPDATE reminders SET date = COALESCE(date, due_date)")
        if "due_time" in refreshed_columns:
            conn.execute("UPDATE reminders SET time = COALESCE(time, due_time)")
        conn.execute("UPDATE reminders SET type = COALESCE(NULLIF(type, ''), 'reminder')")
        conn.execute("UPDATE reminders SET priority = COALESCE(NULLIF(priority, ''), 'medium')")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id, completed, date, time, id)")

    def get_today_schedule(self, user_id: int | None = None) -> list[dict[str, Any]]:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, title, date, time, type, priority, completed FROM schedule_items
                WHERE user_id = ?
                ORDER BY COALESCE(date, ''), COALESCE(time, ''), id
                """,
                (resolved_user_id,),
            ).fetchall()

        return [self._schedule_row_to_dict(row) for row in rows]

    def get_upcoming_deadlines(self, user_id: int | None = None) -> list[dict[str, Any]]:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, title, date, time, type, priority, completed
                FROM schedule_items
                WHERE user_id = ? AND type IN ('assignment', 'test', 'quiz', 'study')
                ORDER BY COALESCE(date, ''), COALESCE(time, ''), id
                LIMIT 5
                """,
                (resolved_user_id,),
            ).fetchall()

        return [self._schedule_row_to_dict(row) for row in rows]

    def add_schedule_item(
        self,
        title: str,
        date: str | None = None,
        time: str | None = None,
        type: str = "study",
        priority: str = "medium",
        user_id: int | None = None,
    ) -> dict[str, Any]:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            raise ValueError("A logged-in user is required to add a schedule item.")
        title = title.strip()
        item_type = (type or "study").strip().lower()
        priority = (priority or "medium").strip().lower()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO schedule_items (user_id, title, date, time, type, priority)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (resolved_user_id, title, date, time, item_type, priority),
            )
            item_id = cursor.lastrowid

        return {
            "id": item_id,
            "title": title,
            "date": date,
            "formatted_date": self.format_display_date(date),
            "time": time,
            "type": item_type,
            "priority": priority,
            "completed": False,
            "user_id": resolved_user_id,
        }

    def update_schedule_item(
        self,
        item_id: int,
        *,
        title: str | None = None,
        date: str | None = None,
        time: str | None = None,
        type: str | None = None,
        priority: str | None = None,
        completed: bool | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any] | None:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT title, date, time, type, priority, completed FROM schedule_items WHERE id = ? AND user_id = ?",
                (item_id, resolved_user_id),
            ).fetchone()
            if row is None:
                return None

            updated_title = title.strip() if title is not None else row[0]
            updated_date = date if date is not None else row[1]
            updated_time = time if time is not None else row[2]
            updated_type = (type.strip().lower() if type else row[3]) if type is not None else row[3]
            updated_priority = (priority.strip().lower() if priority else row[4]) if priority is not None else row[4]
            updated_completed = completed if completed is not None else bool(row[5])

            conn.execute(
                """
                UPDATE schedule_items
                SET title = ?, date = ?, time = ?, type = ?, priority = ?, completed = ?,
                    notified_30 = 0, notified_due = 0
                WHERE id = ? AND user_id = ?
                """,
                (
                    updated_title, updated_date, updated_time, updated_type, updated_priority,
                    1 if updated_completed else 0, item_id, resolved_user_id,
                ),
            )

        return {
            "id": item_id,
            "title": updated_title,
            "date": updated_date,
            "formatted_date": self.format_display_date(updated_date),
            "time": updated_time,
            "type": updated_type,
            "priority": updated_priority,
            "completed": updated_completed,
            "user_id": resolved_user_id,
        }

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
                  AND completed = 0
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

            due_trigger = due_at - tolerance
            is_due_now = now >= due_trigger

            if not notified_due and is_due_now:
                due_items.append({**base, "stage": "due", "remaining_minutes": 0})
            elif not is_due_now and not notified_30 and now >= (due_at - timedelta(minutes=30) - tolerance):
                # Once the due stage's own window has opened, the 30-minute
                # warning no longer applies (covers "due now" and "already
                # overdue" items) - only fire one stage per tick. For items
                # that genuinely had less than 30 minutes of lead time at
                # creation, speak the actual remaining time instead of a
                # fixed "30 minutes" that would be inaccurate.
                remaining_minutes = max(1, round((due_at - now).total_seconds() / 60))
                due_items.append({**base, "stage": "30", "remaining_minutes": remaining_minutes})

        return due_items

    def mark_notified(self, item_id: int, stage: str) -> None:
        column = "notified_30" if stage == "30" else "notified_due"
        with self._connect() as conn:
            conn.execute(f"UPDATE schedule_items SET {column} = 1 WHERE id = ?", (item_id,))

    def delete_schedule_item(self, item_id: int, user_id: int | None = None) -> bool:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return False
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM schedule_items WHERE id = ? AND user_id = ?", (item_id, resolved_user_id))
            return cursor.rowcount > 0

    def add_reminder(
        self,
        title: str,
        date: str | None = None,
        time: str | None = None,
        type: str = "reminder",
        priority: str = "medium",
        user_id: int | None = None,
    ) -> dict[str, Any]:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            raise ValueError("A logged-in user is required to add a reminder.")
        title = title.strip()
        item_type = (type or "reminder").strip().lower()
        priority = (priority or "medium").strip().lower()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reminders (user_id, title, date, time, type, priority, completed)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (resolved_user_id, title, date, time, item_type, priority),
            )
            reminder_id = cursor.lastrowid

        return {
            "id": reminder_id,
            "title": title,
            "date": date,
            "formatted_date": self.format_display_date(date),
            "time": time,
            "type": item_type,
            "priority": priority,
            "completed": False,
            # Backwards-compatible aliases for older dashboard/test code.
            "due_date": date,
            "due_time": time,
            "user_id": resolved_user_id,
        }

    def list_reminders(self, include_completed: bool = True, user_id: int | None = None) -> list[dict[str, Any]]:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return []
        completed_filter = "" if include_completed else "AND completed = 0"
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, title, date, time, type, priority, completed
                FROM reminders
                WHERE user_id = ? {completed_filter}
                ORDER BY completed ASC, COALESCE(date, ''), COALESCE(time, ''), id
                """,
                (resolved_user_id,),
            ).fetchall()

        return [self._reminder_row_to_dict(row) for row in rows]

    def delete_reminder(self, item_id: int, user_id: int | None = None) -> bool:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return False
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM reminders WHERE id = ? AND user_id = ?", (item_id, resolved_user_id))
            return cursor.rowcount > 0

    def set_reminder_completed(self, item_id: int, completed: bool = True, user_id: int | None = None) -> dict[str, Any] | None:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return None
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE reminders SET completed = ? WHERE id = ? AND user_id = ?",
                (1 if completed else 0, item_id, resolved_user_id),
            )
            if cursor.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT id, title, date, time, type, priority, completed FROM reminders WHERE id = ? AND user_id = ?",
                (item_id, resolved_user_id),
            ).fetchone()

        return self._reminder_row_to_dict(row)

    @staticmethod
    def format_display_date(value: str | None) -> str | None:
        if not value:
            return None
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return value
        return f"{parsed.day} {parsed.strftime('%B')}, {parsed.year}"

    @classmethod
    def _schedule_row_to_dict(cls, row) -> dict[str, Any]:
        return {
            "id": row[0],
            "title": row[1],
            "date": row[2],
            "formatted_date": cls.format_display_date(row[2]),
            "time": row[3],
            "type": row[4],
            "priority": row[5],
            "completed": bool(row[6]),
        }

    @classmethod
    def _reminder_row_to_dict(cls, row) -> dict[str, Any]:
        date = row[2]
        time_value = row[3]
        return {
            "id": row[0],
            "title": row[1],
            "date": date,
            "formatted_date": cls.format_display_date(date),
            "time": time_value,
            "type": row[4] or "reminder",
            "priority": row[5] or "medium",
            "completed": bool(row[6]),
            # Backwards-compatible aliases for old frontend/API consumers.
            "due_date": date,
            "due_time": time_value,
        }
