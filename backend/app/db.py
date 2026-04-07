import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "bot.db"


DEAL_STATUS_CREATED = "created"
DEAL_STATUS_ACCEPTED = "accepted"
DEAL_STATUS_IN_PROGRESS = "in_progress"
DEAL_STATUS_DELIVERED = "delivered"
DEAL_STATUS_COMPLETED = "completed"
DEAL_STATUS_CANCELLED = "cancelled"

TX_DEPOSIT = "deposit"
TX_HOLD = "hold"
TX_RELEASE = "release"
TX_WITHDRAW_REQUEST = "withdraw_request"
TX_WITHDRAW_APPROVED = "withdraw_approved"
TX_REFUND = "refund"


@dataclass
class User:
    telegram_id: int
    username: str
    first_name: str
    role: str


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        user_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if user_columns:
            if "role" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
            if "rating_sum" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN rating_sum INTEGER NOT NULL DEFAULT 0")
            if "rating_count" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN rating_count INTEGER NOT NULL DEFAULT 0")

        deal_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(deals)").fetchall()
        }
        if deal_columns and "buyer_id" not in deal_columns and "creator_id" in deal_columns:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS deals_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    buyer_id INTEGER NOT NULL,
                    seller_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL DEFAULT 0,
                    fee INTEGER NOT NULL DEFAULT 0,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'created',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    accepted_at DATETIME,
                    delivered_at DATETIME,
                    completed_at DATETIME,
                    cancelled_at DATETIME
                )
                """
            )
            conn.execute(
                """
                INSERT INTO deals_new (id, buyer_id, seller_id, amount, description, status, created_at)
                SELECT id, creator_id, target_id, 0, '', status, created_at FROM deals
                """
            )
            conn.execute("DROP TABLE deals")
            conn.execute("ALTER TABLE deals_new RENAME TO deals")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                first_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                rating_sum INTEGER NOT NULL DEFAULT 0,
                rating_count INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                fee INTEGER NOT NULL DEFAULT 0,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'created',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                accepted_at DATETIME,
                delivered_at DATETIME,
                completed_at DATETIME,
                cancelled_at DATETIME,
                FOREIGN KEY (buyer_id) REFERENCES users(telegram_id),
                FOREIGN KEY (seller_id) REFERENCES users(telegram_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                deal_id INTEGER,
                tx_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USDT',
                status TEXT NOT NULL DEFAULT 'done',
                meta_json TEXT NOT NULL DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id),
                FOREIGN KEY (deal_id) REFERENCES deals(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(deal_id, author_id),
                FOREIGN KEY (deal_id) REFERENCES deals(id),
                FOREIGN KEY (author_id) REFERENCES users(telegram_id),
                FOREIGN KEY (target_id) REFERENCES users(telegram_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                method TEXT NOT NULL,
                destination TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                admin_note TEXT NOT NULL DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                approved_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_intents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                external_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USDT',
                status TEXT NOT NULL DEFAULT 'pending',
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider, external_id),
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
            """
        )
        conn.commit()


def upsert_user(
    telegram_id: int,
    username: Optional[str],
    first_name: str,
    role: str = "user",
) -> None:
    normalized_username = (username or "").strip().lower()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, role)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (telegram_id, normalized_username, first_name, role),
        )
        conn.commit()


def set_admin_role(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE users SET role = 'admin' WHERE telegram_id = ?", (user_id,))
        conn.commit()


def get_user(user_id: int) -> Optional[User]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT telegram_id, username, first_name, role FROM users WHERE telegram_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return User(
        telegram_id=row["telegram_id"],
        username=row["username"] or "",
        first_name=row["first_name"],
        role=row["role"],
    )


def get_user_by_username(username: str) -> Optional[User]:
    normalized = username.strip().lstrip("@").lower()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT telegram_id, username, first_name, role FROM users WHERE username = ?",
            (normalized,),
        ).fetchone()
    if not row:
        return None
    return User(
        telegram_id=row["telegram_id"],
        username=row["username"] or "",
        first_name=row["first_name"],
        role=row["role"],
    )


