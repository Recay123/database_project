"""인증 + 쓰기 라우트. 폼은 303 리다이렉트, AJAX는 JSON (docs/API_CONTRACT.md)."""
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from mysql.connector import errors as mysql_errors

from backend import read_service as reads
from backend.auth import (check_csrf, hash_password, require_user_id,
                          verify_dummy, verify_password)
from backend.db import get_db
from backend.routers.pages import page

router = APIRouter()

ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = ROOT / "static" / "uploads"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
USER_ID_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")


def _redirect(url):
    return RedirectResponse(url=url, status_code=303)


# ---------------- 인증 ----------------
@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...),
          csrf_token: str = Form(""), db=Depends(get_db)):
    check_csrf(request, csrf_token)
    cur = reads.cursor(db)
    cur.execute("SELECT user_id, password_hash FROM users WHERE user_id=%s", (username.strip(),))
    row = cur.fetchone()
    cur.close()
    if row and verify_password(password, row["password_hash"]):
        request.session.clear()                    # 세션 고정 공격 방지
        request.session["user_id"] = row["user_id"]
        return _redirect("/feed")
    if not row:
        verify_dummy(password)
    return page(request, db, "login.html", layout="auth", active_page="login", current=None,
                status_code=401, error="아이디 또는 비밀번호가 올바르지 않습니다.")


@router.post("/signup")
def signup(request: Request, username: str = Form(...), display_name: str = Form(...),
           password: str = Form(...), confirm_password: str = Form(...),
           csrf_token: str = Form(""), db=Depends(get_db)):
    check_csrf(request, csrf_token)
    username, display_name = username.strip(), display_name.strip()

    def fail(msg):
        return page(request, db, "signup.html", layout="auth", active_page="signup",
                    current=None, status_code=400, error=msg)

    if not USER_ID_RE.match(username):
        return fail("아이디는 영문, 숫자, _ 로 3~30자여야 합니다.")
    if not (1 <= len(display_name) <= 50):
        return fail("이름은 1~50자로 입력해 주세요.")
    if not (8 <= len(password) <= 128):
        return fail("비밀번호는 8~128자여야 합니다.")
    if password != confirm_password:
        return fail("비밀번호 확인이 일치하지 않습니다.")

    cur = reads.cursor(db)
    try:
        cur.execute(
            "INSERT INTO users (user_id, password_hash, display_name) VALUES (%s, %s, %s)",
            (username, hash_password(password), display_name))
        db.commit()
    except mysql_errors.IntegrityError:
        db.rollback()
        return fail("이미 사용 중인 아이디입니다.")
    finally:
        cur.close()
    return _redirect("/login")


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form("")):
    check_csrf(request, csrf_token)
    request.session.clear()
    return _redirect("/login")


@router.post("/settings/password")
def password_update(request: Request, current_password: str = Form(...),
                    new_password: str = Form(...), confirm_password: str = Form(...),
                    csrf_token: str = Form(""), db=Depends(get_db)):
    check_csrf(request, csrf_token)
    current = reads.get_current_user(db, request)
    if not current:
        return _redirect("/login")

    def fail(msg):
        return page(request, db, "change_password.html", active_page="settings",
                    current=current, status_code=400, error=msg)

    cur = reads.cursor(db)
    cur.execute("SELECT password_hash FROM users WHERE user_id=%s", (current["user_id"],))
    row = cur.fetchone()
    if not row or not verify_password(current_password, row["password_hash"]):
        cur.close()
        return fail("현재 비밀번호가 올바르지 않습니다.")
    if not (8 <= len(new_password) <= 128):
        cur.close()
        return fail("새 비밀번호는 8~128자여야 합니다.")
    if new_password != confirm_password:
        cur.close()
        return fail("새 비밀번호 확인이 일치하지 않습니다.")
    cur.execute("UPDATE users SET password_hash=%s WHERE user_id=%s",
                (hash_password(new_password), current["user_id"]))
    db.commit()
    cur.close()
    return _redirect("/settings/password?changed=1")


# ---------------- 게시물 ----------------
def _image_ext(head: bytes):
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


