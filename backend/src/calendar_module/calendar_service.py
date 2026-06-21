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
        columns = {row[1] for row in conn.execute("PRAGMA table_info(reminders)").fetchall()}
        required = {
            "date": "TEXT",
            "time": "TEXT",
            "type": "TEXT DEFAULT 'reminder'",
            "priority": "TEXT",
            "completed": "INTEGER DEFAULT 0",
            "user_id": "INTEGER",
            "notified_30": "INTEGER DEFAULT 0",
            "notified_due": "INTEGER DEFAULT 0",
        }
        for column, definition in required.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE reminders ADD COLUMN {column} {definition}")

        # Carry over from the old column name if it exists from a prior version.
        refreshed_columns = {row[1] for row in conn.execute("PRAGMA table_info(reminders)").fetchall()}
        if "notified_30min" in refreshed_columns:
            conn.execute("UPDATE reminders SET notified_30 = COALESCE(notified_30, notified_30min)")

        if "due_date" in refreshed_columns:
            conn.execute("UPDATE reminders SET date = COALESCE(date, due_date)")
        if "due_time" in refreshed_columns:
            conn.execute("UPDATE reminders SET time = COALESCE(time, due_time)")
        conn.execute("UPDATE reminders SET type = COALESCE(NULLIF(type, ''), 'reminder')")
        conn.execute("UPDATE reminders SET priority = COALESCE(NULLIF(priority, ''), 'medium')")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id, completed, date, time, id)")

    def get_today_schedule(
        self, user_id: int | None = None, include_completed: bool = True
    ) -> list[dict[str, Any]]:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return []
        completed_filter = "" if include_completed else "AND completed = 0"
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, title, date, time, type, priority, completed FROM schedule_items
                WHERE user_id = ? {completed_filter}
                ORDER BY COALESCE(date, ''), COALESCE(time, ''), id
                """,
                (resolved_user_id,),
            ).fetchall()

        return [self._schedule_row_to_dict(row) for row in rows]

    def get_schedule_item(self, item_id: int, user_id: int | None = None) -> dict[str, Any] | None:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, title, date, time, type, priority, completed FROM schedule_items WHERE id = ? AND user_id = ?",
                (item_id, resolved_user_id),
            ).fetchone()
        return self._schedule_row_to_dict(row) if row else None

    def get_upcoming_deadlines(self, user_id: int | None = None) -> list[dict[str, Any]]:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, title, date, time, type, priority, completed
                FROM schedule_items
                WHERE user_id = ? 
                AND type IN ('assignment', 'test', 'quiz', 'study')
                AND (completed = 0 OR completed IS NULL)  -- FIXED: Excludes completed items
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

    # Below this many seconds of lead time, firing a separate "30 minutes
    # before" notification would land essentially back-to-back with the due
    # notification, so it is skipped entirely and the item just waits for
    # the due-time stage instead.
    SHORT_LEAD_SECONDS = 30

    # How close the actual remaining time has to be to a round minute mark
    # (e.g. exactly 1 minute, exactly 10 minutes) before it's spoken as that
    # exact number rather than qualified with "about".
    REMAINING_EXACT_TOLERANCE_SECONDS = 5

    @staticmethod
    def _format_remaining(seconds: float) -> tuple[int, str]:
        """Whole minutes remaining plus a human label, with a "less than a
        minute" phrasing for the 30s-60s band instead of rounding to 0 or 1.

        For 60s and up, the minute count is rounded to the nearest minute,
        and prefixed with "about" unless the actual remaining time is within
        REMAINING_EXACT_TOLERANCE_SECONDS of that exact minute mark - e.g.
        75 seconds rounds to "1 minute" but is 15s off the 60s mark, so it's
        spoken as "about 1 minute" rather than implying it's exactly 1:00."""
        seconds = max(0.0, seconds)
        if seconds < 60:
            return 0, "less than a minute"
        minutes = round(seconds / 60)
        word = "1 minute" if minutes == 1 else f"{minutes} minutes"
        is_exact = abs(seconds - minutes * 60) <= CalendarService.REMAINING_EXACT_TOLERANCE_SECONDS
        return minutes, (word if is_exact else f"about {word}")

    @staticmethod
    def _format_overdue(seconds: float) -> str:
        """Human label for how long an item has been overdue, scaling the
        unit up from minutes to hours and days as it grows. Sub-minute
        overdue durations are phrased as "less than a minute" rather than
        being called out in seconds."""
        total = int(round(abs(seconds)))
        if total < 60:
            return "less than a minute"
        minutes = total // 60
        if minutes < 60:
            return f"{minutes} minute" + ("" if minutes == 1 else "s")
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour" + ("" if hours == 1 else "s")
        days = hours // 24
        return f"{days} day" + ("" if days == 1 else "s")

    def get_items_needing_notification(
        self, now: datetime, table_name: str, tolerance_seconds: float = 15.0
    ) -> list[dict[str, Any]]:
        """Return every (item, stage) pair currently due for a spoken notification,
        for either 'schedule_items' or 'reminders' — both tables share the same
        date/time/notified_30/notified_due shape, so one method covers both.

        Each item gets at most one of "30" (upcoming) or "due" (due-now /
        overdue) per call - the two are mutually exclusive based on how much
        lead time is left, which also covers four creation-time cases:
          - created >30 min before due: "30" fires when lead crosses the
            30-minute mark, "due" fires later at the due time.
          - created with 30s-30min of lead: "30" fires immediately with the
            real remaining time (e.g. "12 minutes", or "less than a minute"
            for the 30s-60s band); "due" still fires later at the due time.
          - created with <=30s of lead (SHORT_LEAD_SECONDS): "30" is skipped
            entirely; only "due" fires, once the due time is reached.
          - created at or after the due time: only "due" fires immediately,
            tagged overdue=True with an overdue_label when already overdue.

        The trigger condition is one-sided (now >= target - tolerance, with no
        upper bound) rather than a tight window. This means a delayed check tick
        still eventually surfaces every pending notification exactly once; the
        notified_30/notified_due flags (set via mark_notified) are what make each
        stage fire only once per item.
        """
        if table_name not in {"schedule_items", "reminders"}:
            raise ValueError(f"Unsupported table for notifications: {table_name}")

        # Both schedule_items and reminders carry a completed column (see the
        # migrations above) and neither should fire notifications once done.
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, user_id, title, date, time, type, priority, notified_30, notified_due
                FROM {table_name}
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
            lead_seconds = (due_at - now).total_seconds()

            is_due_now = lead_seconds <= tolerance_seconds
            if not notified_due and is_due_now:
                overdue = lead_seconds < -tolerance_seconds
                entry = {**base, "stage": "due", "overdue": overdue}
                if overdue:
                    entry["overdue_label"] = self._format_overdue(lead_seconds)
                due_items.append(entry)

            is_upcoming_window = tolerance_seconds < lead_seconds <= (30 * 60 + tolerance_seconds)
            if not notified_30 and is_upcoming_window and lead_seconds > self.SHORT_LEAD_SECONDS:
                remaining_minutes, remaining_label = self._format_remaining(lead_seconds)
                due_items.append({
                    **base,
                    "stage": "30",
                    "remaining_minutes": remaining_minutes,
                    "remaining_label": remaining_label,
                })
        return due_items


    def mark_notified(self, item_id: int, stage: str, table_name: str) -> None:
        if table_name not in {"schedule_items", "reminders"}:
            raise ValueError(f"Unsupported table for notifications: {table_name}")
        column = "notified_30" if stage == "30" else "notified_due"
        with self._connect() as conn:
            conn.execute(f"UPDATE {table_name} SET {column} = 1 WHERE id = ?", (item_id,))
            
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
    def update_reminder(
        self,
        item_id: int,
        title: str,
        date: str | None = None,
        time: str | None = None,
        type: str = "reminder",
        priority: str = "medium",
        completed: bool | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any] | None:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            raise ValueError("A logged-in user is required to update a reminder.")

        with self._connect() as conn:
            row = conn.execute(
                "SELECT title, date, time, type, priority, completed FROM reminders WHERE id = ? AND user_id = ?",
                (item_id, resolved_user_id),
            ).fetchone()
            if row is None:
                return None

            # Mirrors update_schedule_item: any field left as None keeps the
            # existing stored value instead of being overwritten/cleared, so a
            # partial update (e.g. only toggling completed) can't accidentally
            # null out date/time and silently drop the item from notifications.
            updated_title = title.strip() if title is not None else row[0]
            updated_date = date if date is not None else row[1]
            updated_time = time if time is not None else row[2]
            updated_type = (type.strip().lower() if type else row[3]) if type is not None else row[3]
            updated_priority = (priority.strip().lower() if priority else row[4]) if priority is not None else row[4]
            updated_completed = completed if completed is not None else bool(row[5])

            conn.execute(
                """
                UPDATE reminders
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
            "due_date": updated_date,
            "due_time": updated_time,
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

    def get_reminder(self, item_id: int, user_id: int | None = None) -> dict[str, Any] | None:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, title, date, time, type, priority, completed FROM reminders WHERE id = ? AND user_id = ?",
                (item_id, resolved_user_id),
            ).fetchone()
        return self._reminder_row_to_dict(row) if row else None

    def delete_reminder(self, item_id: int, user_id: int | None = None) -> bool:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return False
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM reminders WHERE id = ? AND user_id = ?", (item_id, resolved_user_id))
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
