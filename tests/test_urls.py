import pytest
from unittest.mock import MagicMock, patch
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
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
    mock_url = MagicMock()
    mock_url.short_code = "abc123"

    with patch("app.routes.urls.Url.create", return_value=mock_url):
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
    mock_url = MagicMock()
    mock_url.original_url = "https://www.example.com"

    with patch("app.routes.urls.Url.get", return_value=mock_url):
        response = client.get("/abc123")

    assert response.status_code == 302
    assert "example.com" in response.headers["Location"]


def test_redirect_invalid_short_code(client):
    from peewee import DoesNotExist

    with patch("app.routes.urls.Url.get", side_effect=DoesNotExist):
        response = client.get("/notfound")

    assert response.status_code == 404
    assert "error" in response.get_json()
