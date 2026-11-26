"""인증 + 쓰기 라우트. 폼은 303 리다이렉트, AJAX는 JSON (docs/API_CONTRACT.md)."""
import logging
import re
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from mysql.connector import errorcode
from mysql.connector import errors as mysql_errors
from PIL import Image

from backend import read_service as reads
from backend.auth import (check_csrf, hash_password, require_user_id,
                          verify_dummy, verify_password)
from backend.db import get_db
from backend.routers.pages import page

router = APIRouter()
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = ROOT / "static" / "uploads"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
IMAGE_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
UPLOADED_IMAGE_RE = re.compile(r"uploads/([0-9a-f]{32}\.(?:jpg|png|webp))")
USER_ID_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")


def _redirect(url):
    return RedirectResponse(url=url, status_code=303)


# ---------------- 인증 ----------------
@router.post("/login")
def login(request: Request, username: str = Form(""), password: str = Form(""),
          csrf_token: str = Form(""), db=Depends(get_db)):
    check_csrf(request, csrf_token)
    username = username.strip()
    row = None
    if USER_ID_RE.fullmatch(username) and 1 <= len(password) <= 128:
        with reads.cursor(db) as cur:
            cur.execute("SELECT user_id, password_hash FROM users WHERE user_id=%s", (username,))
            row = cur.fetchone()
    if row and verify_password(password, row["password_hash"]):
        request.session.clear()
        request.session["user_id"] = row["user_id"]
        return _redirect("/feed")
    if not row and len(password) <= 128:
        verify_dummy(password)
    return page(request, db, "login.html", layout="auth", active_page="login", current=None,
                status_code=401, error="아이디 또는 비밀번호가 올바르지 않습니다.")


@router.post("/signup")
def signup(request: Request, username: str = Form(""), display_name: str = Form(""),
           password: str = Form(""), confirm_password: str = Form(""),
           csrf_token: str = Form(""), db=Depends(get_db)):
    check_csrf(request, csrf_token)
    username, display_name = username.strip(), display_name.strip()

    def fail(msg):
        return page(request, db, "signup.html", layout="auth", active_page="signup",
                    current=None, status_code=400, error=msg)

    if not USER_ID_RE.fullmatch(username):
        return fail("아이디는 영문, 숫자, _ 로 3~30자여야 합니다.")
    if not (1 <= len(display_name) <= 50):
        return fail("이름은 1~50자로 입력해 주세요.")
    if not (8 <= len(password) <= 128):
        return fail("비밀번호는 8~128자여야 합니다.")
    if password != confirm_password:
        return fail("비밀번호 확인이 일치하지 않습니다.")

    try:
        with reads.cursor(db) as cur:
            cur.execute(
                "INSERT INTO users (user_id, password_hash, display_name) VALUES (%s, %s, %s)",
                (username, hash_password(password), display_name))
        db.commit()
    except mysql_errors.IntegrityError as exc:
        db.rollback()
        if exc.errno != errorcode.ER_DUP_ENTRY:
            raise
        return fail("이미 사용 중인 아이디입니다.")
    request.session["signup_success"] = True
    return _redirect("/login")


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form("")):
    check_csrf(request, csrf_token)
    request.session.clear()
    return _redirect("/login")


@router.post("/settings/profile")
def profile_update(request: Request, display_name: str = Form(""), bio: str = Form(""),
                   csrf_token: str = Form(""), db=Depends(get_db)):
    current = reads.get_current_user(db, request)
    if not current:
        return _redirect("/login")
    check_csrf(request, csrf_token)
    display_name, bio = display_name.strip(), bio.strip()

    if not 1 <= len(display_name) <= 50 or len(bio) > 200:
        error = ("표시 이름은 1~50자로 입력해 주세요." if not 1 <= len(display_name) <= 50
                 else "자기소개는 200자 이하로 입력해 주세요.")
        return page(request, db, "change_password.html", active_page="settings",
                    current=current, status_code=400, profile_error=error,
                    display_name_input=display_name, bio_input=bio)

    with reads.cursor(db) as cur:
        cur.execute(
            "UPDATE users SET display_name=%s, bio=%s WHERE user_id=%s",
            (display_name, bio or None, current["user_id"]),
        )
    db.commit()
    request.session["profile_saved"] = True
    return _redirect("/settings/password")


