import pytest
from unittest.mock import patch, call
from peewee import IntegrityError
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


# --- Area 1: Rejecting Bad Input ---

def test_rejects_empty_string(client):
    response = client.post("/shorten", json={"url": ""})
    assert response.status_code == 400


def test_rejects_plain_word(client):
    response = client.post("/shorten", json={"url": "hello"})
    assert response.status_code == 400


def test_rejects_non_http_scheme(client):
    response = client.post("/shorten", json={"url": "ftp://example.com"})
    assert response.status_code == 400


def test_rejects_url_over_2048_chars(client):
    long_url = "https://example.com/" + "a" * 2048
    response = client.post("/shorten", json={"url": long_url})
    assert response.status_code == 400


def test_accepts_http_url(client):
    response = client.post("/shorten", json={"url": "http://example.com"})
    assert response.status_code == 201


def test_accepts_https_url(client):
    response = client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201


# --- Area 2: Data Consistency ---

def test_stored_url_matches_submitted(client, app):
    response = client.post("/shorten", json={"url": "https://www.example.com/path?q=1"})
    assert response.status_code == 201
    data = response.get_json()

    with app.app_context():
        db.connect(reuse_if_open=True)
        url = Url.get(Url.short_code == data["short_code"])
        assert url.original_url == "https://www.example.com/path?q=1"
        assert url.short_code == data["short_code"]
        db.close()


def test_failed_create_leaves_no_record(client, app):
    with patch("app.routes.urls.Url.create", side_effect=IntegrityError):
        client.post("/shorten", json={"url": "https://www.example.com"})

    with app.app_context():
        db.connect(reuse_if_open=True)
        count = Url.select().count()
        db.close()

    assert count == 0


def test_same_url_twice_creates_two_records(client, app):
    client.post("/shorten", json={"url": "https://www.example.com"})
    client.post("/shorten", json={"url": "https://www.example.com"})

    with app.app_context():
        db.connect(reuse_if_open=True)
        count = Url.select().count()
        db.close()

    assert count == 2


# --- Area 3: Enforcing Uniqueness ---

def test_retries_on_collision_and_succeeds(client, app):
    from unittest.mock import MagicMock
    mock_url = MagicMock()
    mock_url.short_code = "retry1"
    mock_url.original_url = "https://www.example.com"

    side_effects = [IntegrityError, mock_url]

    with patch("app.routes.urls.Url.create", side_effect=side_effects):
        response = client.post("/shorten", json={"url": "https://www.example.com"})

    assert response.status_code == 201


def test_returns_500_after_max_retries_exhausted(client, app):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    with patch("app.routes.urls.Url.create", side_effect=IntegrityError):
        response = client.post("/shorten", json={"url": "https://www.example.com"})

    assert response.status_code == 500
    assert "could not generate a unique short code" in response.get_json()["error"]

    app.config["PROPAGATE_EXCEPTIONS"] = True


# --- Area 4: Handling Invalid or Inactive Resources Correctly ---

def test_health_returns_503_when_db_unreachable(client, app):
    from app.database import db
    with patch.object(db.obj, "execute_sql", side_effect=Exception("db down")):
        response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["status"] == "unavailable"


def test_strips_whitespace_from_url(client, app):
    response = client.post("/shorten", json={"url": "  https://example.com  "})
    assert response.status_code == 201

    with app.app_context():
        db.connect(reuse_if_open=True)
        url = Url.get(Url.short_code == response.get_json()["short_code"])
        assert url.original_url == "https://example.com"
        db.close()


# --- Area 5: Maintaining Expected Behavior Across Core Flows ---

def test_short_url_in_response_is_full_url(client):
    response = client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    short_url = response.get_json()["short_url"]
    assert short_url.startswith("http://")


def test_query_params_preserved_through_redirect(client):
    original = "https://example.com/path?q=1&foo=bar"
    post_response = client.post("/shorten", json={"url": original})
    short_code = post_response.get_json()["short_code"]
    response = client.get(f"/{short_code}")
    assert response.status_code == 302
    assert response.headers["Location"] == original


def test_fragment_preserved_through_redirect(client):
    original = "https://example.com/page#section"
    post_response = client.post("/shorten", json={"url": original})
    short_code = post_response.get_json()["short_code"]
    response = client.get(f"/{short_code}")
    assert response.status_code == 302
    assert response.headers["Location"] == original
