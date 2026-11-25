"""MySQL read adapter. 반환 구조는 docs/API_CONTRACT.md를 따른다."""
import html
from urllib.parse import quote


def cursor(db):
    # buffered: 한 연결에서 여러 쿼리를 연속 실행해도 'Unread result' 오류가 나지 않게
    return db.cursor(dictionary=True, buffered=True)


def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def _avatar(avatar_url, display_name, user_id):
    if avatar_url:
        return avatar_url
    initial = html.escape((display_name or user_id or "?")[:1].upper())
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
        "<rect width='100' height='100' fill='#9aa5a0'/>"
        "<text x='50' y='50' dy='.35em' text-anchor='middle' font-size='48' "
        f"fill='white' font-family='sans-serif'>{initial}</text></svg>"
    )
    return "data:image/svg+xml;utf8," + quote(svg, safe="")


def _image_url(path):
    if path.startswith(("/", "http://", "https://")):
        return path
    return "/static/" + path


# ---------- 현재 사용자 / 추천 ----------
def get_current_user(db, request):
    uid = request.session.get("user_id")
    if not uid:
        return None
    cur = cursor(db)
    cur.execute("SELECT user_id, display_name, avatar_url, bio FROM users WHERE user_id=%s", (uid,))
    row = cur.fetchone()
    cur.close()
    if not row:
        request.session.clear()
        return None
    return {
        "user_id": row["user_id"],
        "display_name": row["display_name"],
        "avatar_url": _avatar(row["avatar_url"], row["display_name"], row["user_id"]),
        "bio": row["bio"] or "",
    }


def get_suggested_users(db, viewer_id):
    if not viewer_id:
        return []
    cur = cursor(db)
    cur.execute(
        """SELECT user_id, display_name, avatar_url FROM users
           WHERE user_id <> %s
             AND user_id NOT IN (SELECT followee_id FROM follows WHERE follower_id = %s)
           ORDER BY created_at DESC LIMIT 5""",
        (viewer_id, viewer_id),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {"user_id": r["user_id"], "display_name": r["display_name"],
         "avatar_url": _avatar(r["avatar_url"], r["display_name"], r["user_id"])}
        for r in rows
    ]


# ---------- 게시물 ----------
_POST_SELECT = """
SELECT p.post_id, p.author_id, u.display_name AS author_name, u.avatar_url AS author_avatar,
       p.image_path, p.caption, p.location, p.created_at,
       (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.post_id) AS like_count,
       (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.post_id) AS comment_count,
       EXISTS(SELECT 1 FROM likes l WHERE l.post_id = p.post_id AND l.user_id = %s) AS is_liked
FROM posts p JOIN users u ON u.user_id = p.author_id
"""


def _query_posts(db, where, params, viewer_id):
    cur = cursor(db)
    cur.execute(
        _POST_SELECT + f" WHERE {where} ORDER BY p.created_at DESC, p.post_id DESC LIMIT 100",
        (viewer_id, *params),
    )
    rows = cur.fetchall()

    comments = {}
    if rows:
        ids = [r["post_id"] for r in rows]
        marks = ",".join(["%s"] * len(ids))
        cur.execute(
            "SELECT comment_id, post_id, author_id, text, created_at FROM comments "
            f"WHERE post_id IN ({marks}) ORDER BY created_at, comment_id",
            ids,
        )
        for c in cur.fetchall():
            comments.setdefault(c["post_id"], []).append({
                "comment_id": c["comment_id"], "author_id": c["author_id"],
                "text": c["text"], "created_at": _fmt(c["created_at"]),
            })
    cur.close()

    return [{
        "post_id": r["post_id"],
        "author_id": r["author_id"],
        "author_name": r["author_name"],
        "author_avatar": _avatar(r["author_avatar"], r["author_name"], r["author_id"]),
        "image_url": _image_url(r["image_path"]),
        "image_alt": f'{r["author_name"]}의 게시물 사진',
        "caption": r["caption"] or "",
        "created_at": _fmt(r["created_at"]),
        "location": r["location"] or "",
        "like_count": int(r["like_count"]),
        "comment_count": int(r["comment_count"]),
        "is_liked": bool(r["is_liked"]),
        "comments": comments.get(r["post_id"], []),
    } for r in rows]


def get_feed(db, viewer_id):
    if not viewer_id:
        return []
    return _query_posts(
        db,
        "p.author_id = %s OR p.author_id IN (SELECT followee_id FROM follows WHERE follower_id = %s)",
        (viewer_id, viewer_id), viewer_id,
    )


def get_user_posts(db, user_id, viewer_id):
    return _query_posts(db, "p.author_id = %s", (user_id,), viewer_id)


# ---------- 사용자 ----------
_USER_SELECT = """
SELECT u.user_id, u.display_name, u.avatar_url, u.bio,
  (SELECT COUNT(*) FROM follows f WHERE f.followee_id = u.user_id) AS followers_count,
  (SELECT COUNT(*) FROM follows f WHERE f.follower_id = u.user_id) AS following_count,
  (SELECT COUNT(*) FROM posts p WHERE p.author_id = u.user_id) AS post_count,
  EXISTS(SELECT 1 FROM follows f WHERE f.follower_id = %s AND f.followee_id = u.user_id) AS is_following
FROM users u
"""


def _query_users(db, where, params, viewer_id, tail=""):
    cur = cursor(db)
    cur.execute(_USER_SELECT + f" WHERE {where} {tail}", (viewer_id, *params))
    rows = cur.fetchall()
    cur.close()
    return [{
        "user_id": r["user_id"],
        "display_name": r["display_name"],
        "avatar_url": _avatar(r["avatar_url"], r["display_name"], r["user_id"]),
        "bio": r["bio"] or "",
        "location": "",
        "followers_count": int(r["followers_count"]),
        "following_count": int(r["following_count"]),
        "post_count": int(r["post_count"]),
        "is_following": bool(r["is_following"]),
    } for r in rows]


def get_user(db, user_id, viewer_id):
    rows = _query_users(db, "u.user_id = %s", (user_id,), viewer_id)
    return rows[0] if rows else None


def search_users(db, q, viewer_id):
    q = q.strip()[:60]
    if not q:
        return []
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return _query_users(db, "u.user_id LIKE %s", (f"%{escaped}%",), viewer_id,
                        tail="ORDER BY u.user_id LIMIT 30")


def get_follow_users(db, user_id, mode, viewer_id):
    if mode == "followers":
        where = "u.user_id IN (SELECT follower_id FROM follows WHERE followee_id = %s)"
    else:
        where = "u.user_id IN (SELECT followee_id FROM follows WHERE follower_id = %s)"
    return _query_users(db, where, (user_id,), viewer_id, tail="ORDER BY u.user_id")


# ---------- 스토리 (DB 없이 게시물에서 파생) ----------
def get_stories(posts):
    stories, seen = [], set()
    for p in posts:
        if p["author_id"] in seen:
            continue
        seen.add(p["author_id"])
        stories.append({
            "user_id": p["author_id"], "display_name": p["author_name"],
            "avatar_url": p["author_avatar"], "story_image": p["image_url"],
            "story_caption": p["caption"] or "오늘의 순간",
        })
    return stories