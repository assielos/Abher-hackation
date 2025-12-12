from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "db.sqlite3"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

STATUS_PENDING = "PENDING_APPROVAL"
STATUS_APPROVED = "APPROVED"
STATUS_READY = "READY"
STATUS_REJECTED = "REJECTED"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                national_address TEXT NOT NULL,
                street_name TEXT,
                incident_date TEXT NOT NULL,
                incident_start TEXT NOT NULL,
                incident_end TEXT NOT NULL,
                report_path TEXT NOT NULL,
                status TEXT NOT NULL,
                upload_token TEXT NOT NULL,
                download_token TEXT,
                download_expires_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                channel TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES requests(id)
            )
            """
        )
        _ensure_columns(conn)
        conn.commit()


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """
    Lightweight migration to add new columns if the table already existed.
    """
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(requests)")}
    required = {
        "street_name": "ALTER TABLE requests ADD COLUMN street_name TEXT",
        "incident_date": "ALTER TABLE requests ADD COLUMN incident_date TEXT DEFAULT ''",
        "incident_start": "ALTER TABLE requests ADD COLUMN incident_start TEXT DEFAULT ''",
        "incident_end": "ALTER TABLE requests ADD COLUMN incident_end TEXT DEFAULT ''",
    }
    for col, stmt in required.items():
        if col not in existing:
            conn.execute(stmt)


def _now() -> str:
    return datetime.utcnow().isoformat()


def generate_token() -> str:
    return secrets.token_urlsafe(24)


def create_request(
    user_id: str,
    national_address: str,
    incident_date: str,
    incident_start: str,
    incident_end: str,
    report_path: Path,
    street_name: Optional[str] = None,
) -> int:
    upload_token = generate_token()
    now = _now()
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO requests (
                user_id, national_address, street_name,
                incident_date, incident_start, incident_end,
                report_path, status, upload_token, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                national_address,
                street_name,
                incident_date,
                incident_start,
                incident_end,
                str(report_path),
                STATUS_APPROVED,  # Auto-approve requests
                upload_token,
                now,
                now,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_report_path(request_id: int, report_path: Path) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE requests SET report_path = ?, updated_at = ? WHERE id = ?",
            (str(report_path), _now(), request_id),
        )
        conn.commit()


def get_request(request_id: int) -> Optional[sqlite3.Row]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM requests WHERE id = ?", (request_id,)
        ).fetchone()
        return row


def set_status(request_id: int, status: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE requests SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), request_id),
        )
        conn.commit()


def set_download_token(
    request_id: int, token: str, expires_at: datetime
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE requests
            SET download_token = ?, download_expires_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (token, expires_at.isoformat(), _now(), request_id),
        )
        conn.commit()


def record_notification(request_id: int, channel: str, message: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO notifications (request_id, channel, message, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (request_id, channel, message, _now()),
        )
        conn.commit()


def get_upload_token(request_id: int) -> Optional[str]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT upload_token FROM requests WHERE id = ?", (request_id,)
        ).fetchone()
        return row["upload_token"] if row else None


def validate_download_token(request_id: int, token: str) -> Tuple[bool, str]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT download_token, download_expires_at, status
            FROM requests WHERE id = ?
            """,
            (request_id,),
        ).fetchone()
        if not row:
            return False, "Request not found."
        if row["status"] != STATUS_READY:
            return False, "Video not ready."
        if row["download_token"] != token:
            return False, "Invalid token."
        if row["download_expires_at"]:
            expiry = datetime.fromisoformat(row["download_expires_at"])
            if datetime.utcnow() > expiry:
                return False, "Download link expired."
        return True, ""


def approve_request(request_id: int) -> None:
    set_status(request_id, STATUS_APPROVED)


def reject_request(request_id: int) -> None:
    set_status(request_id, STATUS_REJECTED)


def make_download_ready(request_id: int, hours_valid: int = 24) -> str:
    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=hours_valid)
    set_download_token(request_id, token, expires_at)
    set_status(request_id, STATUS_READY)
    return token

