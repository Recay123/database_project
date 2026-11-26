"""DB-independent tests for FRAME v4 routes.

Run: python -m unittest tests.test_v4 -v
Requires packages from requirements-backend.txt.
"""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from PIL import Image

from backend.routers import v4_actions as v4


class Cursor:
    def __init__(self, db):
        self.db = db
        self.rowcount = 1
        self.last = None

    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, sql, params=()):
        self.db.statements.append((sql, params))
        if sql.startswith('SELECT '):
            self.last = ({'post_id': 1, 'comment_id': 2} if self.db.is_owner else None)
        else:
            self.last = None
            self.rowcount = 1
    def fetchone(self): return self.last


class DB:
    def __init__(self, is_owner=True):
        self.is_owner = is_owner
        self.statements = []
        self.committed = False
        self.rolled_back = False
    def cursor(self, **kwargs): return Cursor(self)
    def commit(self): self.committed = True
    def rollback(self): self.rolled_back = True


class V4Tests(unittest.TestCase):
    def setUp(self):
        self.csrf = patch.object(v4, 'check_csrf', return_value=None)
        self.csrf.start()
        self.addCleanup(self.csrf.stop)

    def test_edit_post_ownership_and_length(self):
        db = DB()
        result = v4.edit_post(1, object(), caption='  안녕하세요  ', x_csrf_token='token',
                              uid='alice', db=db)
        self.assertEqual(result['caption'], '안녕하세요')
        self.assertTrue(db.committed)
        self.assertTrue(any(s.startswith('UPDATE posts') for s, _ in db.statements))
        with self.assertRaises(HTTPException) as err:
            v4.edit_post(1, object(), caption='no', uid='mallory', db=DB(is_owner=False))
        self.assertEqual(err.exception.status_code, 404)
        with self.assertRaises(HTTPException) as err:
            v4.edit_post(1, object(), caption='x' * 2201, uid='alice', db=DB())
        self.assertEqual(err.exception.status_code, 400)

    def test_edit_comment_ownership_and_validations(self):
        db = DB()
        result = v4.edit_comment(1, 2, object(), text=' @alice 좋아요 ', uid='alice', db=db)
        self.assertEqual(result['comment']['text'], '@alice 좋아요')
        self.assertTrue(db.committed)
        with self.assertRaises(HTTPException) as err:
            v4.edit_comment(1, 2, object(), text='own?', uid='mallory', db=DB(is_owner=False))
        self.assertEqual(err.exception.status_code, 404)
        with self.assertRaises(HTTPException) as err:
            v4.edit_comment(1, 2, object(), text='  ', uid='alice', db=DB())
        self.assertEqual(err.exception.status_code, 400)

    def test_avatar_persists_new_path_and_reencodes_jpeg(self):
        image = Image.new('RGBA', (24, 20), color=(60, 120, 170, 90))
        buffer = io.BytesIO()
        image.save(buffer, 'PNG')
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(v4, 'UPLOAD_DIR', Path(folder) / 'uploads'):
                db = DB()
                result = v4.upload_avatar(object(),
                    avatar=UploadFile(filename='a.png', file=io.BytesIO(buffer.getvalue())),
                    uid='alice', db=db)
                self.assertTrue(db.committed)
                self.assertTrue(result['avatar_url'].startswith('/static/uploads/'))
                out, = v4.UPLOAD_DIR.iterdir()
                with Image.open(out) as jpeg:
                    self.assertEqual(jpeg.format, 'JPEG')
                self.assertEqual(out.suffix, '.jpg')

    def test_bad_avatar_rejected(self):
        db = DB()
        with self.assertRaises(HTTPException) as err:
            v4.upload_avatar(object(),
                avatar=UploadFile(filename='fake.jpg', file=io.BytesIO(b'not an image')),
                uid='alice', db=db)
        self.assertEqual(err.exception.status_code, 400)
        self.assertFalse(db.committed)


if __name__ == '__main__':
    unittest.main()
