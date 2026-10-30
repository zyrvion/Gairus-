"""Fail-closed authentication for an owner-only cloud deployment."""
import hmac
import os
from flask import jsonify, request


def install_web_auth(app):
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    @app.before_request
    def protect_api():
        if not request.path.startswith("/api/"):
            return None
        if request.path in {"/api/slack/events", "/api/orta/chat"}:
            return None  # These handlers validate their own scoped credentials.
        if request.method == "OPTIONS":
            return "", 204
        key = os.getenv("GAIRUS_ADMIN_KEY", "").strip()
        if len(key) < 32:
            return jsonify(
                ok=False, error="admin_key_not_configured",
                message="Configurer GAIRUS_ADMIN_KEY (32 caractères minimum) sur le serveur.",
            ), 503
        scheme, _, supplied = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(
            supplied.encode("utf-8"), key.encode("utf-8")
        ):
            return jsonify(ok=False, error="authentication_required",
                           message="Authentification requise."), 401
        return None

    @app.after_request
    def response_security(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
