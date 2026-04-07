import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "bot.db"


@dataclass
class User:
    telegram_id: int
    username: str
    first_name: str


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                first_name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES users(telegram_id),
                FOREIGN KEY (target_id) REFERENCES users(telegram_id)
            )
            """
        )
        conn.commit()


def upsert_user(telegram_id: int, username: Optional[str], first_name: str) -> None:
    normalized_username = (username or "").strip().lower()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (telegram_id, normalized_username, first_name),
        )
        conn.commit()


def get_user_by_username(username: str) -> Optional[User]:
    normalized = username.strip().lstrip("@").lower()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT telegram_id, username, first_name FROM users WHERE username = ?",
            (normalized,),
        ).fetchone()
    if not row:
        return None
    return User(
        telegram_id=row["telegram_id"],
        username=row["username"],
        first_name=row["first_name"],
    )


def create_deal(creator_id: int, target_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO deals (creator_id, target_id) VALUES (?, ?)",
            (creator_id, target_id),
        )
        conn.commit()
        return int(cursor.lastrowid)
