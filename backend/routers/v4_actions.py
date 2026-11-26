"""FRAME v4: author-only editing and profile photo upload.

Routes are additive to the existing v3 actions router. MySQL already has
users.avatar_url, posts.caption and comments.text, so no DDL migration needed.
"""
import logging
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from PIL import Image

from backend.auth import check_csrf, require_user_id
from backend.db import get_db
from backend.routers.actions import MAX_IMAGE_BYTES, MAX_IMAGE_PIXELS, _image_ext
from backend import read_service as reads

router = APIRouter(tags=["v4 editing & avatars"])
logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = ROOT / "static" / "uploads"


def _valid_id(identifier: int) -> bool:
    return 1 <= identifier <= (2**63 - 1)


@router.patch("/posts/{post_id}")
def edit_post(post_id: int, request: Request, caption: str = Form(""),
              x_csrf_token: str | None = Header(None),
              uid: str = Depends(require_user_id), db=Depends(get_db)):
    check_csrf(request, x_csrf_token)
    if not _valid_id(post_id):
        raise HTTPException(status_code=404, detail="게시물을 찾을 수 없습니다.")
    if len(caption) > 2200:
        raise HTTPException(status_code=400, detail="캡션은 최대 2200자입니다.")

    with reads.cursor(db) as cur:
        cur.execute("SELECT post_id FROM posts WHERE post_id=%s AND author_id=%s",
                    (post_id, uid))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="수정할 수 있는 게시물이 없습니다.")
        normalized = caption.strip()
        cur.execute("UPDATE posts SET caption=%s WHERE post_id=%s AND author_id=%s",
                    (normalized or None, post_id, uid))
        db.commit()
    return {"post_id": post_id, "caption": normalized, "updated": True}


@router.patch("/posts/{post_id}/comments/{comment_id}")
def edit_comment(post_id: int, comment_id: int, request: Request,
                 text: str = Form(""), x_csrf_token: str | None = Header(None),
                 uid: str = Depends(require_user_id), db=Depends(get_db)):
    check_csrf(request, x_csrf_token)
    if not _valid_id(post_id) or not _valid_id(comment_id):
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    normalized = text.strip()
    if not (1 <= len(normalized) <= 1000):
        raise HTTPException(status_code=400, detail="댓글은 1~1000자로 입력해 주세요.")

    with reads.cursor(db) as cur:
        cur.execute(
            "SELECT comment_id FROM comments WHERE comment_id=%s AND post_id=%s AND author_id=%s",
            (comment_id, post_id, uid),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="수정할 수 있는 댓글이 없습니다.")
        cur.execute(
            "UPDATE comments SET text=%s WHERE comment_id=%s AND post_id=%s AND author_id=%s",
            (normalized, comment_id, post_id, uid),
        )
        db.commit()
    return {"comment": {"comment_id": comment_id, "post_id": post_id,
                        "author_id": uid, "text": normalized}, "updated": True}


@router.post("/users/me/avatar")
def upload_avatar(request: Request, avatar: UploadFile | None = File(None),
                  x_csrf_token: str | None = Header(None),
                  uid: str = Depends(require_user_id), db=Depends(get_db)):
    check_csrf(request, x_csrf_token)
    data = avatar.file.read(MAX_IMAGE_BYTES + 1) if avatar else b""
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="8MB 이하의 프로필 사진을 선택해 주세요.")
    if _image_ext(data) is None:
        raise HTTPException(status_code=400, detail="정상적인 JPG·PNG·WEBP 사진만 등록할 수 있습니다.")

    # JPEG 재인코딩으로 EXIF 및 불필요한 메타데이터 제거.
    try:
        with Image.open(BytesIO(data)) as img:
            if img.width * img.height > MAX_IMAGE_PIXELS:
                raise ValueError("Image dimensions exceed the limit")
            rgb = img.convert("RGB")
            rgb.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            name = f"{uuid.uuid4().hex}.jpg"
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            path = UPLOAD_DIR / name
            rgb.save(path, "JPEG", quality=86, optimize=True)
    except (OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="사진을 처리할 수 없습니다.")

    avatar_url = f"/static/uploads/{name}"
    committed = False
    try:
        with reads.cursor(db) as cur:
            cur.execute("UPDATE users SET avatar_url=%s WHERE user_id=%s", (avatar_url, uid))
            if cur.rowcount != 1:
                raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다.")
        db.commit()
        committed = True
    finally:
        if not committed:
            db.rollback()
            path.unlink(missing_ok=True)

    return {"avatar_url": avatar_url, "user_id": uid, "updated": True}
