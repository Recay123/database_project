"""Jinja2 page routes. 템플릿 변수 이름은 프론트와의 계약."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend import read_service as reads
from backend.auth import csrf_token as issue_csrf
from backend.db import get_db

router = APIRouter()
_UNSET = object()


def page(request, db, template, *, layout="app", active_page="", status_code=200,
         current=_UNSET, **data):
    if current is _UNSET:
        current = reads.get_current_user(db, request)
    context = {
        "integration_mode": "backend", "layout": layout, "active_page": active_page,
        "current_user": current,
        "suggested_users": reads.get_suggested_users(db, current["user_id"]) if current else [],
        "csrf_token": issue_csrf(request),
        **data,
    }
    return request.app.state.templates.TemplateResponse(
        request=request, name=template, context=context, status_code=status_code)


def _login_redirect():
    return RedirectResponse(url="/login", status_code=303)


@router.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/feed", status_code=302)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db=Depends(get_db)):
    current = reads.get_current_user(db, request)
    if current:
        return RedirectResponse(url="/feed", status_code=303)
    return page(request, db, "login.html", layout="auth", active_page="login", current=None,
                registered=bool(request.session.pop("signup_success", False)))


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, db=Depends(get_db)):
    current = reads.get_current_user(db, request)
    if current:
        return RedirectResponse(url="/feed", status_code=303)
    return page(request, db, "signup.html", layout="auth", active_page="signup", current=None)


@router.get("/feed", response_class=HTMLResponse)
def feed_page(request: Request, db=Depends(get_db)):
    current = reads.get_current_user(db, request)
    if not current:
        return _login_redirect()
    posts = reads.get_feed(db, current["user_id"])
    return page(request, db, "feed.html", active_page="feed", current=current,
                posts=posts, stories=reads.get_stories(posts))


@router.get("/search", response_class=HTMLResponse)
def search_page(request: Request, q: str = "", db=Depends(get_db)):
    current = reads.get_current_user(db, request)
    if not current:
        return _login_redirect()
    q = q.strip()[:60]
    return page(request, db, "search.html", active_page="search", current=current, q=q,
                users=reads.search_users(db, q, current["user_id"]) if q else [])


@router.get("/profile/{user_id}", response_class=HTMLResponse)
def profile_page(request: Request, user_id: str, db=Depends(get_db)):
    current = reads.get_current_user(db, request)
    if not current:
        return _login_redirect()
    profile_user = reads.get_user(db, user_id, current["user_id"])
    if not profile_user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    own = profile_user["user_id"] == current["user_id"]
    return page(request, db, "profile.html", active_page="profile" if own else "", current=current,
                profile_user=profile_user,
                posts=reads.get_user_posts(db, profile_user["user_id"], current["user_id"]),
                is_own_profile=own)


@router.get("/profile/{user_id}/{mode}", response_class=HTMLResponse)
def follow_list_page(request: Request, user_id: str, mode: str, db=Depends(get_db)):
    if mode not in ("followers", "following"):
        raise HTTPException(status_code=404, detail="목록을 찾을 수 없습니다.")
    current = reads.get_current_user(db, request)
    if not current:
        return _login_redirect()
    profile_user = reads.get_user(db, user_id, current["user_id"])
    if not profile_user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    own = profile_user["user_id"] == current["user_id"]
    return page(request, db, "follows.html", active_page="profile" if own else "", current=current,
                profile_user=profile_user, mode=mode,
                users=reads.get_follow_users(db, profile_user["user_id"], mode, current["user_id"]))


@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request, db=Depends(get_db)):
    current = reads.get_current_user(db, request)
    if not current:
        return _login_redirect()
    return page(request, db, "upload.html", active_page="upload", current=current, upload_error="")


@router.get("/settings/password", response_class=HTMLResponse)
def password_page(request: Request, db=Depends(get_db)):
    current = reads.get_current_user(db, request)
    if not current:
        return _login_redirect()
    return page(request, db, "change_password.html", active_page="settings", current=current,
                success=request.query_params.get("changed") == "1")