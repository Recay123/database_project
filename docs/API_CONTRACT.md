# FRAME v3/v4 — HTTP 및 Jinja2 계약 (팀 공통)

## 0. 구조 / 데이터 전달 방식

- **서버 렌더링**: FastAPI가 `templates/*.html`을 Jinja2로 렌더링해 브라우저에 전달.
- **페이지 전환**: GET 페이지 URL 이동 (`<a href=...>`).
- **폼 제출**: 로그인·회원가입·비밀번호 변경·업로드는 HTML form POST, 성공 시 303 리다이렉트.
- **부분 갱신**: 댓글·좋아요·팔로우는 JS `fetch()` → JSON 응답으로 화면 갱신.
- **프론트-only**: 게시물 팝업·프로필 사진 팝업·테마·스토리 읽음 링; 현재 DB 불필요. 스토리 지속/동기화는 별도 확장.
- **오류**: JSON API는 `4xx/5xx` + `{ "detail": "사용자에게 표시할 한국어 메시지" }`. HTML 폼은 오류 템플릿 렌더(4xx) 또는 오류 정보를 보존한 303 리다이렉트.

## 1. 템플릿 컨텍스트 스키마

모든 화면에 필요한 공통 값:

```json
{
  "layout": "app",
  "active_page": "feed",
  "integration_mode": "backend",
  "csrf_token": "<signed token from session>",
  "current_user": {"user_id": "jineon", "display_name": "Jineon Kim", "avatar_url": "/static/uploads/avatar.jpg", "bio": "hello"},
  "suggested_users": [{"user_id":"alice", "display_name":"Alice Park", "avatar_url":"/static/images/demo/avatar-alice.svg"}]
}
```

> 공개 페이지(`/login`, `/signup`)에서는 `layout: "auth"`. 실제 백엔드에서는 인증된 세션 사용자를 `current_user`로 설정. 로그인 전 페이지에 따라 `current_user`는 null 허용하되 **앱 레이아웃에서 null 상태로 렌더링하지 않도록** 로그인으로 리다이렉트.

사용자(User) 객체 (표시/검색/프로필):

```json
{
 "user_id":"alice", "display_name":"Alice Park", "avatar_url":"/static/uploads/avatar-a.jpg",
 "bio":"sea lover", "location":"Busan", "followers_count":20,
 "following_count":10, "post_count":3, "is_following":false
}
```

게시물(Post) 객체 (피드/프로필/모달):

```json
{
 "post_id":105, "author_id":"alice", "author_name":"Alice Park",
 "author_avatar":"/static/uploads/avatar-a.jpg",
 "image_url":"/static/uploads/photo-105.jpg", "image_alt":"사진",
 "caption":"사진 설명 #sea", "created_at":"2026-11-21 15:00", "location":"Busan",
 "like_count":2, "comment_count":1, "is_liked":false,
 "comments":[{"comment_id":12, "author_id":"jineon", "text":"멋져요", "created_at":"2026-11-21 15:04"}]
}
```

스토리(Story) 표시 객체 (현재는 선택적 샘플/브라우저 읽음 처리):

```json
{"user_id":"alice", "display_name":"Alice Park", "avatar_url":"/static/uploads/avatar-a.jpg",
 "story_image":"/static/uploads/story1.jpg", "story_caption":"오늘의 기록"}
```

페이지별 추가 컨텍스트:

| GET 경로 | 템플릿 | 추가 키 |
|---|---|---|
| `/login` | `login.html` | `layout='auth'` |
| `/signup` | `signup.html` | `layout='auth'` |
| `/feed` | `feed.html` | `posts: Post[]`, `stories: Story[]` (최신순) |
| `/profile/{user_id}` | `profile.html` | `profile_user: User`, `posts: Post[]`, `is_own_profile: bool` |
| `/profile/{user_id}/followers` | `follows.html` | `profile_user`, `mode='followers'`, `users: User[]` |
| `/profile/{user_id}/following` | `follows.html` | `profile_user`, `mode='following'`, `users: User[]` |
| `/search?q=alice` | `search.html` | `q: str`, `users: User[]` |
| `/upload` | `upload.html` | `upload_error: str` (빈 문자열이면 오류 없음) |
| `/settings/password` | `change_password.html` | 공통 값만 |

## 2. HTML POST 계약 (body: application/x-www-form-urlencoded 또는 multipart/form-data)

