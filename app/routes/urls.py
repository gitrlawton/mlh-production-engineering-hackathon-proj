import secrets
from urllib.parse import urlparse
from flask import Blueprint, jsonify, redirect, render_template, request
from app.models.url import Url
from peewee import DoesNotExist, IntegrityError

urls_bp = Blueprint("urls", __name__)

MAX_RETRIES = 5


def is_valid_url(url):
    try:
        result = urlparse(url)
        return result.scheme in ("http", "https") and bool(result.netloc) and len(url) <= 2048
    except Exception:
        return False


def create_url(original_url):
    for _ in range(MAX_RETRIES):
        short_code = secrets.token_urlsafe(6)
        try:
            return Url.create(original_url=original_url, short_code=short_code)
        except IntegrityError:
            continue
    return None


@urls_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@urls_bp.route("/", methods=["POST"])
def index_post():
    original_url = (request.form.get("url") or "").strip()

    if not original_url or not is_valid_url(original_url):
        return render_template("index.html", error="A valid URL is required (must start with http:// or https://).")

    url = create_url(original_url)
    if url is None:
        return render_template("index.html", error="Could not generate a unique short code. Please try again.")

    return render_template("index.html", short_url=f"/{url.short_code}", short_code=url.short_code, submitted_url=original_url)


@urls_bp.route("/shorten", methods=["POST"])
def shorten():
    data = request.get_json()
    original_url = ((data.get("url") or "").strip()) if data else ""

    if not original_url or not is_valid_url(original_url):
        return jsonify({"error": "a valid url is required (must start with http:// or https://)"}), 400

    url = create_url(original_url)
    if url is None:
        return jsonify({"error": "could not generate a unique short code"}), 500

    return jsonify({"short_code": url.short_code, "short_url": f"{request.host_url}{url.short_code}"}), 201


@urls_bp.route("/<short_code>", methods=["GET"])
def redirect_to_url(short_code):
    try:
        url = Url.get(Url.short_code == short_code)
        return redirect(url.original_url)
    except DoesNotExist:
        return jsonify({"error": "short code not found"}), 404
