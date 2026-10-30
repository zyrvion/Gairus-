import pytest
import autonomy
from self_code_tools import _safe_path


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    monkeypatch.setattr(autonomy, "DB_PATH", str(tmp_path / "runtime.db"))
    autonomy.init_autonomy()
    monkeypatch.setattr(
        autonomy, "ask_resilient",
        lambda *args, **kwargs: {"reply": "Test synthesis; no external AI request."},
    )
    return autonomy


def test_model_cannot_bypass_write_approval(runtime):
    mission = runtime.create_mission("Test", "No external effects")
    task = runtime.create_task(mission, "Write request")
    action = runtime.create_action(task, "write_code", {"path": "test.py", "content": ""}, False)
    row = runtime.get_action(action)
    assert row["status"] == "waiting_approval"
    assert row["requires_approval"] == 1
    assert row["approval_id"]


def test_native_parameter_dictionary_executes(runtime):
    mission = runtime.create_mission("Test", "Read system status")
    task = runtime.create_task(mission, "Status")
    action = runtime.create_action(task, "system_status", {"marker": "test"})
    result = runtime.autonomous_mission_cycle(mission)
    assert result["ok"]
    assert result["results"][0]["ok"]
    assert runtime.get_action(action)["status"] == "completed"


def test_failed_native_tool_is_not_marked_complete(runtime, monkeypatch):
    monkeypatch.setitem(
        runtime.TOOL_REGISTRY, "test_failure",
        lambda parameters: {"ok": False, "error": "Expected QA failure"},
    )
    mission = runtime.create_mission("Test", "Failure handling")
    task = runtime.create_task(mission, "Fail")
    action = runtime.create_action(task, "test_failure")
    result = runtime.autonomous_mission_cycle(mission)
    assert result["results"][0]["ok"] is False
    assert runtime.get_action(action)["status"] == "failed"


@pytest.mark.parametrize("path", [".env", "data/private.db", "../outside", "/etc/passwd", ".git/config", "server.pem"])
def test_self_code_tools_cannot_read_secrets(path):
    with pytest.raises(ValueError):
        _safe_path(path)
