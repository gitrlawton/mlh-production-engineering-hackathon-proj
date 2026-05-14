from flask import Blueprint, jsonify, request

from app.logging import get_log_buffer, MAX_LOG_ENTRIES

logs_bp = Blueprint("logs", __name__)

DEFAULT_LINES = 100


@logs_bp.route("/logs", methods=["GET"])
def logs():
    try:
        lines = int(request.args.get("lines", DEFAULT_LINES))
    except ValueError:
        lines = DEFAULT_LINES

    lines = max(1, min(lines, MAX_LOG_ENTRIES))

    entries = list(get_log_buffer())[-lines:]
    entries.reverse()

    return jsonify(entries), 200
