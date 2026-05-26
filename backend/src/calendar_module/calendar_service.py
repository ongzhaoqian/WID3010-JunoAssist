from __future__ import annotations
import sqlite3
from datetime import datetime
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
        return sqlite3.connect(self.db_path)

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
        """Clear all user-scoped schedule/reminder rows for a fresh backend session."""
        with self._connect() as conn:
            conn.execute("DELETE FROM schedule_items")
            conn.execute("DELETE FROM reminders")
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('schedule_items', 'reminders')")

    def _migrate_schedule_columns(self, conn: sqlite3.Connection) -> None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(schedule_items)").fetchall()}
        if "user_id" not in columns:
            conn.execute("ALTER TABLE schedule_items ADD COLUMN user_id INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_items_user ON schedule_items(user_id, date, time, id)")

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
                SELECT id, title, date, time, type, priority FROM schedule_items
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
                SELECT id, title, date, time, type, priority
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
            "user_id": resolved_user_id,
        }

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

    def set_reminder_completed(self, item_id: int, completed: bool = True, user_id: int | None = None) -> bool:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return False
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE reminders SET completed = ? WHERE id = ? AND user_id = ?",
                (1 if completed else 0, item_id, resolved_user_id),
            )
            return cursor.rowcount > 0

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
