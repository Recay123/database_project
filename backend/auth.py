"""Password hashing, CSRF helpers, session user id."""
import hmac
import secrets

from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from pwdlib.exceptions import HashVerificationError, UnknownHashError

from backend.db import get_db
from backend.read_service import get_current_user

_ph = PasswordHash.recommended()
_DUMMY_HASH = _ph.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bool(_ph.verify(password, password_hash))
    except (HashVerificationError, UnknownHashError, ValueError):
        return False


def verify_dummy(password: str) -> None:
    """존재하지 않는 ID로 시도해도 응답 시간이 비슷하도록."""
    verify_password(password, _DUMMY_HASH)


def require_user_id(request: Request, db=Depends(get_db)) -> str:
    user = get_current_user(db, request)
    if not user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return user["user_id"]


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return token


def check_csrf(request: Request, submitted) -> None:
    expected = request.session.get("csrf")
    if not expected or not submitted or not hmac.compare_digest(
        expected.encode("utf-8"), submitted.encode("utf-8")
    ):
        raise HTTPException(
            status_code=403,
            detail="잘못된 요청입니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.",
        )
