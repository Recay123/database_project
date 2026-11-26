# FRAME v4 프론트/백엔드 통합 패치

기준: `Recay123/database_project` `main` 브랜치, 2026-11-26 확인 SHA `b8c2c0d2e31ac7b70b32c56d534f8f0612bb666d`.

## 변경 기능

- 사용자 가입 성공 시 `회원가입이 완료됐어요!` 안내 (서버의 성공 리다이렉트와 연결)
- 본인 게시물의 `···` 메뉴로 캡션 수정 및 게시물 삭제
- 본인 댓글의 인라인 수정 폼, 기존 삭제 기능 유지
- 내 프로필에서 프로필 사진 업로드/변경, 기존 확대 팝업 유지
- `@아이디` 자동 링크 기능은 기존 `app.js`에 존재하므로 유지
- 작성자 권한·CSRF 검증은 프론트가 아닌 서버에서 재검증
- DB 변경 없음 (`users.avatar_url` 기존 컬럼 재사용)

## 적용 방법

1. `git status`로 변경 사항 확인. 수정 중인 파일이 있으면 먼저 별도 커밋 또는 백업.
2. 이 ZIP의 **전체 파일**을 `group_proj_team/` 최상위에 압축 해제. `backend/routers/v4_actions.py`, `static/js/v4.js`, `static/css/v4.css`, `tests/test_v4.py`는 새 파일로 추가, 기존 파일 덮어쓰기 없음.
3. `python apply_frame_v4.py` 실행. 기존 8개 파일 및 `.gitignore`은 검증 후 패치하며 기존 상태는 `.frame_v4_backup/`에 자동 백업.
4. `git diff --check`, 테스트, 브라우저에서 수동 동작 확인.
5. `git add backend/routers/v4_actions.py backend/main.py backend/routers/actions.py backend/routers/pages.py static/js/v4.js static/css/v4.css tests/test_v4.py .gitignore templates/base.html templates/feed.html templates/profile.html templates/login.html docs/API_CONTRACT.md` 등으로 Git 등록 후 커밋 및 푸시.

> 이미 v4가 적용된 상태에서 `apply_frame_v4.py`를 재실행하면 안전하게 중단하도록 설계. 최신 팀원 코드의 앵커가 바뀌면 역시 중단하며, 무조건 덮어쓰지 않음.

## 새 HTTP API

- `PATCH /posts/{post_id}`: FormData `caption`
- `PATCH /posts/{post_id}/comments/{comment_id}`: FormData `text`
- `POST /users/me/avatar`: multipart `avatar`

백엔드 모드: `python -m uvicorn backend.main:app --reload`, 프로젝트 루트의 `.env`에 MySQL 연결 정보와 `SESSION_SECRET` 필수. 미리보기 서버는 기존 `app.preview_main:app` 실행. 프론트는 백엔드 모드에서만 저장 API 호출.

## 주의

- 다른 사람의 게시물/댓글에 수정·삭제 컨트롤을 제공하지 않으며, 서버가 소유권을 검사.
- 기존 프론트의 스토리 표시, ID 검색, 테마, 댓글 삭제, 이미지 팝업, 좋아요, 팔로우는 유지.
- 프로필 사진은 새로운 서버 파일로 저장되며 예전 프로필 이미지의 자동 삭제는 아직 제공하지 않음.
- GitHub 저장소에 대한 ChatGPT 연결은 `push: false`여서 실제 Push는 Windows의 인증된 Git으로 진행해야 함.

DB 없이 실행할 수 있는 신규 테스트: `python -m unittest discover -s tests -p test_v4.py -v`