def wallet_balance(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS balance FROM wallet_transactions WHERE user_id = ? AND status = 'done'",
            (user_id,),
        ).fetchone()
    return int(row["balance"] if row else 0)


def add_wallet_transaction(
    user_id: int,
    tx_type: str,
    amount: int,
    currency: str = "USDT",
    deal_id: Optional[int] = None,
    status: str = "done",
    meta: Optional[dict] = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO wallet_transactions (user_id, deal_id, tx_type, amount, currency, status, meta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, deal_id, tx_type, amount, currency, status, json.dumps(meta or {})),
        )
        conn.commit()


def create_deal(buyer_id: int, seller_id: int, amount: int, description: str) -> int:
    with get_connection() as conn:
        if wallet_balance(buyer_id) < amount:
            raise ValueError("INSUFFICIENT_BALANCE")
        cursor = conn.execute(
            """
            INSERT INTO deals (buyer_id, seller_id, amount, description, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (buyer_id, seller_id, amount, description, DEAL_STATUS_CREATED),
        )
        deal_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO wallet_transactions (user_id, deal_id, tx_type, amount, currency, status, meta_json)
            VALUES (?, ?, ?, ?, 'USDT', 'done', ?)
            """,
            (buyer_id, deal_id, TX_HOLD, -amount, json.dumps({"reason": "deal_hold"})),
        )
        conn.commit()
    return deal_id


def get_deal(deal_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
    return row


def list_user_deals(user_id: int, limit: int = 10) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM deals
            WHERE buyer_id = ? OR seller_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, user_id, limit),
        ).fetchall()
    return rows


def update_deal_status(deal_id: int, status: str) -> None:
    field_by_status = {
        DEAL_STATUS_ACCEPTED: "accepted_at",
        DEAL_STATUS_DELIVERED: "delivered_at",
        DEAL_STATUS_COMPLETED: "completed_at",
        DEAL_STATUS_CANCELLED: "cancelled_at",
    }
    set_field = field_by_status.get(status)
    with get_connection() as conn:
        if set_field:
            conn.execute(
                f"UPDATE deals SET status = ?, {set_field} = CURRENT_TIMESTAMP WHERE id = ?",
                (status, deal_id),
            )
        else:
            conn.execute("UPDATE deals SET status = ? WHERE id = ?", (status, deal_id))
        conn.commit()


def accept_deal(deal_id: int, seller_id: int) -> sqlite3.Row:
    with get_connection() as conn:
        deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
        if not deal:
            raise ValueError("DEAL_NOT_FOUND")
        if int(deal["seller_id"]) != seller_id:
            raise ValueError("FORBIDDEN")
        if deal["status"] != DEAL_STATUS_CREATED:
            raise ValueError("INVALID_STATUS")
        conn.execute(
            "UPDATE deals SET status = ?, accepted_at = CURRENT_TIMESTAMP WHERE id = ?",
            (DEAL_STATUS_IN_PROGRESS, deal_id),
        )
        conn.commit()
    return get_deal(deal_id)  # type: ignore[return-value]


def mark_delivered(deal_id: int, seller_id: int) -> sqlite3.Row:
    with get_connection() as conn:
        deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
        if not deal:
            raise ValueError("DEAL_NOT_FOUND")
        if int(deal["seller_id"]) != seller_id:
            raise ValueError("FORBIDDEN")
        if deal["status"] != DEAL_STATUS_IN_PROGRESS:
            raise ValueError("INVALID_STATUS")
        conn.execute(
            "UPDATE deals SET status = ?, delivered_at = CURRENT_TIMESTAMP WHERE id = ?",
            (DEAL_STATUS_DELIVERED, deal_id),
        )
        conn.commit()
    return get_deal(deal_id)  # type: ignore[return-value]


