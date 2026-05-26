from pathlib import Path

import yaml
from flask import Blueprint, jsonify, render_template

from app.alerts import get_error_rate
from app.database import db

alerts_bp = Blueprint("alerts", __name__)

CONFIG_PATH = Path(__file__).parent.parent.parent / "alerts.yml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


@alerts_bp.route("/alerts")
def alerts_dashboard():
    return render_template("alerts.html")


@alerts_bp.route("/alerts/config")
def alerts_config():
    return jsonify(load_config()), 200


@alerts_bp.route("/alerts/status")
def alerts_status():
    try:
        db.execute_sql("SELECT 1")
        healthy = True
    except Exception:
        healthy = False

    return jsonify({
        "healthy": healthy,
        "error_rate_percent": get_error_rate(),
    }), 200
