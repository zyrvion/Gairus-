"""Public PWA routes are testable without importing/altering an owner database."""

import json
import struct
import subprocess

from flask import Flask
import pytest

from pwa import ROOT, pwa_bp
from security.web_auth import install_web_auth


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(pwa_bp)
    install_web_auth(app)
    app.add_url_rule("/", endpoint="home", view_func=lambda: "public shell")
    app.add_url_rule("/api/memory", endpoint="memory", view_func=lambda: {"private": True})
    return app.test_client()


def test_stable_manifest_and_real_safe_area_icons(client):
    response = client.get("/manifest.json")
    assert response.status_code == 200
    assert response.mimetype == "application/manifest+json"
    manifest = json.loads(response.data)
    assert manifest["id"] == manifest["scope"] == manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["lang"] == "fr"
    for icon in manifest["icons"]:
        response = client.get(icon["src"])
        assert response.status_code == 200
        assert response.mimetype == "image/png"
        assert response.data.startswith(b"\x89PNG\r\n\x1a\n")
        size = int(icon["sizes"].split("x")[0])
        assert struct.unpack(">II", response.data[16:24]) == (size, size)
    assert client.get("/icon-180.png").status_code == 200
    assert client.get("/icon-999.png").status_code == 404


@pytest.mark.parametrize("path", ["/", "/manifest.json", "/sw.js"])
def test_shell_and_worker_revalidate_instead_of_retaining_old_release(client, path):
    response = client.get(path)
    assert "no-cache" in response.headers["Cache-Control"]
    assert "must-revalidate" in response.headers["Cache-Control"]
    if path == "/sw.js":
        assert response.headers["Service-Worker-Allowed"] == "/"


def test_offline_page_is_public_static_and_makes_no_success_claim(client):
    response = client.get("/offline.html")
    assert response.status_code == 200
    assert "Aucune nouvelle tâche" in response.text
    assert "<script" not in response.text
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_pwa_keeps_api_boundary_and_does_not_expose_owner_key(client, monkeypatch):
    monkeypatch.setenv("GAIRUS_ADMIN_KEY", "private-test-key-" + "x" * 40)
    assert client.get("/api/memory").status_code == 401
    response = client.get(
        "/api/memory",
        headers={"Authorization": "Bearer private-test-key-" + "x" * 40},
    )
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    for path in ("/manifest.json", "/sw.js", "/offline.html"):
        assert "private-test-key" not in client.get(path).text


def test_worker_cache_privacy_and_update_lifecycle():
    result = subprocess.run(
        ["node", str(ROOT / "tests" / "pwa_worker_checks.cjs")],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PWA worker checks passed" in result.stdout
