import secrets
from flask import Blueprint, jsonify, redirect, render_template, request
from app.models.url import Url
from peewee import DoesNotExist

urls_bp = Blueprint("urls", __name__)


@urls_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@urls_bp.route("/", methods=["POST"])
def index_post():
    original_url = request.form.get("url")

    if not original_url:
        return render_template("index.html", error="A URL is required.")

    short_code = secrets.token_urlsafe(6)
    url = Url.create(original_url=original_url, short_code=short_code)

    return render_template("index.html", short_url=f"/{url.short_code}", short_code=url.short_code, submitted_url=original_url)


@urls_bp.route("/shorten", methods=["POST"])
def shorten():
    data = request.get_json()
    original_url = data.get("url")

    if not original_url:
        return jsonify({"error": "url is required"}), 400

    short_code = secrets.token_urlsafe(6)
    url = Url.create(original_url=original_url, short_code=short_code)

    return jsonify({"short_code": url.short_code, "short_url": f"/{url.short_code}"}), 201


@urls_bp.route("/<short_code>", methods=["GET"])
def redirect_to_url(short_code):
    try:
        url = Url.get(Url.short_code == short_code)
        return redirect(url.original_url)
    except DoesNotExist:
        return jsonify({"error": "short code not found"}), 404
