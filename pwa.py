"""Public install/update assets. Never serve private data through this module."""

from pathlib import Path

from flask import Blueprint, send_from_directory


ROOT = Path(__file__).resolve().parent
pwa_bp = Blueprint("pwa", __name__)


@pwa_bp.get("/manifest.json")
def manifest():
    return send_from_directory(
        ROOT / "static", "manifest.json", mimetype="application/manifest+json"
    )


@pwa_bp.get("/sw.js")
def service_worker():
    response = send_from_directory(
        ROOT / "static", "sw.js", mimetype="application/javascript"
    )
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@pwa_bp.get("/offline.html")
def offline():
    return send_from_directory(ROOT / "templates", "offline.html")


@pwa_bp.get("/icon-<int:size>.png")
def icon(size):
    if size not in (180, 192, 512):
        return "", 404
    return send_from_directory(ROOT / "static", f"icon-{size}.png")


@pwa_bp.after_app_request
def update_headers(response):
    from flask import request

    if request.path in ("/", "/manifest.json", "/sw.js"):
        response.headers["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
    if request.path == "/offline.html":
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; img-src 'self'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
        )
    return response
