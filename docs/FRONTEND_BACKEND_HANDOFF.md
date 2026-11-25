# FRAME v3 — 프론트엔드 → 백엔드 인수인계

> 팀원 전달용. 현재 `app/preview_main.py`는 **미리보기**, `backend/main.py`는 **연동 개발용 골격**입니다. MySQL 연동/실제 로그인/댓글/팔로우/좋아요는 아직 구현되지 않았습니다. `/health`를 확인해 실행 모드를 구분하세요.

## 시작 가이드 (Windows PowerShell)

작업 경로: `C:\Users\com\Desktop\jineon\dev_ws\database\group_proj`

```powershell
cd "C:\Users\com\Desktop\jineon\dev_ws\database\group_proj"
& "C:\Users\com\Desktop\jineon\venv\Scripts\python.exe" -m pip install -r requirements-backend.txt

# UI 확인: 로컬 저장 기능이 있는 v2 미리보기
& "C:\Users\com\Desktop\jineon\venv\Scripts\python.exe" -m uvicorn app.preview_main:app --reload

# 또는 백엔드 작업: 별도 터미널에서 미리보기 서버 중단 후 시작
& "C:\Users\com\Desktop\jineon\venv\Scripts\python.exe" -m uvicorn backend.main:app --reload
```

두 서버는 기본 포트 8000을 쓰므로 **동시에 같은 포트로 실행할 수 없습니다**. 병렬 실행 시 `--port 8001` 등을 사용하세요. v2와 v3의 화면 파일은 **공통**이며, `data-integration-mode`로 JS 동작을 분기합니다.

## 담당자별 소유권

| 담당 | 관리 대상 | 남기는 결과물 |
|---|---|---|
| 프론트엔드 | `templates/`, `static/css/`, `static/js/` | Jinja2 렌더링, 모달, JS 이벤트, 사용자 입력 UI |
| 백엔드 | `backend/` (또는 팀이 합의한 `app/routers/`), `.env` | 페이지 라우트, 인증/세션, DB 액세스, 업로드, JSON 응답 |
| DB | `sql/`, `docs/`의 ERD·정규화 자료 | MySQL DDL, 키·제약조건, 시드 데이터, SQL 쿼리 |

**규칙**: UI에서 `author_id`·`user_id`를 전달하더라도 쓰기 작업의 작성자/팔로워는 **세션에 저장된 ID만** 신뢰합니다. 백엔드 담당자가 `app/preview_main.py`를 변경하지 않아도 됩니다. `backend/read_service.py`의 샘플 조회 함수를 SQL로 변경하거나 동일 반환 형식을 유지하는 새 서비스를 주입하세요.

## 기능별 연결 맵

| 사용자 UI 동작 | 현재 프론트 라우트/호출 | 백엔드가 할 일 | 성공 후 반응 |
|---|---|---|---|
| 로그인 버튼 | `POST /login`, form | 해시 검증 → 세션 쿠키 발급 | `303 /feed` |
| 회원가입 | `POST /signup`, form | users INSERT + 해시 | `303 /login` |
| 피드 열기 | `GET /feed` | 본인 + 팔로잉의 posts SQL 조회, 최신순 | Jinja2 `posts`, `stories` 렌더 |
| 게시물 업로드 | `POST /posts`, multipart | 이미지 파일 저장, 경로로 posts INSERT | `303 /feed?uploaded=1` |
| 프로필/게시물 선택 | `GET /profile/{user_id}` | 프로필 데이터 + 작성 게시물 | 게시물 팝업은 화면 JS가 처리 |
| 댓글 쓰기 | `POST /posts/{id}/comments`, AJAX | comments INSERT, 인가 | JSON 반환 → 댓글 목록 추가 |
| 좋아요 누르기 | `POST` / `DELETE /posts/{id}/likes`, AJAX | likes INSERT/DELETE | JSON 반환 → 아이콘·숫자 갱신 |
| 팔로우/취소 | `POST` / `DELETE /users/{id}/follow`, AJAX | follows INSERT/DELETE | JSON 반환 → 버튼·팔로워 수 갱신 |
| ID 검색 | `GET /search?q=ali` | users 검색 (SQL 파라미터화) | 검색 결과 렌더 |
| 팔로워/팔로잉 | `GET /profile/{id}/followers` 등 | follows JOIN | 목록 렌더 |
| 비밀번호 변경 | `POST /settings/password`, form | 현재 비밀번호 검증 → 새 해시 UPDATE | `303 /settings/password` |
| 스토리 클릭·읽음 테두리 | JS, 현재 `localStorage` | 지금은 추가 서버 호출 불필요 | 모달, 회색 테두리 |
| 테마 변경 | JS, `localStorage` | 현재 서버 호출 불필요 | 테마 유지 |
| 프로필 사진 확대 | JS 모달 | avatar_url만 렌더링하면 됨 | X/Esc/뒤로가기 |

## 가장 먼저 합의할 것

1. 사용자 ID는 `users.user_id` (문자열, 유일), `display_name`은 별개로 처리.
2. 게시물 식별자(`post_id`)는 문자열화 가능한 값. 프론트가 숫자/문자열 둘 다 받아 처리함.
3. Jinja 템플릿에 전달하는 `current_user`, `posts`, `stories`, `profile_user`, `users` 객체 구조는 **API_CONTRACT.md** 준수.
4. 목록 필드(`posts`, `comments`, `users`)는 `None`이 아니라 `[]`로 전달.
5. 미구현 기능에서 가짜 성공 응답을 보내지 말 것. 제공된 `backend/routers/actions.py`가 현재 501을 반환하는 이유입니다.
6. 코드 합치기 전 Git 커밋 후 서로 충돌되는 `templates/`, `static/` 수정은 프론트 담당과 협의.

## 단계별 인수 테스트

- 단계 0: `GET /health` = `backend-scaffold`; `GET /feed`, `/profile/alice`, `/search?q=ali` 200.
- 단계 1: DB 접속·테이블 생성·시드 데이터로 조회 결과가 DB 기준으로 바뀌는지 확인.
- 단계 2: 서로 다른 계정으로 회원가입/로그인/로그아웃/비밀번호 변경 확인.
- 단계 3: 계정 A에서 계정 B 팔로우 → A의 피드에 B 게시물이 최신순으로 보이는지 확인.
- 단계 4: 실제 사진 업로드 → MySQL 게시물 행 + `static/uploads/` 파일 존재 → 프로필 팝업 조회.
- 단계 5: 댓글·좋아요 추가/취소 → 리로드 후에도 DB에서 상태 유지, 동일 좋아요/팔로우 중복 없음.
- 단계 6: 비로그인 POST 차단, 이미지 크기/형식 거부, SQL 인젝션 시도 차단, CSRF 보호와 예외 처리 확인.

### 주의: 개발 완료로 간주하지 않는 것

- 현재 `backend/main.py`는 **GET 샘플 데이터 화면만 보여주는 미완성 시작점**입니다. 로그인은 실제로 이루어지지 않습니다.
- 미리보기 `preview_data/posts.json` 및 `static/uploads`는 실제 DB 테이블이 아닙니다.
- 좋아요·팔로우·댓글의 UI 시연이 된다고 서버에 저장된 것은 아닙니다. `backend` 모드에서만 실제 요청이 나갑니다.
- `backend` 모드에서는 인증/CSRF/세션이 전혀 구성되지 않았으므로 **인터넷에 공개하지 마세요**.