@router.post("/posts")
def create_post(request: Request, image: UploadFile = File(...), caption: str = Form(""),
                csrf_token: str = Form(""), db=Depends(get_db)):
    check_csrf(request, csrf_token)
    current = reads.get_current_user(db, request)
    if not current:
        return _redirect("/login")

    def fail(msg):
        return page(request, db, "upload.html", active_page="upload", current=current,
                    status_code=400, upload_error=msg)

    caption = caption.strip()
    if len(caption) > 2200:
        return fail("캡션은 2200자 이하로 입력해 주세요.")
    data = image.file.read(MAX_IMAGE_BYTES + 1)
    if not data:
        return fail("사진을 선택해 주세요.")
    if len(data) > MAX_IMAGE_BYTES:
        return fail("사진은 8MB 이하만 올릴 수 있습니다.")
    ext = _image_ext(data[:16])
    if not ext:
        return fail("JPG, PNG, WEBP 형식만 올릴 수 있습니다.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / name
    path.write_bytes(data)
    try:
        cur = reads.cursor(db)
        cur.execute("INSERT INTO posts (author_id, image_path, caption) VALUES (%s, %s, %s)",
                    (current["user_id"], f"uploads/{name}", caption or None))
        db.commit()
        cur.close()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    return _redirect("/feed?uploaded=1")


def _require_post(cur, post_id: int):
    cur.execute("SELECT 1 AS ok FROM posts WHERE post_id=%s", (post_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="게시물을 찾을 수 없습니다.")


@router.post("/posts/{post_id}/comments", status_code=201)
def create_comment(post_id: int, request: Request, text: str = Form(...),
                   csrf_token: str = Form(""), x_csrf_token: str | None = Header(None),
                   db=Depends(get_db)):
    check_csrf(request, x_csrf_token or csrf_token)
    uid = require_user_id(request)
    text = text.strip()
    if not (1 <= len(text) <= 1000):
        raise HTTPException(status_code=400, detail="댓글은 1~1000자로 입력해 주세요.")
    cur = reads.cursor(db)
    _require_post(cur, post_id)
    cur.execute("INSERT INTO comments (post_id, author_id, text) VALUES (%s, %s, %s)",
                (post_id, uid, text))
    comment_id = cur.lastrowid
    cur.execute("SELECT created_at FROM comments WHERE comment_id=%s", (comment_id,))
    created = cur.fetchone()["created_at"]
    cur.execute("SELECT COUNT(*) AS n FROM comments WHERE post_id=%s", (post_id,))
    count = int(cur.fetchone()["n"])
    db.commit()
    cur.close()
    return {"comment": {"comment_id": comment_id, "author_id": uid, "text": text,
                        "created_at": reads._fmt(created)},
            "comment_count": count}


def _like_count(cur, post_id):
    cur.execute("SELECT COUNT(*) AS n FROM likes WHERE post_id=%s", (post_id,))
    return int(cur.fetchone()["n"])


@router.delete("/posts/{post_id}/comments/{comment_id}")
def delete_comment(post_id: int, comment_id: int, request: Request,
                   x_csrf_token: str | None = Header(None), db=Depends(get_db)):
    check_csrf(request, x_csrf_token)
    uid = require_user_id(request)
    cur = reads.cursor(db)
    try:
        # 작성자 조건을 DELETE에도 넣어 다른 사람의 댓글 삭제를 차단한다.
        cur.execute(
            "DELETE FROM comments WHERE comment_id=%s AND post_id=%s AND author_id=%s",
            (comment_id, post_id, uid))
        if cur.rowcount != 1:
            raise HTTPException(status_code=404, detail="삭제할 수 있는 댓글을 찾을 수 없습니다.")
        cur.execute("SELECT COUNT(*) AS n FROM comments WHERE post_id=%s", (post_id,))
        count = int(cur.fetchone()["n"])
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()
    return {"deleted": True, "comment_id": comment_id, "comment_count": count}


@router.post("/posts/{post_id}/likes")
def add_like(post_id: int, request: Request, x_csrf_token: str | None = Header(None),
             db=Depends(get_db)):
    check_csrf(request, x_csrf_token)
    uid = require_user_id(request)
    cur = reads.cursor(db)
    _require_post(cur, post_id)
    cur.execute("INSERT IGNORE INTO likes (post_id, user_id) VALUES (%s, %s)", (post_id, uid))
    db.commit()
    n = _like_count(cur, post_id)
    cur.close()
    return {"liked": True, "like_count": n}


@router.delete("/posts/{post_id}/likes")
def remove_like(post_id: int, request: Request, x_csrf_token: str | None = Header(None),
                db=Depends(get_db)):
    check_csrf(request, x_csrf_token)
    uid = require_user_id(request)
    cur = reads.cursor(db)
    _require_post(cur, post_id)
    cur.execute("DELETE FROM likes WHERE post_id=%s AND user_id=%s", (post_id, uid))
    db.commit()
    n = _like_count(cur, post_id)
    cur.close()
    return {"liked": False, "like_count": n}


# ---------------- 팔로우 ----------------
def _target_user(cur, user_id: str, me: str) -> str:
    cur.execute("SELECT user_id FROM users WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    if row["user_id"] == me:
        raise HTTPException(status_code=400, detail="자기 자신은 팔로우할 수 없습니다.")
    return row["user_id"]


def _followers(cur, user_id):
    cur.execute("SELECT COUNT(*) AS n FROM follows WHERE followee_id=%s", (user_id,))
    return int(cur.fetchone()["n"])


@router.post("/users/{user_id}/follow")
def follow(user_id: str, request: Request, x_csrf_token: str | None = Header(None),
           db=Depends(get_db)):
    check_csrf(request, x_csrf_token)
    me = require_user_id(request)
    cur = reads.cursor(db)
    target = _target_user(cur, user_id, me)
    cur.execute("INSERT IGNORE INTO follows (follower_id, followee_id) VALUES (%s, %s)", (me, target))
    db.commit()
    n = _followers(cur, target)
    cur.close()
    return {"user_id": target, "is_following": True, "followers_count": n}


@router.delete("/users/{user_id}/follow")
def unfollow(user_id: str, request: Request, x_csrf_token: str | None = Header(None),
             db=Depends(get_db)):
    check_csrf(request, x_csrf_token)
    me = require_user_id(request)
    cur = reads.cursor(db)
    target = _target_user(cur, user_id, me)
    cur.execute("DELETE FROM follows WHERE follower_id=%s AND followee_id=%s", (me, target))
    db.commit()
    n = _followers(cur, target)
    cur.close()
    return {"user_id": target, "is_following": False, "followers_count": n}
