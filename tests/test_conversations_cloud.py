import app as app_module


def test_server_history_is_owner_only_and_chronological(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "DB", tmp_path / "test.db")
    monkeypatch.setenv("GAIRUS_ADMIN_KEY", "test-owner-only-key-" + "x" * 32)
    app_module.init_db()
    app_module.save_message("user", "Test question")
    app_module.save_message("assistant", "Test answer")
    client = app_module.app.test_client()
    assert client.get("/api/conversations").status_code == 401
    response = client.get(
        "/api/conversations",
        headers={"Authorization": "Bearer " + "test-owner-only-key-" + "x" * 32},
    )
    assert response.status_code == 200
    assert [item["content"] for item in response.json] == ["Test question", "Test answer"]
    assert response.headers["Cache-Control"] == "no-store"
