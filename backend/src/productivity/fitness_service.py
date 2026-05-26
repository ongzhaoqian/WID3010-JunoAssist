from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

FITNESS_GAME_URL = "https://67speed.com/"
DEFAULT_GAME_MET = 4.0


class FitnessService:
    """Persistence and calorie estimation for the JUNO 6-7 fitness game.

    The game runs on a third-party page, so the backend stores the score passed
    by the dashboard. Calorie output is a rough activity estimate, not a medical
    or fitness prescription.
    """

    def __init__(self, db_path: str = "juno_assist.db") -> None:
        self.db_path = db_path
        self._initialise()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialise(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fitness_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    height_m REAL,
                    weight_kg REAL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fitness_game_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _estimate_duration_seconds(score_67: int, duration_seconds: int | None = None) -> int:
        if duration_seconds is not None and duration_seconds > 0:
            return max(5, min(600, int(duration_seconds)))
        # One 6-7 motion is usually very short. Use a conservative activity
        # window so the score affects the estimate but does not exaggerate it.
        return max(20, min(180, round(max(0, int(score_67)) * 1.1)))

    @staticmethod
    def estimate_calories(weight_kg: float | None, duration_seconds: int, met: float = DEFAULT_GAME_MET) -> float | None:
        if weight_kg is None or weight_kg <= 0 or duration_seconds <= 0:
            return None
        duration_minutes = duration_seconds / 60.0
        # Standard MET formula: kcal/min = MET * 3.5 * body mass kg / 200.
        calories = met * 3.5 * float(weight_kg) / 200.0 * duration_minutes
        return round(calories, 2)

    def get_profile(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT height_m, weight_kg, updated_at FROM fitness_profile WHERE id = 1").fetchone()
        if not row:
            return {"height_m": None, "weight_kg": None, "updated_at": None, "complete": False}
        return {
            "height_m": row[0],
            "weight_kg": row[1],
            "updated_at": row[2],
            "complete": row[0] is not None and row[1] is not None,
        }

    def save_profile(self, height_m: float | None, weight_kg: float | None) -> dict[str, Any]:
        now = self._now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO fitness_profile (id, height_m, weight_kg, updated_at)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    height_m = excluded.height_m,
                    weight_kg = excluded.weight_kg,
                    updated_at = excluded.updated_at
                """,
                (height_m, weight_kg, now),
            )
        return self.get_profile()

    def add_session(self, score_67: int, source: str = "manual", duration_seconds: int | None = None) -> dict[str, Any]:
        score = max(0, int(score_67))
        duration = self._estimate_duration_seconds(score, duration_seconds)
        profile = self.get_profile()
        height_m = profile.get("height_m")
        weight_kg = profile.get("weight_kg")
        calories = self.estimate_calories(weight_kg, duration)
        created_at = self._now_iso()
        source = (source or "manual").strip().lower()[:40] or "manual"
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO fitness_game_sessions
                    (score_67, duration_seconds, height_m, weight_kg, calories_burned, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (score, duration, height_m, weight_kg, calories, source, created_at),
            )
            session_id = cursor.lastrowid
        return self._session_to_dict((session_id, score, duration, height_m, weight_kg, calories, source, created_at), profile)

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(100, int(limit)))
        profile = self.get_profile()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, score_67, duration_seconds, height_m, weight_kg, calories_burned, source, created_at
                FROM fitness_game_sessions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._session_to_dict(row, profile) for row in rows]

    def stats(self, scope: str = "latest") -> dict[str, Any]:
        scope = (scope or "latest").strip().lower()
        if scope not in {"latest", "cumulative"}:
            scope = "latest"
        profile = self.get_profile()
        with self._connect() as conn:
            if scope == "latest":
                rows = conn.execute(
                    """
                    SELECT id, score_67, duration_seconds, height_m, weight_kg, calories_burned, source, created_at
                    FROM fitness_game_sessions
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, score_67, duration_seconds, height_m, weight_kg, calories_burned, source, created_at
                    FROM fitness_game_sessions
                    ORDER BY id ASC
                    """
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
