import pytest
from app import create_app


@pytest.fixture
def app():
    _app = create_app()
    _app.config["TESTING"] = True
    yield _app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


def test_metrics_returns_200(client):
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_response_shape(client):
    data = client.get("/metrics").get_json()
    assert "cpu" in data
    assert "percent" in data["cpu"]
    assert "memory" in data
    for key in ("total", "used", "available", "percent"):
        assert key in data["memory"]


def test_metrics_cpu_in_range(client):
    data = client.get("/metrics").get_json()
    assert 0.0 <= data["cpu"]["percent"] <= 100.0


def test_metrics_memory_values_positive(client):
    data = client.get("/metrics").get_json()
    mem = data["memory"]
    assert mem["total"] > 0
    assert mem["used"] > 0
    assert mem["available"] >= 0
    assert 0.0 <= mem["percent"] <= 100.0
