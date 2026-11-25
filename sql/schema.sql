-- Run against the selected, empty MySQL database (DB_NAME).

CREATE TABLE users (
  user_id       VARCHAR(30)  PRIMARY KEY,
  password_hash VARCHAR(255) NOT NULL,
  display_name  VARCHAR(50)  NOT NULL,
  avatar_url    VARCHAR(255),
  bio           VARCHAR(200),
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_user_id CHECK (user_id REGEXP '^[A-Za-z0-9_]{3,30}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE follows (
  follower_id VARCHAR(30) NOT NULL,
  followee_id VARCHAR(30) NOT NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (follower_id, followee_id),
  FOREIGN KEY (follower_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (followee_id) REFERENCES users(user_id) ON DELETE CASCADE,
  INDEX idx_followee (followee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE posts (
  post_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
  author_id  VARCHAR(30)  NOT NULL,
  image_path VARCHAR(255) NOT NULL,
  caption    VARCHAR(2200),
  location   VARCHAR(100),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (author_id) REFERENCES users(user_id) ON DELETE CASCADE,
  INDEX idx_author_time (author_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE comments (
  comment_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  post_id    BIGINT      NOT NULL,
  author_id  VARCHAR(30) NOT NULL,
  text       VARCHAR(1000) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (post_id)   REFERENCES posts(post_id) ON DELETE CASCADE,
  FOREIGN KEY (author_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT chk_text CHECK (CHAR_LENGTH(TRIM(text)) > 0),
  INDEX idx_post_time (post_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE likes (
  post_id    BIGINT      NOT NULL,
  user_id    VARCHAR(30) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (post_id, user_id),
  FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DELIMITER //
CREATE TRIGGER trg_no_self_follow BEFORE INSERT ON follows
FOR EACH ROW
BEGIN
  IF NEW.follower_id = NEW.followee_id THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'cannot follow yourself';
  END IF;
END//
CREATE TRIGGER trg_no_self_follow_update BEFORE UPDATE ON follows
FOR EACH ROW
BEGIN
  IF NEW.follower_id = NEW.followee_id THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'cannot follow yourself';
  END IF;
END//
DELIMITER ;
