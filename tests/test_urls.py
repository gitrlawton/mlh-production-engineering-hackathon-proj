import pytest
from app import create_app
from app.database import db
from app.models.url import Url


@pytest.fixture
def app():
    _app = create_app()
    _app.config["TESTING"] = True

    with _app.app_context():
        db.connect(reuse_if_open=True)
        db.create_tables([Url], safe=True)
        db.close()

    yield _app

    with _app.app_context():
        db.connect(reuse_if_open=True)
        Url.delete().execute()
        db.close()


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


# --- /health ---

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


# --- GET / ---

def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"URL Shortener" in response.data


# --- POST /shorten (JSON API) ---

def test_shorten_valid_url(client):
    response = client.post(
        "/shorten",
        json={"url": "https://www.example.com"}
    )
    assert response.status_code == 201
    data = response.get_json()
    assert "short_code" in data
    assert "short_url" in data


def test_shorten_missing_url(client):
    response = client.post("/shorten", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()


# --- GET /<short_code> ---

def test_redirect_valid_short_code(client):
    post_response = client.post(
        "/shorten",
        json={"url": "https://www.example.com"}
    )
    short_code = post_response.get_json()["short_code"]
    response = client.get(f"/{short_code}")
    assert response.status_code == 302
    assert "example.com" in response.headers["Location"]


def test_redirect_invalid_short_code(client):
    response = client.get("/notfound")
    assert response.status_code == 404
    assert "error" in response.get_json()
