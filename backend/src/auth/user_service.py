from __future__ import annotations

import base64
import hashlib
import hmac
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

DEFAULT_ACCOUNTS = (
    ("mackwongyy@gmail.com", "12345678"),
    ("jonathansiew@hotmail.com", "87654321"),
)


class AuthError(Exception):
    pass


class AuthService:
    """SQLite-backed user authentication for the JUNO dashboard prototype.

    Passwords are stored as PBKDF2-HMAC hashes, not plaintext. Session tokens are
    random bearer tokens stored in SQLite so dashboard API requests can be scoped
    to the authenticated user.
    """

    def __init__(self, db_path: str = "juno_assist.db") -> None:
        self.db_path = db_path
        self._active_user_id: int | None = None
        self._initialise()
        self.ensure_default_accounts()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _initialise(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )

    def ensure_default_accounts(self) -> None:
        for username, password in DEFAULT_ACCOUNTS:
            self.create_user(username=username, password=password, if_missing=True)

    def create_user(self, username: str, password: str, if_missing: bool = False) -> dict[str, Any]:
        username = self._normalise_username(username)
        self._validate_password(password)
        password_hash = self.hash_password(password)
        now = self._now_iso()
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO users (username, password_hash, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (username, password_hash, now),
                )
                user_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            if if_missing:
                existing = self.get_user_by_username(username)
                if existing:
                    return existing
            raise AuthError("Username already exists")
        return {"id": user_id, "username": username, "created_at": now}

    def login(self, username: str, password: str) -> dict[str, Any]:
        username = self._normalise_username(username)
        user = self._get_user_with_hash(username)
        if not user or not self.verify_password(password, user["password_hash"]):
            raise AuthError("Invalid username or password")
        token = uuid.uuid4().hex + uuid.uuid4().hex
        now = self._now_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO user_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user["id"], now),
            )
        self._active_user_id = int(user["id"])
        return {"token": token, "user": self._public_user(user)}

    def logout(self, token: str) -> None:
        user = self.get_user_by_token(token)
        with self._connect() as conn:
            conn.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        if user and self._active_user_id == user["id"]:
            self._active_user_id = None

    def get_user_by_token(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.username, u.created_at
                FROM user_sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ?
                """,
                (token,),
            ).fetchone()
        if not row:
            return None
        return {"id": int(row[0]), "username": row[1], "created_at": row[2]}

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        user = self._get_user_with_hash(username)
        return self._public_user(user) if user else None

    def active_user_id(self) -> int | None:
        return self._active_user_id

    def set_active_user(self, user_id: int | None) -> None:
        self._active_user_id = int(user_id) if user_id else None

    def _get_user_with_hash(self, username: str) -> dict[str, Any] | None:
        username = self._normalise_username(username)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if not row:
            return None
        return {"id": int(row[0]), "username": row[1], "password_hash": row[2], "created_at": row[3]}

    @staticmethod
    def _public_user(user: dict[str, Any]) -> dict[str, Any]:
        return {"id": int(user["id"]), "username": user["username"], "created_at": user.get("created_at")}

    @staticmethod
    def _normalise_username(username: str) -> str:
        value = (username or "").strip().lower()
        if not value or "@" not in value or len(value) > 120:
            raise AuthError("Please provide a valid email username")
        return value

    @staticmethod
    def _validate_password(password: str) -> None:
        if not password or len(password) < 8:
            raise AuthError("Password must be at least 8 characters")

    @staticmethod
    def hash_password(password: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return "pbkdf2_sha256$120000$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        try:
            algorithm, iterations_s, salt_b64, digest_b64 = stored_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            iterations = int(iterations_s)
            salt = base64.b64decode(salt_b64.encode())
            expected = base64.b64decode(digest_b64.encode())
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False