def confirm_deal(deal_id: int, buyer_id: int) -> sqlite3.Row:
    with get_connection() as conn:
        deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
        if not deal:
            raise ValueError("DEAL_NOT_FOUND")
        if int(deal["buyer_id"]) != buyer_id:
            raise ValueError("FORBIDDEN")
        if deal["status"] != DEAL_STATUS_DELIVERED:
            raise ValueError("INVALID_STATUS")
        amount = int(deal["amount"])
        conn.execute(
            "UPDATE deals SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (DEAL_STATUS_COMPLETED, deal_id),
        )
        conn.execute(
            """
            INSERT INTO wallet_transactions (user_id, deal_id, tx_type, amount, currency, status, meta_json)
            VALUES (?, ?, ?, ?, 'USDT', 'done', ?)
            """,
            (
                int(deal["seller_id"]),
                deal_id,
                TX_RELEASE,
                amount,
                json.dumps({"reason": "deal_release"}),
            ),
        )
        conn.commit()
    return get_deal(deal_id)  # type: ignore[return-value]


def create_review(
    deal_id: int,
    author_id: int,
    target_id: int,
    rating: int,
    text: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO reviews (deal_id, author_id, target_id, rating, text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (deal_id, author_id, target_id, rating, text),
        )
        conn.execute(
            """
            UPDATE users
            SET rating_sum = rating_sum + ?, rating_count = rating_count + 1
            WHERE telegram_id = ?
            """,
            (rating, target_id),
        )
        conn.commit()


def create_withdraw_request(user_id: int, amount: int, destination: str) -> int:
    with get_connection() as conn:
        if wallet_balance(user_id) < amount:
            raise ValueError("INSUFFICIENT_BALANCE")
        conn.execute(
            """
            INSERT INTO wallet_transactions (user_id, tx_type, amount, currency, status, meta_json)
            VALUES (?, ?, ?, 'USDT', 'done', ?)
            """,
            (user_id, TX_WITHDRAW_REQUEST, -amount, json.dumps({"destination": destination})),
        )
        cursor = conn.execute(
            """
            INSERT INTO withdraw_requests (user_id, amount, method, destination, status)
            VALUES (?, ?, 'cryptobot', ?, 'pending')
            """,
            (user_id, amount, destination),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_pending_withdraw_requests() -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY id ASC"
        ).fetchall()
    return rows


def approve_withdraw_request(request_id: int, admin_note: str = "") -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        request = conn.execute(
            "SELECT * FROM withdraw_requests WHERE id = ?",
            (request_id,),
        ).fetchone()
        if not request or request["status"] != "pending":
            return None
        conn.execute(
            """
            UPDATE withdraw_requests
            SET status = 'approved', admin_note = ?, approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (admin_note, request_id),
        )
        conn.execute(
            """
            INSERT INTO wallet_transactions (user_id, tx_type, amount, currency, status, meta_json)
            VALUES (?, ?, 0, 'USDT', 'done', ?)
            """,
            (
                int(request["user_id"]),
                TX_WITHDRAW_APPROVED,
                json.dumps({"withdraw_request_id": request_id}),
            ),
        )
        conn.commit()
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM withdraw_requests WHERE id = ?",
            (request_id,),
        ).fetchone()


def create_payment_intent(
    user_id: int,
    provider: str,
    external_id: str,
    amount: int,
    currency: str,
    payload: Optional[dict] = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO payment_intents (user_id, provider, external_id, amount, currency, status, payload_json, updated_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, CURRENT_TIMESTAMP)
            """,
            (user_id, provider, external_id, amount, currency, json.dumps(payload or {})),
        )
        conn.commit()


def mark_payment_intent_paid(provider: str, external_id: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM payment_intents WHERE provider = ? AND external_id = ?",
            (provider, external_id),
        ).fetchone()
        if not row:
            return None
        if row["status"] == "paid":
            return row
        conn.execute(
            """
            UPDATE payment_intents
            SET status = 'paid', updated_at = CURRENT_TIMESTAMP
            WHERE provider = ? AND external_id = ?
            """,
            (provider, external_id),
        )
        conn.commit()
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM payment_intents WHERE provider = ? AND external_id = ?",
            (provider, external_id),
        ).fetchone()


def list_wallet_transactions(user_id: int, limit: int = 15) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM wallet_transactions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return rows
