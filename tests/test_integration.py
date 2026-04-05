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


# --- POST /shorten → verify DB record created ---

def test_shorten_creates_db_record(client, app):
    response = client.post(
        "/shorten",
        json={"url": "https://www.example.com"}
    )
    assert response.status_code == 201
    short_code = response.get_json()["short_code"]

    with app.app_context():
        db.connect(reuse_if_open=True)
        url = Url.get(Url.short_code == short_code)
        assert url.original_url == "https://www.example.com"
        assert url.short_code == short_code
        db.close()


# --- GET /<short_code> → verify redirect uses URL from DB ---

def test_redirect_uses_db_url(client, app):
    with app.app_context():
        db.connect(reuse_if_open=True)
        url = Url.create(original_url="https://www.example.com", short_code="test99")
        db.close()

    response = client.get(f"/{url.short_code}")
    assert response.status_code == 302
    assert response.headers["Location"] == "https://www.example.com"
