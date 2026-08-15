import pytest
from unittest.mock import patch
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


def test_redirect_cache_hit(client):
    """Test that a cache hit directly redirects without querying the database."""
    with patch("app.routes.urls.cache.get", return_value="https://cached-destination.com") as mock_get, \
         patch("app.routes.urls.Url.get") as mock_db_get:

        response = client.get("/cached123")

        assert response.status_code == 302
        assert response.headers["Location"] == "https://cached-destination.com"
        mock_get.assert_called_once_with("url:cached123")
        mock_db_get.assert_not_called()


def test_redirect_cache_miss_populates_cache(client, app):
    """Test that a cache miss queries the DB and populates Redis cache."""
    with app.app_context():
        db.connect(reuse_if_open=True)
        Url.create(original_url="https://db-destination.com", short_code="dbcode123")
        db.close()

    with patch("app.routes.urls.cache.get", return_value=None) as mock_get, \
         patch("app.routes.urls.cache.setex") as mock_setex:

        response = client.get("/dbcode123")

        assert response.status_code == 302
        assert response.headers["Location"] == "https://db-destination.com"
        mock_get.assert_called_once_with("url:dbcode123")
        mock_setex.assert_called_once_with("url:dbcode123", 3600, "https://db-destination.com")


def test_shorten_write_through_cache(client):
    """Test that creating a short URL populates the Redis cache immediately."""
    with patch("app.routes.urls.cache.setex") as mock_setex:
        response = client.post("/shorten", json={"url": "https://new-url.com"})

        assert response.status_code == 201
        short_code = response.get_json()["short_code"]
        mock_setex.assert_called_once_with(f"url:{short_code}", 3600, "https://new-url.com")


def test_cache_failure_fallback_to_db(client, app):
    """Test graceful fallback to DB when Redis raises an exception."""
    with app.app_context():
        db.connect(reuse_if_open=True)
        Url.create(original_url="https://fallback-url.com", short_code="fallback123")
        db.close()

    with patch("app.routes.urls.cache.get", side_effect=Exception("Redis connection error")), \
         patch("app.routes.urls.cache.setex", side_effect=Exception("Redis write error")):

        response = client.get("/fallback123")

        assert response.status_code == 302
        assert response.headers["Location"] == "https://fallback-url.com"
