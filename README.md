# FRAME

FRAME은 사진과 캡션을 공유하고, 내가 팔로우하는 계정의 게시물을 최신순으로 볼 수 있는 팀 프로젝트입니다. FastAPI, Jinja2, MySQL을 사용합니다.

## 팀원 실행 방법

1. 최신 `main`을 받은 뒤 VS Code에서 프로젝트 폴더를 엽니다.
2. Python 3.11 이상과 MySQL을 준비합니다.
3. 프로젝트 루트의 `.env`에 `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `SESSION_SECRET`을 설정합니다. 처음 설치하는 팀원은 [백엔드 실행 안내](docs/BACKEND_RUN.md)에 따라 빈 데모 DB에 `sql/schema.sql`과 `sql/seed.sql`을 적용합니다.
4. VS Code의 터미널에서 실행합니다.

```powershell
python -m pip install -r requirements-backend.txt
python -m uvicorn backend.main:app --reload
```

[로그인 화면](http://127.0.0.1:8000/login)에서 시작합니다. [연결 상태](http://127.0.0.1:8000/health)에서 `"mysql_connected": true`가 나오면 DB 연결이 된 상태입니다.

