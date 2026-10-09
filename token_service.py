import hashlib
import secrets
import sqlite3
from datetime import datetime, timezone
from .config import DB_PATH


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_tokens (
            token_hash TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            last_used_at TEXT,
            revoked INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    token = "npa_" + secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("INSERT INTO api_tokens(token_hash, created_at) VALUES(?, ?)", (_hash(token), now))
    return token


def validate_token(token: str) -> bool:
    if not token or not token.startswith("npa_"):
        return False
    h = _hash(token)
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        row = conn.execute("SELECT revoked FROM api_tokens WHERE token_hash=?", (h,)).fetchone()
        if not row or row[0]:
            return False
        conn.execute("UPDATE api_tokens SET last_used_at=? WHERE token_hash=?", (now, h))
        conn.commit()
    return True
