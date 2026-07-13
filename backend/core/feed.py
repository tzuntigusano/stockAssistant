"""Feed personal por acción: links de X, imágenes (con texto) y notas de texto.

Sustituye a las noticias en la ficha. Persistente en SQLite; las imágenes se
guardan en disco (backend/data/feed_images) para no inflar la BD.
"""

from __future__ import annotations

import base64
import os
import sqlite3
import time
import uuid

from core.cache import CACHE_DIR, DB_PATH

IMAGES_DIR = CACHE_DIR / "feed_images"

_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
}
_MAX_IMAGE_BYTES = 6 * 1024 * 1024  # 6 MB


def init_db():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feed_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            kind TEXT NOT NULL,          -- 'x' | 'image' | 'text'
            url TEXT,
            text TEXT,
            image TEXT,                  -- nombre de fichero en IMAGES_DIR
            created_at REAL NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_feed_ticker ON feed_posts(ticker)")
    conn.commit()
    conn.close()


def _row(r) -> dict:
    return {
        "id": r[0], "ticker": r[1], "kind": r[2],
        "url": r[3], "text": r[4], "image": r[5], "created_at": r[6],
    }


_COLS = "id, ticker, kind, url, text, image, created_at"


def _save_image(data_url: str) -> str:
    """Guarda una imagen dataURL en disco y devuelve el nombre de fichero."""
    if not data_url.startswith("data:"):
        raise ValueError("Formato de imagen no válido")
    header, _, b64 = data_url.partition(",")
    mime = header[5:].split(";")[0].lower()  # 'image/png'
    ext = _EXT.get(mime)
    if not ext:
        raise ValueError("Tipo de imagen no soportado")
    raw = base64.b64decode(b64)
    if len(raw) > _MAX_IMAGE_BYTES:
        raise ValueError("La imagen es demasiado grande (máx. 6 MB)")
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (IMAGES_DIR / name).write_bytes(raw)
    return name


def create(ticker: str, kind: str, url: str | None, text: str | None, image_data: str | None) -> dict:
    image = _save_image(image_data) if image_data else None
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO feed_posts (ticker, kind, url, text, image, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (ticker.upper(), kind, url, text, image, time.time()),
    )
    conn.commit()
    row = conn.execute(f"SELECT {_COLS} FROM feed_posts WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return _row(row)


def list_posts(ticker: str, offset: int = 0, limit: int = 5) -> tuple[list[dict], int]:
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute(
        "SELECT COUNT(*) FROM feed_posts WHERE ticker = ?", (ticker.upper(),)
    ).fetchone()[0]
    rows = conn.execute(
        f"SELECT {_COLS} FROM feed_posts WHERE ticker = ? "
        "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        (ticker.upper(), limit, offset),
    ).fetchall()
    conn.close()
    return [_row(r) for r in rows], total


def update(post_id: int, text: str | None = None, url: str | None = None) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(f"SELECT {_COLS} FROM feed_posts WHERE id = ?", (post_id,)).fetchone()
    if not cur:
        conn.close()
        return None
    new_url = url if url is not None else cur[3]
    new_text = text if text is not None else cur[4]
    conn.execute("UPDATE feed_posts SET url = ?, text = ? WHERE id = ?", (new_url, new_text, post_id))
    conn.commit()
    row = conn.execute(f"SELECT {_COLS} FROM feed_posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    return _row(row)


def delete(post_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT image FROM feed_posts WHERE id = ?", (post_id,)).fetchone()
    conn.execute("DELETE FROM feed_posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    if row and row[0]:
        try:
            (IMAGES_DIR / row[0]).unlink(missing_ok=True)
        except Exception:
            pass
    return True


def image_path(name: str):
    """Ruta segura de una imagen del feed (evita path traversal)."""
    safe = os.path.basename(name)
    p = IMAGES_DIR / safe
    return p if p.exists() else None
