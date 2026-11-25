# FRAME v3 — 프론트엔드 / 백엔드 연동 핸드오프

**바로 전달:** `docs/FRONTEND_BACKEND_HANDOFF.md` → `docs/API_CONTRACT.md` → `docs/DB_TEAM_HANDOFF.md`를 확인해주세요.

- 프론트엔드 UI와 v2 미리보기 기능은 유지됩니다. `app/preview_main.py` 사용.
- **새로 추가**된 `backend/` 폴더가 백엔드 팀원 작업 공간이며, `backend/main.py`를 별도로 실행합니다.
- `backend/read_service.py`의 샘플 조회를 SQL로 변경하고, `backend/routers/actions.py`의 501 스텁을 실제 API로 구현하면 됩니다.
- 클라이언트는 `backend` 모드에서만 실제 서버 POST/DELETE 요청을 보내고, `preview` 모드는 기존 데모로 남습니다.
- **현재 실DB 기능은 완성되지 않았습니다.** 인증/세션/CSRF/DB 트랜잭션은 백엔드 팀원이 구현해야 합니다.

## 실행 명령

```powershell
cd "C:\Users\com\Desktop\jineon\dev_ws\database\group_proj"
& "C:\Users\com\Desktop\jineon\venv\Scripts\python.exe" -m pip install -r requirements-backend.txt

# UI 데모 (포트 8000)
& "C:\Users\com\Desktop\jineon\venv\Scripts\python.exe" -m uvicorn app.preview_main:app --reload

# 백엔드 개발 서버 (별도 터미널 / 8001)
& "C:\Users\com\Desktop\jineon\venv\Scripts\python.exe" -m uvicorn backend.main:app --reload --port 8001
```

- 미리보기: http://127.0.0.1:8000/feed
- 백엔드 스캐폴드: http://127.0.0.1:8001/feed (GET은 샘플 데이터, POST는 501)
- API 문서: http://127.0.0.1:8001/docs
- 자동 테스트: `python -m pytest -q tests/test_handoff.py` (`pytest`, `httpx` 설치 필요)

---

## 이전 v2 안내 (기능 시연 설명 및 디자인 소개)

# FRAME — Frontend v2 기능 확장 (Database Term Project)

기존 FRAME 프론트엔드 v1을 확장한 **FastAPI + Jinja2 미리보기**입니다. DB가 아직 완성되지 않아도 화면을 테스트할 수 있습니다. `app/main.py`가 있더라도 수정하지 않으며, 프론트 미리보기는 `app/preview_main.py`에서 실행합니다.

## 1. 이번 버전의 여섯 기능

| 기능 | 사용 방법 | 현재 저장 방식 |
| --- | --- | --- |
| 게시물 업로드 | 새 게시물 → JPG/PNG/WEBP 선택 → 캡션 → 공유하기 | `static/uploads/` 이미지와 `preview_data/posts.json`에 로컬 저장. 새로고침 후에도 피드/내 프로필 유지 |
| 스토리 확인/읽음 표시 | 피드의 스토리 원 클릭 → 전체 화면 감상 → `X`/이전/다음 | 본 브라우저의 `localStorage`에 읽음 표시 저장(읽은 스토리는 회색 테두리) |
| 게시물 팝업 | 프로필 사진 그리드에서 게시물 클릭 → 상세 다이얼로그 | 샘플 및 업로드 게시물 표시. `X`/← 돌아가기/브라우저 뒤로가기/Esc로 닫기 |
| 화면 테마 변경 | 설정 → 화면 컬러 테마에서 Forest/Ocean/Lavender/Coral 선택 | 본 브라우저 `localStorage`에 저장, 모든 페이지에 유지 |
| ID 검색 | 왼쪽 메뉴/모바일 하단의 `ID 검색` → 검색어 입력 | `/search?q=...`에서 샘플 `USERS`의 **user_id** 부분 일치 (대소문자 무관) |
| 프로필 사진 팝업 | 프로필 상단 큰 사진, 피드/검색 결과/사이드바 아바타 클릭 | 확대 다이얼로그; `X`/← 돌아가기/브라우저 뒤로가기/Esc로 닫기 |

