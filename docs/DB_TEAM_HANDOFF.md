# DB 팀원에게 전달할 스키마/SQL 합의안

> 과제 원문 필수: `User`, `Follow`, `Post`, `Comment` 및 ERD → 관계 스키마 → 함수적 종속성 → 정규화 → MySQL DDL. 아래는 팀 협업을 위한 **제안**이며 과제 필수 구조 자체와 동일하다고 단정하지 않습니다.

## 최소 4테이블

| 릴레이션 | 컬럼 제안 | 핵심 제약/근거 |
|---|---|---|
| users | `user_id VARCHAR(30) PK`, `password_hash`, `display_name`, `avatar_url`, `bio`, `created_at` | 원문 `password`는 실제 구현에서 해시로 저장, ID 유일 |
| follows | `follower_id`, `followee_id`, `created_at` | `(follower_id, followee_id)` 복합 PK, 모두 users FK, 본인 팔로우 CHECK |
| posts | `post_id BIGINT AUTO_INCREMENT PK`, `author_id FK`, `image_path`, `caption`, `created_at` | 이미지 내용이 아닌 경로 저장 |
| comments | `comment_id BIGINT AUTO_INCREMENT PK`, `post_id FK`, `author_id FK`, `text`, `created_at` | 멘션 `@ID`는 text 안에 포함 가능 |

## 가산점 기능 제안

- `likes(post_id, user_id, created_at)`: `(post_id,user_id)` 복합 PK, 중복 좋아요 방지. 백엔드 프론트 v3에서 좋아요 JSON API 계약 존재.
- `stories(story_id, author_id, image_path, caption, created_at, expires_at)`와 `story_views(story_id,viewer_id, viewed_at)`: 진짜 스토리 게시/조회 기록/만료 처리가 필요할 때만 추가. 현재 프론트 v3의 스토리 원은 **게시물 이미지로 만든 샘플**, 읽음 표시는 브라우저 `localStorage`.
- `hashtags` / `post_hashtags`: 추후 기능 확대 시 고려.

## DB 담당 SQL 쿼리 체크리스트

1. 회원 가입 `INSERT users`, 로그인 `SELECT password_hash`, 비밀번호 변경 `UPDATE users SET password_hash = ...`.
2. 팔로우 `INSERT follows`, 취소 `DELETE follows`, `COUNT` followers/following, 두 방향 사용자 목록 조회.
3. 게시물 `INSERT posts`, 작성자의 프로필 게시물 최신순 조회.
4. 홈 피드 SQL: 본인 게시물 + 팔로잉 이용자 게시물, `ORDER BY p.created_at DESC, p.post_id DESC`.
5. 댓글 `INSERT comments`, 해당 게시물 댓글 조회, @mention 문자열 유지.
6. 좋아요 추가/취소 및 `COUNT`, 사용자별 `is_liked` 계산.
7. `users.user_id` ID 부분 일치 검색 (검색 SQL의 `%`, `_` 와일드카드 처리 및 결과 수 제한 검토).
8. 샘플 데이터, ERD, FD, 3NF/BCNF 검사 및 필요한 분해를 문서화.

모든 사용자 입력 SQL은 `%s` 바인딩. `backend/db.py`는 연결 설정 예시일 뿐이며, SQL은 별도 파일/백엔드 서비스로 구현합니다.
