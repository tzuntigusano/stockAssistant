"""SQLite cache layer to avoid hammering Yahoo Finance API."""

import sqlite3
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "data"
CACHE_DIR.mkdir(exist_ok=True)
DB_PATH = CACHE_DIR / "stocks.db"

_QUERIES = {
    "quote": 300,          # 5 min for quotes
    "ohlcv": 900,           # 15 min for OHLCV data
    "news": 1800,           # 30 min for news
    "fundamentals": 21600,  # 6 h for fundamentals (cambian poco)
}


def init_db():
    """Create cache tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def get(cache_type: str, key: str) -> dict | None:
    """Get cached value if not expired."""
    ttl = _QUERIES.get(cache_type, 600)
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT value FROM cache WHERE key = ? AND (strftime('%s','now') - created_at) < ?",
        (key, ttl),
    ).fetchone()
    conn.close()
    if row:
        import json
        return json.loads(row[0])
    return None


def set(cache_type: str, key: str, data: dict):
    """Store value in cache."""
    import json
    ts = time.time()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
        (key, json.dumps(data), ts),
    )
    conn.commit()
    conn.close()
