"""Contract/regression checks runnable with: python -m pytest -q tests/test_handoff.py"""
from fastapi.testclient import TestClient

from app.preview_main import app as preview
from backend.main import app as backend


def test_preview_kept_working():
    with TestClient(preview) as client:
        assert client.get('/health').json()['mode'] == 'frontend-preview'
        for page in ['/feed', '/login', '/signup', '/profile/alice', '/upload', '/search?q=ali', '/settings/password']:
            response = client.get(page)
            assert response.status_code == 200, (page, response.text[:120])
        assert 'data-integration-mode="preview"' in client.get('/feed').text


def test_backend_get_routes_sample_only():
    with TestClient(backend) as client:
        assert client.get('/health').json() == {'status': 'ok', 'mode': 'backend-scaffold', 'mysql_connected': False}
        for page in ['/feed', '/login', '/signup', '/profile/alice', '/profile/alice/followers', '/profile/alice/following', '/upload', '/search?q=ali', '/settings/password']:
            r = client.get(page)
            assert r.status_code == 200, (page, r.text[:200])
        page = client.get('/feed').text
        assert 'data-integration-mode="backend"' in page
        assert 'name="text"' in page
        assert client.get('/profile/nope').status_code == 404
        assert client.get('/static/js/app.js').status_code == 200


def test_backend_mutations_are_explicit_todos():
    with TestClient(backend) as client:
        for method, url, kwargs in [
            ('post', '/login', {'data': {'username':'jineon', 'password':'x'}}),
            ('post', '/signup', {'data': {'username':'new','display_name':'New','password':'12345678','confirm_password':'12345678'}}),
            ('post', '/settings/password', {'data':{'current_password':'x', 'new_password':'y','confirm_password':'y'}}),
            ('post', '/posts/105/comments', {'data':{'text':'hello'}}),
            ('post', '/posts/105/likes', {}),
            ('delete', '/posts/105/likes', {}),
            ('post', '/users/alice/follow', {}),
            ('delete', '/users/alice/follow', {}),
        ]:
            result = getattr(client, method)(url, **kwargs)
            assert result.status_code == 501, (method, url, result.status_code)
