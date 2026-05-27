import json
import os
import urllib.request
from pathlib import Path

import yaml
from flask import Blueprint, jsonify, render_template, request

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


@alerts_bp.route("/alerts/notify", methods=["POST"])
def alerts_notify():
    data = request.get_json(silent=True) or {}
    title = data.get("title", "Alert")
    message = data.get("message", "")
    level = data.get("level", "INFO")

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return jsonify({"status": "skipped", "reason": "DISCORD_WEBHOOK_URL not set"}), 200

    colors = {"ERROR": 0xFF0000, "WARNING": 0xFF8C10, "INFO": 0x3498DB}
    payload = json.dumps({
        "embeds": [{
            "title": title,
            "description": message,
            "color": colors.get(level, 0x3498DB),
        }]
    }).encode()

    try:
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "DiscordBot (https://github.com, 1.0)",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
        return jsonify({"status": "sent"}), 200
    except Exception as e:
        return jsonify({"status": "error", "reason": str(e)}), 500


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