@router.post("/settings/password")
def password_update(request: Request, current_password: str = Form(""),
                    new_password: str = Form(""), confirm_password: str = Form(""),
                    csrf_token: str = Form(""), db=Depends(get_db)):
    current = reads.get_current_user(db, request)
    if not current:
        return _redirect("/login")
    check_csrf(request, csrf_token)

    def fail(msg):
        return page(request, db, "change_password.html", active_page="settings",
                    current=current, status_code=400, error=msg)

    if not (8 <= len(new_password) <= 128):
        return fail("새 비밀번호는 8~128자여야 합니다.")
    if new_password != confirm_password:
        return fail("새 비밀번호 확인이 일치하지 않습니다.")
    with reads.cursor(db) as cur:
        cur.execute("SELECT password_hash FROM users WHERE user_id=%s", (current["user_id"],))
        row = cur.fetchone()
        if (not row or not 1 <= len(current_password) <= 128
                or not verify_password(current_password, row["password_hash"])):
            return fail("현재 비밀번호가 올바르지 않습니다.")
        cur.execute(
            "UPDATE users SET password_hash=%s WHERE user_id=%s AND CAST(password_hash AS BINARY)=%s",
            (hash_password(new_password), current["user_id"], row["password_hash"].encode("utf-8")),
        )
        if cur.rowcount != 1:
            db.rollback()
            return fail("비밀번호가 이미 변경되었습니다. 현재 비밀번호를 다시 확인해 주세요.")
    db.commit()
    return _redirect("/settings/password?changed=1")


# ---------------- 게시물 ----------------
def _image_ext(data: bytes) -> str | None:
    try:
        with Image.open(BytesIO(data), formats=list(IMAGE_EXTENSIONS)) as photo:
            if photo.width * photo.height > MAX_IMAGE_PIXELS:
                return None
            ext = IMAGE_EXTENSIONS[photo.format]
            photo.verify()
        with Image.open(BytesIO(data), formats=list(IMAGE_EXTENSIONS)) as photo:
            photo.load()
        return ext
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        return None


@router.post("/posts")
def create_post(request: Request, image: UploadFile | None = File(None), caption: str = Form(""),
                csrf_token: str = Form(""), db=Depends(get_db)):
    current = reads.get_current_user(db, request)
    if not current:
        return _redirect("/login")
    check_csrf(request, csrf_token)

    def fail(msg):
        return page(request, db, "upload.html", active_page="upload", current=current,
                    status_code=400, upload_error=msg)

    if len(caption) > 2200:
        return fail("캡션은 2200자 이하로 입력해 주세요.")
    data = image.file.read(MAX_IMAGE_BYTES + 1) if image else b""
    if not data:
        return fail("사진을 선택해 주세요.")
    if len(data) > MAX_IMAGE_BYTES:
        return fail("사진은 8MB 이하만 올릴 수 있습니다.")
    ext = _image_ext(data)
    if not ext:
        return fail("2500만 픽셀 이하의 정상적인 JPG, PNG, WEBP 사진을 올려 주세요.")

    name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / name
    saved = False
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        with reads.cursor(db) as cur:
            cur.execute("INSERT INTO posts (author_id, image_path, caption) VALUES (%s, %s, %s)",
                        (current["user_id"], f"uploads/{name}", caption.strip() or None))
        db.commit()
        saved = True
    finally:
        if not saved:
            path.unlink(missing_ok=True)
    return _redirect("/feed?uploaded=1")


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, request: Request, x_csrf_token: str | None = Header(None),
                uid: str = Depends(require_user_id), db=Depends(get_db)):
    check_csrf(request, x_csrf_token)
    if not 1 <= post_id <= 2**63 - 1:
        raise HTTPException(status_code=404, detail="삭제할 수 있는 게시물을 찾을 수 없습니다.")

    with reads.cursor(db) as cur:
        cur.execute(
            "SELECT image_path FROM posts WHERE post_id=%s AND author_id=%s FOR UPDATE",
            (post_id, uid),
        )
        post = cur.fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="삭제할 수 있는 게시물을 찾을 수 없습니다.")

        cur.execute("DELETE FROM posts WHERE post_id=%s AND author_id=%s", (post_id, uid))
        uploaded_image = UPLOADED_IMAGE_RE.fullmatch(post["image_path"])
        if uploaded_image:
            cur.execute("SELECT 1 FROM posts WHERE image_path=%s LIMIT 1", (post["image_path"],))
            if cur.fetchone():
                uploaded_image = None
        db.commit()

    if uploaded_image:
        try:
            (UPLOAD_DIR / uploaded_image[1]).unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove the image for deleted post %s", post_id, exc_info=True)
    return {"deleted": True, "post_id": post_id}


def _require_post(cur, post_id: int):
    if 1 <= post_id <= 2**63 - 1:
        cur.execute("SELECT post_id FROM posts WHERE post_id=%s FOR UPDATE", (post_id,))
        if cur.fetchone():
            return
    raise HTTPException(status_code=404, detail="게시물을 찾을 수 없습니다.")


