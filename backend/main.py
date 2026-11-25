"""Backend integration (session + MySQL being implemented).

From group_proj/: python -m uvicorn backend.main:app --reload
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import backend.db  # noqa: F401  (.env를 먼저 읽기 위해 가장 먼저 import)
from backend.routers import actions, pages

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="FRAME · Backend")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["SESSION_SECRET"],
    same_site="lax",
    max_age=60 * 60 * 24 * 7,
)
app.state.templates = Jinja2Templates(directory=str(ROOT / "templates"))
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")
app.include_router(pages.router)
app.include_router(actions.router)


@app.get("/health")
def health():
    try:
        gen = backend.db.get_db()
        conn = next(gen)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        gen.close()
        ok = True
    except Exception:
        ok = False
    return {"status": "ok", "mode": "backend", "mysql_connected": ok}