**중요한 구분:** 업로드는 *미리보기용 서버의 로컬 파일 저장*까지 동작합니다. MySQL의 `posts` 테이블에 기록하지 않습니다. 스토리 이미지는 별도 Story 테이블이 아니라 각 사용자 샘플 게시물 이미지를 임시로 재사용합니다. 스토리 조회 기록, 테마, 좋아요, 팔로우는 브라우저 로컬 상태입니다. 실제 로그인/회원가입/댓글/팔로우/비밀번호 변경은 아직 백엔드·DB에 저장되지 않습니다.

## 2. Windows / VS Code에서 v2 적용하기

현재 프로젝트 위치:

`C:\Users\com\Desktop\jineon\dev_ws\database\group_proj`

1. 기존 파일을 수정했다면 백업 또는 Git 커밋을 먼저 만듭니다.
2. **업데이트 전용 ZIP** 안의 파일과 폴더를 위 `group_proj` 폴더에 **병합**합니다. 같은 이름의 기존 v1 파일들은 v2로 교체됩니다. 다른 팀원의 `app/main.py`, `sql/`, `.env`는 ZIP에 포함되지 않으며 건드리지 않습니다.
3. `group_proj`에서 VS Code 터미널 실행:

```powershell
cd "C:\Users\com\Desktop\jineon\dev_ws\database\group_proj"

# PowerShell의 Activate.ps1 정책 에러를 피하려면 venv Python 직접 실행
& "C:\Users\com\Desktop\jineon\venv\Scripts\python.exe" -m pip install "fastapi[standard]" jinja2
& "C:\Users\com\Desktop\jineon\venv\Scripts\python.exe" -m uvicorn app.preview_main:app --reload
```

기존 가상환경이 없다면 먼저 `py -3 -m venv "C:\Users\com\Desktop\jineon\venv"` 로 만듭니다.

**확인할 주소**

- 피드/스토리: <http://127.0.0.1:8000/feed>
- 내 프로필/게시물 팝업: <http://127.0.0.1:8000/profile/jineon>
- 사진 업로드: <http://127.0.0.1:8000/upload>
- ID 검색: <http://127.0.0.1:8000/search>
- 화면 테마 변경: <http://127.0.0.1:8000/settings/password>

## 3. 백엔드 담당자와 합의할 데이터/라우트

| 기능 | HTTP / 화면 | 입력 / 반환 | 현재 구현 구분 |
| --- | --- | --- | --- |
| 사용자 검색 | `GET /search?q=ali` | `q`: user_id의 검색 문자열. 템플릿에 `users` 반환 | 목 데이터 필터링 |
| 게시물 업로드 | `POST /posts` | `multipart/form-data`: `image` 파일과 `caption` 텍스트 | 미리보기 서버 파일/JSON 저장 → 303 `/feed?uploaded=1` |
| 피드 | `GET /feed` | `posts`, `stories`, `current_user` | Mock POST + 로컬 업로드 합침 |
| 프로필 | `GET /profile/{user_id}` | `profile_user`, `posts`, `is_own_profile` | Mock POST + 로컬 업로드 합침 |
| 게시물 모달 | 별도 서버 요청 없음(v2) | `posts` 객체를 Jinja `tojson`으로 전달 | 프론트 JS에서 모달 렌더링 |
| 스토리 모달 | 별도 서버 요청 없음(v2) | `stories` 각 원소: `user_id`, `display_name`, `avatar_url`, `story_image`, `story_caption` | 실서비스에서는 Story API/DB 필요 |
| 프로필 사진 모달 | 별도 서버 요청 없음 | `avatar_url`, `display_name` | 프론트 JS |
| 테마 | 설정 페이지 | `forest`, `ocean`, `lavender`, `coral` | localStorage. 계정 간 동기화 필요 시 user 설정 API 추가 |

### 게시물 예시

