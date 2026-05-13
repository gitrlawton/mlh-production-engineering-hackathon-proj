import psutil
from flask import Blueprint, jsonify

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/metrics", methods=["GET"])
def metrics():
    mem = psutil.virtual_memory()
    return jsonify({
        "cpu": {
            "percent": psutil.cpu_percent(interval=None),
        },
        "memory": {
            "total": mem.total,
            "used": mem.used,
            "available": mem.available,
            "percent": mem.percent,
        },
    }), 200
