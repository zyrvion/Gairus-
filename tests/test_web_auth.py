from flask import Flask
from security.web_auth import install_web_auth


def client():
    app = Flask(__name__)
    install_web_auth(app)
    app.add_url_rule("/api/memory", endpoint="memory", view_func=lambda: {"ok": True})
    app.add_url_rule("/healthz", endpoint="health", view_func=lambda: {"ok": True})
    app.add_url_rule("/api/slack/events", endpoint="slack", view_func=lambda: {"challenge": "test"}, methods=["POST"])
    app.add_url_rule("/api/orta/chat", endpoint="orta", view_func=lambda: {"scoped": True}, methods=["POST"])
    return app.test_client()


def test_unconfigured_api_is_closed(monkeypatch):
    monkeypatch.delenv("GAIRUS_ADMIN_KEY", raising=False)
    assert client().get("/api/memory").status_code == 503


def test_short_key_is_rejected(monkeypatch):
    monkeypatch.setenv("GAIRUS_ADMIN_KEY", "too-short")
    assert client().get("/api/memory").status_code == 503


def test_missing_or_wrong_key_is_rejected(monkeypatch):
    monkeypatch.setenv("GAIRUS_ADMIN_KEY", "k" * 40)
    c = client()
    assert c.get("/api/memory").status_code == 401
    assert c.get("/api/memory", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert c.get("/api/memory", headers={"Authorization": "Bearer " + "é" * 40}).status_code == 401


def test_correct_key_is_accepted_without_caching(monkeypatch):
    monkeypatch.setenv("GAIRUS_ADMIN_KEY", "k" * 40)
    response = client().get("/api/memory", headers={"Authorization": "Bearer " + "k" * 40})
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"


def test_health_slack_and_orta_keep_their_own_boundary(monkeypatch):
    monkeypatch.delenv("GAIRUS_ADMIN_KEY", raising=False)
    c = client()
    assert c.get("/healthz").status_code == 200
    assert c.post("/api/slack/events").status_code == 200
    assert c.post("/api/orta/chat").status_code == 200