```json
{
  "post_id": 105,
  "author_id": "alice",
  "author_name": "Alice Park",
  "author_avatar": "/static/images/demo/avatar-alice.svg",
  "image_url": "/static/images/demo/coast.svg",
  "image_alt": "해안 풍경",
  "caption": "바다를 보며 찍은 사진 #sea",
  "created_at": "12분 전",
  "location": "Busan, Korea",
  "like_count": 248,
  "comment_count": 2,
  "is_liked": false,
  "comments": [{"author_id": "jineon", "text": "멋져요!"}]
}
```

필수 DB 스키마와 기능이 확정되면 백엔드 팀원은 `preview_main.py` 라우트를 실제 MySQL 기반 라우터로 치환하거나 `app/main.py`에 통합하면 됩니다. HTML 입력 필드 명칭은 `image`, `caption`, `q`를 유지하는 것을 권장합니다.

### DB 담당 팀원에게 추가로 확인할 내용

- ID 검색은 기존 `users.user_id`를 이용하므로 새 테이블이 필요 없습니다. 인덱스/검색 범위는 협의하세요.
- **실제 스토리 기능**을 구현하려면 `stories(story_id, author_id, image_path, created_at, expires_at)` 등 별도 엔티티가 필요할 수 있고, 사용자 간 **읽음 상태를 동기화**하려면 `story_views(story_id, viewer_id, viewed_at)` 같은 관계 테이블이 필요합니다. 지금 v2의 회색 링은 브라우저에만 유지됩니다.
- 업로드는 반드시 인증된 사용자 ID에서 `author_id`를 가져오도록 변경하세요. 미리보기에서는 고정 `jineon` 계정만 사용합니다.
- 실제 서비스에서는 파일 업로드 크기 제한, 확장자/파일 형식 검증, 저장 위치/파일 권한, SQL 파라미터 바인딩, 로그인/세션, CSRF 보호 등을 백엔드에서 구현해야 합니다.

## 4. 새로 추가/수정된 파일

```text
group_proj/
  app/
    preview_main.py        # /posts POST 업로드, /search GET 추가
    preview_store.py       # 로컬 미리보기 파일/JSON 저장
  templates/
    base.html              # 공통 팝업 + 검색 내비게이션
    feed.html              # 스토리 클릭/팝업, 아바타 버튼
    profile.html           # 게시물 선택/아바타 팝업
    search.html            # 신규 ID 검색 페이지
    upload.html            # 업로드 오류/로컬 저장 안내
    change_password.html   # 컬러 테마 선택 UI
  static/
    css/app.css            # 모달/테마/검색 스타일
    js/app.js              # 인터랙션 로직
    uploads/               # 미리보기 업로드 이미지 (실행 시 생성)
  preview_data/
    posts.json             # 미리보기 업로드 메타데이터 (실행 시 생성)
```

팀 Git에 업로드 이미지와 미리보기 데이터를 올리지 않도록 `.gitignore`에 아래 항목을 **추가**하는 것을 추천합니다(기존 `.gitignore` 내용은 유지):

```gitignore
/static/uploads/*
!/static/uploads/.gitkeep
/preview_data/*
!/preview_data/.gitkeep
__pycache__/
*.pyc
```

## 5. 테스트 포인트

- `feed` 스토리 클릭 → 확대 → X 닫기 → 테두리 회색으로 유지
- `profile/jineon` 게시물 클릭 → 팝업 확인 → 브라우저 **뒤로가기** → 프로필 유지
- 프로필 사진 클릭 → 크게 보기 → X 닫기
- 설정에서 Ocean 선택 → 다른 페이지 접속 → Ocean 유지
- 검색창에 `ali` 입력 → `@alice` 결과 클릭
- 업로드에서 JPG/PNG/WEBP 8MB 이하 파일 선택 → 이미지 미리보기 → 공유하기 → 피드 상단에 새 게시물 → 새로고침 및 내 프로필에서도 유지

이미지를 삭제하거나 미리보기 데이터를 초기화하려면 **서버 종료 후** `preview_data/posts.json`과 `static/uploads/` 내 실제 업로드 이미지를 삭제하면 됩니다. 샘플 SVG는 삭제하지 마세요.
