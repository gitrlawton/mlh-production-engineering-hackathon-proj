import pytest
from app import create_app
from app.logging import get_log_buffer


@pytest.fixture(autouse=True)
def clear_log_buffer():
    get_log_buffer().clear()
    yield
    get_log_buffer().clear()


@pytest.fixture
def app():
    _app = create_app()
    _app.config["TESTING"] = True
    yield _app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


def test_logs_returns_200(client):
    response = client.get("/logs")
    assert response.status_code == 200


def test_logs_returns_list(client):
    data = client.get("/logs").get_json()
    assert isinstance(data, list)


def test_request_appears_in_log(client):
    client.get("/metrics")
    entries = client.get("/logs").get_json()
    messages = [e["message"] for e in entries]
    assert any("GET /metrics" in m for m in messages)


def test_log_entry_shape(client):
    client.get("/metrics")
    entries = client.get("/logs").get_json()
    assert len(entries) > 0
    entry = entries[0]
    assert "timestamp" in entry
    assert "level" in entry
    assert "message" in entry


def test_lines_param_limits_results(client):
    for _ in range(10):
        client.get("/metrics")
    entries = client.get("/logs?lines=3").get_json()
    assert len(entries) <= 3


def test_invalid_lines_param_falls_back_to_default(client):
    response = client.get("/logs?lines=abc")
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
