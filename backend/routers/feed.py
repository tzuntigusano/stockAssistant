"""Feed personal por acción (links de X, imágenes, texto)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core import feed

router = APIRouter(prefix="/api", tags=["feed"])


class PostIn(BaseModel):
    kind: str                    # 'x' | 'image' | 'text'
    url: str | None = None
    text: str | None = None
    image: str | None = None     # dataURL (solo al crear una imagen)


class PostEdit(BaseModel):
    text: str | None = None
    url: str | None = None


@router.get("/feed/image/{name}")
def feed_image(name: str):
    p = feed.image_path(name)
    if not p:
        raise HTTPException(404, "Imagen no encontrada")
    return FileResponse(p)


@router.get("/feed/{ticker}")
def list_feed(ticker: str, offset: int = 0, limit: int = 5):
    posts, total = feed.list_posts(ticker, max(0, offset), max(1, min(limit, 50)))
    return {"posts": posts, "total": total}


@router.post("/feed/{ticker}")
def add_feed(ticker: str, body: PostIn):
    if body.kind not in ("x", "image", "text"):
        raise HTTPException(400, "Tipo de publicación no válido")
    try:
        return feed.create(ticker, body.kind, body.url, body.text, body.image)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.patch("/feed/{post_id}")
def edit_feed(post_id: int, body: PostEdit):
    post = feed.update(post_id, body.text, body.url)
    if not post:
        raise HTTPException(404, "Publicación no encontrada")
    return post


@router.delete("/feed/{post_id}")
def del_feed(post_id: int):
    feed.delete(post_id)
    return {"deleted": True}
