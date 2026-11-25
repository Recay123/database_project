"""Run with python -m unittest discover -s tests -v."""
import os
import re
import tempfile
import unittest
from contextlib import closing
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from mysql.connector import Error as MySQLError
from PIL import Image

os.environ.setdefault("SESSION_SECRET", "test-only-frame-session-secret")

from app.preview_main import app as preview
from backend.db import get_db
from backend.main import app as backend
from backend.routers import actions

ROOT = Path(__file__).resolve().parent.parent
DEMO_PASSWORD = "frame-demo-2026"


def csrf(client, page="/login"):
    response = client.get(page)
    response.raise_for_status()
    return re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)[1]


def csrf_headers(client, page="/feed"):
    return {"X-CSRF-Token": csrf(client, page)}


def image_bytes(image_format="PNG"):
    contents = BytesIO()
    Image.new("RGB", (3, 2), "navy").save(contents, format=image_format)
    return contents.getvalue()


def drop_test_database(name):
    with closing(get_db()) as connections:
        with next(connections).cursor() as cur:
            cur.execute(f"DROP DATABASE `{name}`")


class SmokeTests(unittest.TestCase):
    def test_preview_kept_working(self):
        with TestClient(preview) as client:
            self.assertEqual(client.get("/health").json()["mode"], "frontend-preview")
            for page in ("/feed", "/login", "/signup", "/profile/alice", "/upload",
                         "/search?q=ali", "/settings/password"):
                self.assertEqual(client.get(page).status_code, 200, page)
            self.assertIn('data-integration-mode="preview"', client.get("/feed").text)

    def test_image_formats_and_corrupt_file(self):
        for image_format, extension in actions.IMAGE_EXTENSIONS.items():
            with self.subTest(image_format=image_format):
                self.assertEqual(actions._image_ext(image_bytes(image_format)), extension)
        self.assertIsNone(actions._image_ext(b"\x89PNG\r\n\x1a\ncorrupt"))


@unittest.skipUnless(os.environ.get("FRAME_TEST_MYSQL") == "1",
                     "set FRAME_TEST_MYSQL=1 to use an isolated MySQL database")
class MySQLHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name = "frame_test_" + uuid4().hex
        with closing(get_db()) as connections:
            with next(connections).cursor() as cur:
                cur.execute(f"CREATE DATABASE `{name}` DEFAULT CHARACTER SET utf8mb4")
        cls.addClassCleanup(drop_test_database, name)
        cls.enterClassContext(patch.dict(os.environ, {"DB_NAME": name}))
        with closing(get_db()) as connections:
            with next(connections).cursor() as cur:
                for script in ("schema.sql", "seed.sql"):
                    cur.execute((ROOT / "sql" / script).read_text(encoding="utf-8"))
                    list(cur.fetchsets())

    def setUp(self):
        self.client = self.enterContext(TestClient(backend, follow_redirects=False))

    def login(self, username, password=DEMO_PASSWORD, client=None):
        if client is None:
            client = self.client
        return client.post("/login", data={
            "username": username, "password": password, "csrf_token": csrf(client),
        })

    def test_authentication_and_password_change(self):
        client = self.client
        self.assertEqual(client.get("/health").json(), {
            "status": "ok", "mode": "backend", "mysql_connected": True,
        })
        for route in ("/feed", "/profile/demo_alice", "/upload", "/settings/password"):
            self.assertEqual(client.get(route).headers["location"], "/login")
        for route in ("/posts/1/comments", "/posts/1/likes", "/users/demo_alice/follow"):
            self.assertEqual(client.post(route).status_code, 401, route)
        self.assertEqual(client.post("/posts").headers["location"], "/login")
        self.assertEqual(client.post("/settings/password").headers["location"], "/login")

        signup = {
            "username": "test_member", "display_name": "테스트 회원", "password": "before-change",
            "confirm_password": "before-change", "csrf_token": csrf(client, "/signup"),
        }
        self.assertEqual(client.post("/signup", data=signup).headers["location"], "/login")
        self.assertIn("이미 사용 중인 아이디", client.post("/signup", data=signup).text)
        failed = self.login("test_member", "invalid")
        self.assertEqual(failed.status_code, 401)
        self.assertIn("아이디 또는 비밀번호가 올바르지 않습니다.", failed.text)
        self.assertEqual(self.login("test_member", "before-change").headers["location"], "/feed")
        self.assertEqual(client.post("/posts/1/likes",
                                    headers={"X-CSRF-Token": signup["csrf_token"]}).status_code, 403)
        password = {
            "current_password": "wrong-password", "new_password": "after-change",
            "confirm_password": "after-change", "csrf_token": csrf(client, "/settings/password"),
        }
        self.assertIn("현재 비밀번호가 올바르지 않습니다.",
                      client.post("/settings/password", data=password).text)
        password["current_password"] = "before-change"
        response = client.post("/settings/password", data=password)
        self.assertEqual(response.headers["location"], "/settings/password?changed=1")
        self.assertIn("비밀번호가 변경되었습니다", client.get(response.headers["location"]).text)
        token = csrf(client, "/feed")
        self.assertEqual(client.post("/logout", data={"csrf_token": token}).headers["location"], "/login")
        self.assertEqual(self.login("test_member", "before-change").status_code, 401)
        self.assertEqual(self.login("test_member", "after-change").status_code, 303)

    def test_database_guards_and_cascade(self):
        with closing(get_db()) as connections:
            db = next(connections)
            with db.cursor() as cur:
                for sql in (
                    "INSERT INTO follows (follower_id, followee_id) VALUES ('demo_alice', 'demo_alice')",
                    "UPDATE follows SET followee_id=follower_id WHERE follower_id='demo_jineon'",
                ):
                    with self.assertRaises(MySQLError) as error:
                        cur.execute(sql)
                    self.assertEqual(error.exception.sqlstate, "45000")

                cur.execute("DELETE FROM users WHERE user_id='demo_alice'")
                for sql in (
                    "SELECT 1 FROM follows WHERE followee_id='demo_alice'",
                    "SELECT 1 FROM posts WHERE author_id='demo_alice'",
                    "SELECT 1 FROM comments WHERE text='@demo_alice 다음에는 같이 가요!'",
                    "SELECT 1 FROM likes WHERE user_id='demo_jineon'",
                ):
                    cur.execute(sql)
                    self.assertIsNone(cur.fetchone(), sql)
            db.rollback()

    def test_feed_upload_profile_search_and_mutations(self):
        client = self.client
        self.assertEqual(self.login("demo_jineon").status_code, 303)
        headers = csrf_headers(client)
        feed = client.get("/feed").text
        self.assertLess(feed.index("주말 바다 기록"), feed.index("노을 아래 도시"))
        self.assertNotIn("산책길에 발견한 꽃", feed)
        self.assertIn("demo_alice", client.get("/profile/demo_jineon/following").text)
        self.assertIn("demo_jineon", client.get("/profile/demo_alice/followers").text)
        self.assertEqual(client.get("/profile/missing_user").status_code, 404)
        self.assertIn("/profile/demo_alice", client.get("/search", params={"q": "demo_"}).text)
        self.assertNotIn("/profile/demo_alice", client.get("/search", params={"q": "%"}).text)

        follow_url = "/users/demo_mina/follow"
        for _ in range(2):
            self.assertEqual(client.post(follow_url, headers=headers).json(), {
                "user_id": "demo_mina", "is_following": True, "followers_count": 1,
            })
        self.assertIn("산책길에 발견한 꽃", client.get("/feed").text)
        self.assertEqual(client.delete(follow_url, headers=headers).json(), {
            "user_id": "demo_mina", "is_following": False, "followers_count": 0,
        })
        self.assertEqual(client.post("/users/DEMO_JINEON/follow", headers=headers).status_code, 400)
        self.assertEqual(client.post("/users/missing_user/follow", headers=headers).status_code, 404)
        self.assertEqual(client.get("/static/images/demo/coast.svg").status_code, 200)

        static_app = next(route.app for route in backend.routes if route.name == "static")
        with tempfile.TemporaryDirectory() as folder, patch.object(
            actions, "UPLOAD_DIR", Path(folder) / "uploads"
        ), patch.object(static_app, "all_directories", [folder]):
            upload = {"csrf_token": csrf(client, "/upload"), "caption": "테스트 사진"}
            invalid = client.post("/posts", data=upload, files={
                "image": ("broken.png", b"\x89PNG\r\n\x1a\ncorrupt", "image/png"),
            })
            self.assertEqual(invalid.status_code, 400)
            self.assertIn("정상적인 JPG, PNG, WEBP", invalid.text)
            oversized = client.post("/posts", data=upload, files={
                "image": ("large.png", b"x" * (actions.MAX_IMAGE_BYTES + 1), "image/png"),
            })
            self.assertEqual(oversized.status_code, 400)
            self.assertIn("8MB 이하", oversized.text)
            self.assertFalse(actions.UPLOAD_DIR.exists())
            png = image_bytes()
            created = client.post("/posts", data=upload, files={"image": ("photo.png", png, "image/png")})
            self.assertEqual(created.headers["location"], "/feed?uploaded=1")
            saved, = actions.UPLOAD_DIR.iterdir()
            self.assertEqual(saved.read_bytes(), png)
            feed = client.get("/feed").text
            self.assertIn("테스트 사진", feed)
            image_url = "/static/uploads/" + saved.name
            self.assertIn(image_url, feed)
            self.assertEqual(client.get(image_url).content, png)

        post_id = re.search(r'<article class="post-card" data-post-id="(\d+)"', feed)[1]
        base = f"/posts/{post_id}"
        self.assertEqual(client.post(base + "/likes").status_code, 403)
        self.assertEqual(client.post("/posts/99999999/likes", headers=headers).status_code, 404)
        self.assertIsInstance(client.post("/posts/abc/likes", headers=headers).json()["detail"], str)
        for _ in range(2):
            self.assertEqual(client.post(base + "/likes", headers=headers).json(),
                             {"liked": True, "like_count": 1})
        self.assertEqual(client.delete(base + "/likes", headers=headers).json(),
                         {"liked": False, "like_count": 0})
        response = client.post(base + "/comments", headers=headers,
                               data={"text": "@demo_alice 반가워요", "author_id": "demo_alice"})
        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        comment = payload["comment"]
        self.assertEqual(payload["comment_count"], 1)
        self.assertEqual(comment["author_id"], "demo_jineon")
        self.assertEqual(comment["text"], "@demo_alice 반가워요")
        comment_url = f'{base}/comments/{comment["comment_id"]}'
        with TestClient(backend, follow_redirects=False) as alice:
            self.assertEqual(self.login("demo_alice", client=alice).status_code, 303)
            self.assertEqual(alice.delete(comment_url, headers=csrf_headers(alice)).status_code, 404)
        self.assertEqual(client.delete(comment_url, headers=headers).json()["comment_count"], 0)

    def test_delete_post_requires_owner_and_removes_related_data(self):
        owner = self.client
        self.assertEqual(self.login("demo_jineon").status_code, 303)
        headers = csrf_headers(owner)
        caption = "삭제할 게시물 테스트"
        with tempfile.TemporaryDirectory() as folder, patch.object(actions, "UPLOAD_DIR", Path(folder)):
            response = owner.post(
                "/posts",
                data={"caption": caption, "csrf_token": csrf(owner, "/upload")},
                files={"image": ("photo.png", image_bytes(), "image/png")},
            )
            self.assertEqual(response.status_code, 303)
            uploaded_file, = Path(folder).iterdir()
            with closing(get_db()) as connections:
                with next(connections).cursor() as cur:
                    cur.execute("SELECT post_id FROM posts WHERE image_path=%s",
                                (f"uploads/{uploaded_file.name}",))
                    post_id, = cur.fetchone()

            url = f"/posts/{post_id}"
            self.assertEqual(owner.post(url + "/comments", headers=headers,
                                        data={"text": "함께 삭제할 댓글"}).status_code, 201)
            self.assertEqual(owner.post(url + "/likes", headers=headers).status_code, 200)
            self.assertEqual(owner.delete(url).status_code, 403)
            with TestClient(backend, follow_redirects=False) as other:
                self.assertEqual(other.delete(url).status_code, 401)
                self.assertEqual(self.login("demo_alice", client=other).status_code, 303)
                self.assertEqual(other.delete(url, headers=csrf_headers(other)).status_code, 404)
            self.assertTrue(uploaded_file.exists())
            self.assertIn(caption, owner.get("/feed").text)

            deleted = owner.delete(url, headers=headers)
            self.assertEqual(deleted.status_code, 200)
            self.assertEqual(deleted.json(), {"deleted": True, "post_id": post_id})
            self.assertFalse(uploaded_file.exists())
            self.assertNotIn(caption, owner.get("/feed").text)
            self.assertNotIn(caption, owner.get("/profile/demo_jineon").text)
            self.assertEqual(owner.delete(url, headers=headers).status_code, 404)
            with closing(get_db()) as connections:
                with next(connections).cursor() as cur:
                    for table in ("posts", "comments", "likes"):
                        cur.execute(f"SELECT 1 FROM {table} WHERE post_id=%s", (post_id,))
                        self.assertIsNone(cur.fetchone(), table)
