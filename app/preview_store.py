"""Small filesystem-only store for UI previews; not a substitute for MySQL.

Saved data: preview_data/posts.json
Uploaded images: static/uploads/
Do not use this as a production or shared multi-user persistence layer.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import UploadFile

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "preview_data" / "posts.json"
UPLOAD_DIR = ROOT / "static" / "uploads"
MAX_BYTES = 8 * 1024 * 1024
LOCK = Lock()


def read_posts() -> list[dict]:
    if not DATA_PATH.is_file():
        return []
    with LOCK:
        try:
            data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []


def _image_type(content: bytes) -> str | None:
    """Verify magic bytes, not just browser-provided file type / filename."""
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "webp"
    return None


async def store_post(image: UploadFile, caption: str, user: dict) -> dict:
    """Persist preview post and image, returning a render-compatible post dict."""
    content = await image.read(MAX_BYTES + 1)
    if not content or len(content) > MAX_BYTES:
        raise ValueError("사진은 8MB 이하의 JPG, PNG 또는 WEBP 파일이어야 합니다.")
    ext = _image_type(content)
    if ext is None:
        raise ValueError("JPG, PNG 또는 WEBP 이미지 파일만 업로드할 수 있어요.")

    filename = f"{uuid4().hex}.{ext}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / filename).write_bytes(content)

    with LOCK:
        try:
            previous = json.loads(DATA_PATH.read_text(encoding="utf-8")) if DATA_PATH.exists() else []
            if not isinstance(previous, list):
                previous = []
        except (OSError, json.JSONDecodeError):
            previous = []
        post = {
            "post_id": f"preview-{uuid4().hex}",
            "author_id": user["user_id"],
            "author_name": user["display_name"],
            "author_avatar": user["avatar_url"],
            "image_url": f"/static/uploads/{filename}",
            "image_alt": "사용자가 업로드한 사진",
            "caption": caption[:2200],
            "created_at": "방금 전",
            "location": "새 게시물",
            "like_count": 0,
            "comment_count": 0,
            "is_liked": False,
            "comments": [],
        }
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = DATA_PATH.with_name(f"posts.{uuid4().hex}.tmp")
        try:
            tmp.write_text(json.dumps([post, *previous], ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, DATA_PATH)
        finally:
            tmp.unlink(missing_ok=True)
    return post
