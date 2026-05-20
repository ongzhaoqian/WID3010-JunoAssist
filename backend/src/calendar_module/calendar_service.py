from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any


class CalendarService:
    def __init__(self, db_path: str = "juno_assist.db") -> None:
        self.db_path = db_path
        self._initialise()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialise(self) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS schedule_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    date TEXT,
                    time TEXT,
                    type TEXT,
                    priority TEXT
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    due_date TEXT,
                    due_time TEXT,
                    priority TEXT,
                    completed INTEGER DEFAULT 0
                )
                '''
            )

    def seed_from_json_if_empty(self, json_path: str) -> None:
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM schedule_items").fetchone()[0]
            if count > 0:
                return

        path = Path(json_path)
        if not path.exists():
            return

        items: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        with self._connect() as conn:
            conn.executemany(
                '''
                INSERT INTO schedule_items (title, date, time, type, priority)
                VALUES (:title, :date, :time, :type, :priority)
                ''',
                items
            )

    def get_today_schedule(self) -> list[dict[str, Any]]:
        # For demo purposes, return all seeded records.
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, title, date, time, type, priority FROM schedule_items ORDER BY date, time"
            ).fetchall()

        return [
            {
                "id": row[0],
                "title": row[1],
                "date": row[2],
                "time": row[3],
                "type": row[4],
                "priority": row[5],
            }
            for row in rows
        ]

    def get_upcoming_deadlines(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT id, title, date, time, type, priority
                FROM schedule_items
                WHERE type IN ('assignment', 'test', 'quiz', 'study')
                ORDER BY date, time
                LIMIT 5
                '''
            ).fetchall()

        return [
            {
                "id": row[0],
                "title": row[1],
                "date": row[2],
                "time": row[3],
                "type": row[4],
                "priority": row[5],
            }
            for row in rows
        ]

    def add_reminder(self, title: str, due_date: str | None, due_time: str | None, priority: str) -> dict:
        with self._connect() as conn:
            cursor = conn.execute(
                '''
                INSERT INTO reminders (title, due_date, due_time, priority)
                VALUES (?, ?, ?, ?)
                ''',
                (title, due_date, due_time, priority)
            )
            reminder_id = cursor.lastrowid

        return {
            "id": reminder_id,
            "title": title,
            "due_date": due_date,
            "due_time": due_time,
            "priority": priority,
            "completed": False,
        }

    def list_reminders(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT id, title, due_date, due_time, priority, completed
                FROM reminders
                ORDER BY due_date, due_time
                '''
            ).fetchall()

        return [
            {
                "id": row[0],
                "title": row[1],
                "due_date": row[2],
                "due_time": row[3],
                "priority": row[4],
                "completed": bool(row[5]),
            }
            for row in rows
        ]
