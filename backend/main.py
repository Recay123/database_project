"""FRAME application with signed sessions and MySQL-backed routes.

From group_proj/: python -m uvicorn backend.main:app --reload
"""
import logging
import os
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from mysql.connector import Error as MySQLError
from starlette.middleware.sessions import SessionMiddleware

from backend.db import get_db
from backend.routers import actions, pages, v4_actions

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
app.include_router(v4_actions.router)
logger = logging.getLogger(__name__)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    return JSONResponse({"detail": "요청 형식이 올바르지 않습니다."}, status_code=422)


@app.exception_handler(MySQLError)
async def database_error(request, exc):
    logger.error("MySQL request failed (errno=%s)", exc.errno)
    return JSONResponse({"detail": "데이터베이스 요청을 처리할 수 없습니다."}, status_code=503)


@app.get("/health")
def health():
    try:
        with closing(get_db()) as connections:
            with next(connections).cursor() as cur:
                cur.execute("SELECT 1")
                ok = cur.fetchone() == (1,)
    except (MySQLError, KeyError, ValueError):
        ok = False
    return {"status": "ok", "mode": "backend", "mysql_connected": ok}
