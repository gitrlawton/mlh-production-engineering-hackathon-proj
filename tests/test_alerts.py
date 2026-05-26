import pytest
from unittest.mock import patch
from app import create_app
from app.alerts import get_request_window, record_request


@pytest.fixture(autouse=True)
def clear_request_window():
    get_request_window().clear()
    yield
    get_request_window().clear()


@pytest.fixture
def app():
    _app = create_app()
    _app.config["TESTING"] = True
    yield _app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


def test_alerts_dashboard_returns_200(client):
    response = client.get("/alerts")
    assert response.status_code == 200


def test_alerts_config_has_expected_keys(client):
    data = client.get("/alerts/config").get_json()
    assert "service_down" in data
    assert "high_error_rate" in data
    assert "threshold_percent" in data["high_error_rate"]
    assert "check_interval_seconds" in data["service_down"]


def test_alerts_status_shape(client):
    with patch("app.routes.alerts.db") as mock_db:
        mock_db.execute_sql.return_value = None
        data = client.get("/alerts/status").get_json()
    assert "healthy" in data
    assert "error_rate_percent" in data


def test_alerts_status_healthy_when_db_ok(client):
    with patch("app.routes.alerts.db") as mock_db:
        mock_db.execute_sql.return_value = None
        data = client.get("/alerts/status").get_json()
    assert data["healthy"] is True


def test_alerts_status_unhealthy_when_db_fails(client):
    with patch("app.routes.alerts.db") as mock_db:
        mock_db.execute_sql.side_effect = Exception("db down")
        data = client.get("/alerts/status").get_json()
    assert data["healthy"] is False


def test_error_rate_100_when_all_requests_are_errors(client):
    for _ in range(10):
        record_request(500)
    with patch("app.routes.alerts.db") as mock_db:
        mock_db.execute_sql.return_value = None
        data = client.get("/alerts/status").get_json()
    assert data["error_rate_percent"] == 100.0


def test_error_rate_zero_when_no_errors(client):
    for _ in range(10):
        record_request(200)
    with patch("app.routes.alerts.db") as mock_db:
        mock_db.execute_sql.return_value = None
        data = client.get("/alerts/status").get_json()
    assert data["error_rate_percent"] == 0.0