| URL | method | FormData의 name 키 | 성공 시 |
|---|---|---|---|
| `/login` | POST | `username`, `password`, `csrf_token` | 쿠키 발급, 303 `/feed` |
| `/signup` | POST | `username`, `display_name`, `password`, `confirm_password`, `csrf_token` | DB user INSERT, 303 `/login` |
| `/settings/profile` | POST | `display_name` (1~50자), `bio` (최대 200자, 비워도 됨), `csrf_token` | 세션 사용자의 프로필 저장, 303 `/settings/password` |
| `/settings/password` | POST | `current_password`, `new_password`, `confirm_password`, `csrf_token` | 303 `/settings/password` |
| `/posts` | POST multipart | `image` (jpg/png/webp, 최대 8MB), `caption` (최대 2200자), `csrf_token` | 파일 저장+DB INSERT, 303 `/feed?uploaded=1` |

**서버는 입력 검증, CSRF 검증, 세션/권한 검사를 반드시 재수행**해야 함. 캡션/댓글은 SQL 파라미터 바인딩, 렌더링은 Jinja 자동 이스케이프 유지. 회원가입 시 `username`은 `user_id`에 대응 (이름 `display_name`과 혼동 금지).

## 3. AJAX JSON 계약

Same-origin, 세션 쿠키 포함(`credentials: 'same-origin'`), `Accept: application/json` 및 `X-CSRF-Token` 헤더 지원. `DELETE`도 CSRF 검증.

### 댓글 작성

`POST /posts/105/comments` (form fields `text`, `csrf_token`) → HTTP 201

```json
{"comment":{"comment_id":208,"author_id":"jineon","text":"오늘 너무 좋다","created_at":"2026-11-21 17:00"},"comment_count":3}
```

### 좋아요 (멱등적 추가 및 취소)

`POST /posts/105/likes` → HTTP 200

```json
{"liked":true,"like_count":3}
```

`DELETE /posts/105/likes` → HTTP 200

```json
{"liked":false,"like_count":2}
```

### 팔로우 (승인 없는 공개 팔로우)

`POST /users/alice/follow` → HTTP 200

```json
{"user_id":"alice","is_following":true,"followers_count":21}
```

`DELETE /users/alice/follow` → HTTP 200

```json
{"user_id":"alice","is_following":false,"followers_count":20}
```

### 지켜야 할 세부 규칙

- 인증 정보는 **브라우저가 보내는 `author_id`가 아니라 서버의 세션**에서 확인.
- 이미 좋아요/팔로우 중이면 POST 재시도해도 중복 레코드를 만들지 않음 (UNIQUE/복합 PK).
- 본인 자신을 팔로우할 수 없음.
- 좋아요/댓글 대상 게시물이 없으면 404. 미로그인 시 401 또는 로그인 리다이렉트(HTML 폼).
- JSON 응답의 숫자는 정수, 상태는 boolean (문자열 "true" 아님).
- CSRF 토큰은 사용자 세션과 바인딩된 **실제 토큰**을 넣어야 하며 샘플 코드의 빈 토큰은 유효하지 않음.
- `created_at`은 DB의 datetime을 사람이 읽기 쉬운 문자열로 포맷해서 전달.
- `image_url`, `avatar_url`은 브라우저에서 요청 가능한 경로. 서버 디스크의 절대 경로를 반환하지 않음.

## 4. 팀 간 변경 절차

필드나 URL을 변경해야 하면 프론트엔드 담당자에게 알리고 **API_CONTRACT.md, Jinja 템플릿, JS, 백엔드 라우트**를 같은 PR/커밋에서 수정. DB 테이블/컬럼명은 프론트엔드에 직접 노출할 필요 없음. `read_service.py`에서 DB 결과를 이 화면 데이터 구조로 매핑.


## 5. FRAME v4 추가 계약

동일 출처 세션 쿠키 + `X-CSRF-Token` 헤더 필수. 모두 실제 백엔드 서버에서 사용.

| HTTP | URL | 입력 | 응답 | 권한 |
|---|---|---|---|---|
| PATCH | `/posts/{post_id}` | FormData `caption` (0~2200자) | `{post_id, caption, updated}` | 작성자 |
| PATCH | `/posts/{post_id}/comments/{comment_id}` | FormData `text` (1~1000자) | `{comment:{comment_id, post_id, author_id, text}, updated}` | 댓글 작성자 |
| POST | `/users/me/avatar` | multipart `avatar` (JPG/PNG/WEBP, 최대 8MB) | `{avatar_url, user_id, updated}` | 로그인 사용자 |

게시물 및 댓글 삭제는 기존 v3 API를 그대로 사용함. `users.avatar_url`이 이미 존재하므로 마이그레이션은 불필요함.
회원가입 성공 시 세션 플래시(`signup_success`)를 사용하며 기존 `303 /login` URL을 유지하여 성공 메시지를 표시함.
