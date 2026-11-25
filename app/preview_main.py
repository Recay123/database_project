"""Database-free FastAPI demo, with local preview-only photo upload.

Run from group_proj/: python -m uvicorn app.preview_main:app --reload
Actual auth, SQL persistence and per-user permissions belong to the backend team.
"""
from copy import deepcopy
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.mock_data import CURRENT_USER, POSTS, USERS
from app.preview_store import read_posts, store_post

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="FRAME · Frontend Preview")
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))


def page(request: Request, template: str, *, layout: str = "app", active_page: str = "", **data):
    context = {"layout": layout, "active_page": active_page, "current_user": CURRENT_USER, "integration_mode": "preview",
               "suggested_users": [USERS["mina"], USERS["noah"]], **data}
    return templates.TemplateResponse(request=request, name=template, context=context)


def all_posts():
    return read_posts() + deepcopy(POSTS)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/feed", status_code=302)


@app.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return page(request, "login.html", layout="auth", active_page="login")


@app.get("/signup", response_class=HTMLResponse)
def signup(request: Request):
    return page(request, "signup.html", layout="auth", active_page="signup")


@app.get("/feed", response_class=HTMLResponse)
def feed(request: Request):
    posts = all_posts()
    stories = []
    for user in USERS.values():
        recent = next((p for p in posts if p["author_id"] == user["user_id"]), None)
        stories.append({**user, "story_image": recent["image_url"] if recent else user["avatar_url"],
                        "story_caption": recent["caption"] if recent else "오늘의 순간"})
    return page(request, "feed.html", active_page="feed", posts=posts, stories=stories)


@app.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = ""):
    q = q.strip()[:60]
    users = [u for u in USERS.values() if q.casefold() in u["user_id"].casefold()] if q else []
    return page(request, "search.html", active_page="search", q=q, users=deepcopy(users))


@app.get("/profile/{user_id}", response_class=HTMLResponse)
def profile(request: Request, user_id: str):
    profile_user = USERS.get(user_id)
    if not profile_user:
        raise HTTPException(status_code=404, detail="User not found")
    posts = [p for p in all_posts() if p["author_id"] == user_id]
    return page(request, "profile.html", active_page="profile" if user_id == CURRENT_USER["user_id"] else "",
                profile_user=deepcopy(profile_user), posts=posts, is_own_profile=user_id == CURRENT_USER["user_id"])


@app.get("/profile/{user_id}/{mode}", response_class=HTMLResponse)
def follow_list(request: Request, user_id: str, mode: str):
    if mode not in ("followers", "following"):
        raise HTTPException(status_code=404, detail="Unknown list")
    profile_user = USERS.get(user_id)
    if not profile_user:
        raise HTTPException(status_code=404, detail="User not found")
    visible_users = [u for u in USERS.values() if u["user_id"] != user_id]
    return page(request, "follows.html", active_page="profile" if user_id == CURRENT_USER["user_id"] else "",
                profile_user=deepcopy(profile_user), mode=mode, users=deepcopy(visible_users))


@app.get("/upload", response_class=HTMLResponse)
def upload(request: Request, error: str = ""):
    return page(request, "upload.html", active_page="upload", upload_error=error)


@app.post("/posts")
async def create_post(image: UploadFile = File(...), caption: str = Form("")):
    if len(caption) > 2200:
        return RedirectResponse(url="/upload?error=caption", status_code=303)
    try:
        await store_post(image, caption, CURRENT_USER)
    except ValueError:
        return RedirectResponse(url="/upload?error=image", status_code=303)
    finally:
        await image.close()
    return RedirectResponse(url="/feed?uploaded=1", status_code=303)


@app.get("/settings/password", response_class=HTMLResponse)
def password_settings(request: Request):
    return page(request, "change_password.html", active_page="settings")


@app.get("/health")
def health():
    return {"status": "ok", "mode": "frontend-preview", "local_preview_uploads": True}