def _comment_count(cur, post_id):
    cur.execute("SELECT COUNT(*) AS n FROM comments WHERE post_id=%s", (post_id,))
    return int(cur.fetchone()["n"])


@router.post("/posts/{post_id}/comments", status_code=201)
def create_comment(post_id: int, request: Request, text: str = Form(""),
                   csrf_token: str = Form(""), x_csrf_token: str | None = Header(None),
                   uid: str = Depends(require_user_id), db=Depends(get_db)):
    check_csrf(request, x_csrf_token or csrf_token)
    text = text.strip()
    if not (1 <= len(text) <= 1000):
        raise HTTPException(status_code=400, detail="댓글은 1~1000자로 입력해 주세요.")
    with reads.cursor(db) as cur:
        _require_post(cur, post_id)
        cur.execute("INSERT INTO comments (post_id, author_id, text) VALUES (%s, %s, %s)",
                    (post_id, uid, text))
        comment_id = cur.lastrowid
        cur.execute("SELECT created_at FROM comments WHERE comment_id=%s", (comment_id,))
        created = cur.fetchone()["created_at"]
        db.commit()
        count = _comment_count(cur, post_id)
    return {"comment": {"comment_id": comment_id, "author_id": uid, "text": text,
                        "created_at": reads._fmt(created)},
            "comment_count": count}


@router.delete("/posts/{post_id}/comments/{comment_id}")
def delete_comment(post_id: int, comment_id: int, request: Request,
                   x_csrf_token: str | None = Header(None),
                   uid: str = Depends(require_user_id), db=Depends(get_db)):
    check_csrf(request, x_csrf_token)
    with reads.cursor(db) as cur:
        _require_post(cur, post_id)
        if not 1 <= comment_id <= 2**63 - 1:
            raise HTTPException(status_code=404, detail="삭제할 수 있는 댓글을 찾을 수 없습니다.")
        cur.execute(
            "DELETE FROM comments WHERE comment_id=%s AND post_id=%s AND author_id=%s",
            (comment_id, post_id, uid))
        if cur.rowcount != 1:
            raise HTTPException(status_code=404, detail="삭제할 수 있는 댓글을 찾을 수 없습니다.")
        db.commit()
        count = _comment_count(cur, post_id)
    return {"deleted": True, "comment_id": comment_id, "comment_count": count}


@router.post("/posts/{post_id}/likes")
@router.delete("/posts/{post_id}/likes")
def change_like(post_id: int, request: Request, x_csrf_token: str | None = Header(None),
                uid: str = Depends(require_user_id), db=Depends(get_db)):
    check_csrf(request, x_csrf_token)
    liked = request.method == "POST"
    with reads.cursor(db) as cur:
        _require_post(cur, post_id)
        if liked:
            cur.execute(
                "INSERT INTO likes (post_id, user_id) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE user_id=likes.user_id",
                (post_id, uid),
            )
        else:
            cur.execute("DELETE FROM likes WHERE post_id=%s AND user_id=%s", (post_id, uid))
        db.commit()
        cur.execute("SELECT COUNT(*) AS n FROM likes WHERE post_id=%s", (post_id,))
        count = int(cur.fetchone()["n"])
    return {"liked": liked, "like_count": count}


def _target_user(cur, user_id: str, me: str) -> str:
    if USER_ID_RE.fullmatch(user_id):
        cur.execute("SELECT user_id FROM users WHERE user_id=%s FOR SHARE", (user_id,))
        row = cur.fetchone()
        if row:
            if row["user_id"] == me:
                raise HTTPException(status_code=400, detail="자기 자신은 팔로우할 수 없습니다.")
            return row["user_id"]
    raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")


@router.post("/users/{user_id}/follow")
@router.delete("/users/{user_id}/follow")
def change_follow(user_id: str, request: Request, x_csrf_token: str | None = Header(None),
                  me: str = Depends(require_user_id), db=Depends(get_db)):
    check_csrf(request, x_csrf_token)
    following = request.method == "POST"
    with reads.cursor(db) as cur:
        target = _target_user(cur, user_id, me)
        if following:
            cur.execute(
                "INSERT INTO follows (follower_id, followee_id) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE follower_id=follows.follower_id",
                (me, target),
            )
        else:
            cur.execute("DELETE FROM follows WHERE follower_id=%s AND followee_id=%s", (me, target))
        db.commit()
        cur.execute("SELECT COUNT(*) AS n FROM follows WHERE followee_id=%s", (target,))
        count = int(cur.fetchone()["n"])
    return {"user_id": target, "is_following": following, "followers_count": count}
