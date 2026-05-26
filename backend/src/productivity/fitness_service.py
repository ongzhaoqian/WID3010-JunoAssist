from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

FITNESS_GAME_URL = "https://67speed.com/"
DEFAULT_GAME_MET = 4.0


class FitnessService:
    """User-scoped persistence and calorie estimation for the JUNO 6-7 game."""

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
                CREATE TABLE IF NOT EXISTS fitness_profile (
                    user_id INTEGER PRIMARY KEY,
                    height_m REAL,
                    weight_kg REAL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._migrate_profile_table(conn)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fitness_game_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    score_67 INTEGER NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    height_m REAL,
                    weight_kg REAL,
                    calories_burned REAL,
                    source TEXT NOT NULL DEFAULT 'manual',
                    created_at TEXT NOT NULL
                )
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(fitness_game_sessions)").fetchall()}
            if "user_id" not in columns:
                conn.execute("ALTER TABLE fitness_game_sessions ADD COLUMN user_id INTEGER")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fitness_sessions_user ON fitness_game_sessions(user_id, id)")

    def _migrate_profile_table(self, conn: sqlite3.Connection) -> None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(fitness_profile)").fetchall()}
        if "user_id" in columns:
            return
        # Older builds used id=1 as a singleton profile. Convert the table to a
        # user-scoped profile table if that schema is encountered.
        conn.execute("ALTER TABLE fitness_profile RENAME TO fitness_profile_legacy")
        conn.execute(
            """
            CREATE TABLE fitness_profile (
                user_id INTEGER PRIMARY KEY,
                height_m REAL,
                weight_kg REAL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute("DROP TABLE fitness_profile_legacy")

    def reset_runtime_data(self) -> None:
        """Clear all user-scoped fitness rows for a fresh backend run."""
        with self._connect() as conn:
            conn.execute("DELETE FROM fitness_profile")
            conn.execute("DELETE FROM fitness_game_sessions")
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'fitness_game_sessions'")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _estimate_duration_seconds(score_67: int, duration_seconds: int | None = None) -> int:
        if duration_seconds is not None and duration_seconds > 0:
            return max(5, min(600, int(duration_seconds)))
        return max(20, min(180, round(max(0, int(score_67)) * 1.1)))

    @staticmethod
    def estimate_calories(weight_kg: float | None, duration_seconds: int, met: float = DEFAULT_GAME_MET) -> float | None:
        if weight_kg is None or weight_kg <= 0 or duration_seconds <= 0:
            return None
        duration_minutes = duration_seconds / 60.0
        calories = met * 3.5 * float(weight_kg) / 200.0 * duration_minutes
        return round(calories, 2)

    def get_profile(self, user_id: int | None = None) -> dict[str, Any]:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return {"height_m": None, "weight_kg": None, "updated_at": None, "complete": False}
        with self._connect() as conn:
            row = conn.execute(
                "SELECT height_m, weight_kg, updated_at FROM fitness_profile WHERE user_id = ?",
                (resolved_user_id,),
            ).fetchone()
        if not row:
            return {"height_m": None, "weight_kg": None, "updated_at": None, "complete": False, "user_id": resolved_user_id}
        return {
            "height_m": row[0],
            "weight_kg": row[1],
            "updated_at": row[2],
            "complete": row[0] is not None and row[1] is not None,
            "user_id": resolved_user_id,
        }

    def save_profile(self, height_m: float | None, weight_kg: float | None, user_id: int | None = None) -> dict[str, Any]:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            raise ValueError("A logged-in user is required to save a fitness profile.")
        now = self._now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO fitness_profile (user_id, height_m, weight_kg, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    height_m = excluded.height_m,
                    weight_kg = excluded.weight_kg,
                    updated_at = excluded.updated_at
                """,
                (resolved_user_id, height_m, weight_kg, now),
            )
        return self.get_profile(user_id=resolved_user_id)

    def add_session(self, score_67: int, source: str = "manual", duration_seconds: int | None = None, user_id: int | None = None) -> dict[str, Any]:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            raise ValueError("A logged-in user is required to save a fitness session.")
        score = max(0, int(score_67))
        duration = self._estimate_duration_seconds(score, duration_seconds)
        profile = self.get_profile(user_id=resolved_user_id)
        height_m = profile.get("height_m")
        weight_kg = profile.get("weight_kg")
        calories = self.estimate_calories(weight_kg, duration)
        created_at = self._now_iso()
        source = (source or "manual").strip().lower()[:40] or "manual"
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO fitness_game_sessions
                    (user_id, score_67, duration_seconds, height_m, weight_kg, calories_burned, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (resolved_user_id, score, duration, height_m, weight_kg, calories, source, created_at),
            )
            session_id = cursor.lastrowid
        return self._session_to_dict((session_id, score, duration, height_m, weight_kg, calories, source, created_at), profile)

    def list_sessions(self, limit: int = 20, user_id: int | None = None) -> list[dict[str, Any]]:
        resolved_user_id = self._resolve_user_id(user_id)
        if resolved_user_id is None:
            return []
        limit = max(1, min(100, int(limit)))
        profile = self.get_profile(user_id=resolved_user_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, score_67, duration_seconds, height_m, weight_kg, calories_burned, source, created_at
                FROM fitness_game_sessions
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (resolved_user_id, limit),
            ).fetchall()
        return [self._session_to_dict(row, profile) for row in rows]

    def stats(self, scope: str = "latest", user_id: int | None = None) -> dict[str, Any]:
        resolved_user_id = self._resolve_user_id(user_id)
        scope = (scope or "latest").strip().lower()
        if scope not in {"latest", "cumulative"}:
            scope = "latest"
        profile = self.get_profile(user_id=resolved_user_id)
        if resolved_user_id is None:
            rows = []
        else:
            with self._connect() as conn:
                if scope == "latest":
                    rows = conn.execute(
                        """
                        SELECT id, score_67, duration_seconds, height_m, weight_kg, calories_burned, source, created_at
                        FROM fitness_game_sessions
                        WHERE user_id = ?
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (resolved_user_id,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT id, score_67, duration_seconds, height_m, weight_kg, calories_burned, source, created_at
                        FROM fitness_game_sessions
                        WHERE user_id = ?
                        ORDER BY id ASC
                        """,
                        (resolved_user_id,),
                    ).fetchall()
        sessions = [self._session_to_dict(row, profile) for row in rows]
        total_score = sum(int(session["score_67"] or 0) for session in sessions)
        calories_values = [session.get("calories_burned") for session in sessions]
        total_calories = sum(float(value) for value in calories_values if value is not None)
        return {
            "scope": scope,
            "session_count": len(sessions),
            "score_67": total_score,
            "calories_burned": round(total_calories, 2) if calories_values and any(value is not None for value in calories_values) else None,
            "latest_session": sessions[0] if sessions else None,
            "sessions": sessions,
            "profile": profile,
            "needs_profile": not bool(profile.get("weight_kg")),
            "calorie_formula": "Estimated kcal = MET × 3.5 × weight_kg ÷ 200 × duration_minutes; MET defaults to 4.0 for this light fitness game.",
            "game_url": FITNESS_GAME_URL,
        }

    def _session_to_dict(self, row, profile: dict[str, Any]) -> dict[str, Any]:
        session_id, score, duration, height_m, weight_kg, calories, source, created_at = row
        effective_weight = weight_kg if weight_kg is not None else profile.get("weight_kg")
        effective_calories = calories if calories is not None else self.estimate_calories(effective_weight, int(duration or 0))
        return {
            "id": session_id,
            "score_67": int(score or 0),
            "duration_seconds": int(duration or 0),
            "height_m": height_m if height_m is not None else profile.get("height_m"),
            "weight_kg": effective_weight,
            "calories_burned": effective_calories,
            "source": source,
            "created_at": created_at,
            "game_url": FITNESS_GAME_URL,
        }
