from flask import Blueprint, jsonify

debug_bp = Blueprint("debug", __name__)


@debug_bp.route("/debug/error")
def trigger_error():
    return jsonify({"error": "simulated server error"}), 500
