import time

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from app.alerts import record_request
from app.database import db, init_db
from app.logging import init_logging
from app.routes import register_routes


def create_app():
    load_dotenv()

    app = Flask(__name__)

    init_db(app)
    init_logging(app)

    from app import models  # noqa: F401 - registers models with Peewee

    register_routes(app)

    @app.before_request
    def _start_timer():
        request._start_time = time.monotonic()

    @app.after_request
    def _log_request(response):
        duration_ms = round((time.monotonic() - request._start_time) * 1000)
        app.logger.info("%s %s %s (%dms)", request.method, request.path, response.status_code, duration_ms)
        record_request(response.status_code)
        return response

    @app.route("/health")
    def health():
        try:
            db.execute_sql("SELECT 1")
            return jsonify({"status": "ok"}), 200
        except Exception:
            return jsonify({"status": "unavailable", "reason": "database unreachable"}), 503

    @app.errorhandler(404)
    def not_found(e):
        app.logger.warning("404 %s %s", request.method, request.path)
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error("500 %s %s", request.method, request.path)
        return jsonify({"error": "internal server error"}), 500

    return app
