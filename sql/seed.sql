-- Run once against a fresh demo database after schema.sql.
-- The three local demo accounts use the password frame-demo-2026.
SET NAMES utf8mb4;
START TRANSACTION;

SET @demo_hash = '$argon2id$v=19$m=65536,t=3,p=4$k2Bnnm2ksObeMRSW3wf0FA$7Pq6IUPaUFW/Nb5rL51F5gXTkgg995aXx38f4/0HebE';
INSERT INTO users (user_id, password_hash, display_name, avatar_url, bio) VALUES
  ('demo_jineon', @demo_hash, '김진언', '/static/images/demo/avatar-jineon.svg', '사진으로 기록하는 하루'),
  ('demo_alice', @demo_hash, '박앨리스', '/static/images/demo/avatar-alice.svg', '바다를 좋아합니다'),
  ('demo_mina', @demo_hash, '최미나', '/static/images/demo/avatar-mina.svg', '산책 중 만난 꽃');

INSERT INTO follows (follower_id, followee_id) VALUES ('demo_jineon', 'demo_alice');

INSERT INTO posts (author_id, image_path, caption, location, created_at)
VALUES ('demo_jineon', 'images/demo/city.svg', '노을 아래 도시', '서울', NOW() - INTERVAL 2 HOUR);
INSERT INTO posts (author_id, image_path, caption, location, created_at)
VALUES ('demo_alice', 'images/demo/coast.svg', '주말 바다 기록', '부산', NOW() - INTERVAL 1 HOUR);
SET @coast_post = LAST_INSERT_ID();
INSERT INTO posts (author_id, image_path, caption, location, created_at)
VALUES ('demo_mina', 'images/demo/flower.svg', '산책길에 발견한 꽃', '제주', NOW());

INSERT INTO comments (post_id, author_id, text)
VALUES (@coast_post, 'demo_jineon', '@demo_alice 다음에는 같이 가요!');
INSERT INTO likes (post_id, user_id) VALUES (@coast_post, 'demo_jineon');
COMMIT;
