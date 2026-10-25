import copy
import importlib.util
import json
from pathlib import Path
import time
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deploy" / "huggingface"
spec = importlib.util.spec_from_file_location("gairus_cloud_state", SOURCE / "state.py")
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)


@pytest.fixture(autouse=True)
def clear_auth_cache(monkeypatch):
    monkeypatch.setattr(state, "_identities", {})


def profile(name=state.OWNER):
    return SimpleNamespace(username=name)


def token(value="synthetic-test-token"):
    return SimpleNamespace(token=value, expires_at=time.time() + 3600)


def test_owner_requires_login():
    with pytest.raises(state.AccessDenied):
        state.require_owner(None, None)


def test_nonowner_profile_cannot_access_even_with_owner_token():
    with pytest.raises(state.AccessDenied):
        state.require_owner(profile("someone-else"), token())


def test_token_identity_is_checked_not_only_profile():
    with pytest.raises(state.AccessDenied):
        state.require_owner(profile(), token(), lambda _: {"name": "someone-else"})


def test_expired_token_is_rejected():
    expired = SimpleNamespace(token="expired", expires_at=time.time() - 1)
    with pytest.raises(state.AccessDenied):
        state.require_owner(profile(), expired)


def test_valid_owner_caches_only_hash():
    value = token()
    assert state.require_owner(profile(), value, lambda _: {"name": state.OWNER}) == value.token
    assert value.token not in repr(state._identities)
    assert len(next(iter(state._identities))) == 64


@pytest.mark.parametrize("header,key", [
    ("", "a" * 50), ("Bearer wrong", "a" * 50),
    ("Bearer ", ""), ("Basic " + "a" * 50, "a" * 50),
    ("Bearer " + "é" * 50, "a" * 50),
])
def test_stateless_api_fails_closed(header, key):
    with pytest.raises(state.AccessDenied):
        state.require_service_key(header, key)


def test_service_key_accepts_only_correct_bearer():
    state.require_service_key("Bearer " + "a" * 50, "a" * 50)


class FakeApi:
    def __init__(self):
        self.data = state.new_state()
        self.sha = "revision-1"
        self.private = True
        self.commits = []
        self.conflict = False
        self.fail = False

    def repo_info(self, repo, repo_type):
        assert repo_type == "dataset"
        return SimpleNamespace(private=self.private, sha=self.sha)

    def create_commit(self, **kwargs):
        if self.conflict:
            self.conflict = False
            state.add_memory(self.data, "A concurrent safe update", "concurrent")
            self.sha = "concurrent-revision"
            raise SimpleHttpError(409)
        if self.fail:
            raise SimpleHttpError(503)
        assert kwargs["parent_commit"] == self.sha
        self.commits.append(kwargs)
        self.data = json.loads(kwargs["operations"][0].path_or_fileobj)
        self.sha += "-next"


class SimpleHttpError(RuntimeError):
    def __init__(self, status):
        self.response = SimpleNamespace(status_code=status)


def store(api):
    return state.HubState(
        "Owner/private-state",
        client_factory=lambda _: api,
        downloader=lambda *args: json.dumps(api.data).encode(),
    )


def test_durable_state_round_trip_across_new_store():
    api = FakeApi()
    store(api).update("test", lambda value: state.add_memory(value, "Été\n=1+1 <script>"))
    assert store(api).read("test")["memories"][0]["content"] == "Été\n=1+1 <script>"


def test_public_dataset_is_rejected_before_read_or_write():
    api = FakeApi()
    api.private = False
    with pytest.raises(state.AccessDenied):
        store(api).update("test", lambda value: state.add_memory(value, "unsafe"))
    assert api.commits == []
    assert api.data == state.new_state()


def test_conflict_retries_without_losing_other_record():
    api = FakeApi()
    api.conflict = True
    result = store(api).update("test", lambda value: state.add_memory(value, "My update", "mine"))
    assert {m["id"] for m in result["memories"]} == {"mine", "concurrent"}


def test_save_failure_never_replaces_prior_data():
    api = FakeApi()
    api.fail = True
    before = copy.deepcopy(api.data)
    with pytest.raises(state.StoreError, match="sauvegarde privée"):
        store(api).update("test", lambda value: state.add_memory(value, "not saved"))
    assert api.data == before


def test_future_fields_are_preserved():
    api = FakeApi()
    api.data["future_extension"] = {"keep": True}
    result = store(api).update("test", lambda value: state.add_memory(value, "new"))
    assert result["future_extension"] == {"keep": True}


def test_malformed_data_is_not_reset_to_empty():
    api = FakeApi()
    api.data = {"version": 99}
    with pytest.raises(state.StoreError):
        store(api).update("test", lambda value: state.add_memory(value, "new"))
    assert api.data == {"version": 99}
    assert api.commits == []


def test_threads_and_manual_mission_status():
    value = state.new_state()
    ident = state.append_exchange(value, "", "Bonjour", "Bonjour, comment aider ?", "thread-1")
    state.append_exchange(value, ident, "La suite", "Voici la suite.")
    state.add_mission(value, "Terrain", "Préparer les visites", "Proposition uniquement", "mission-1")
    state.set_mission_status(value, "mission-1", "En cours")
    assert len(value["threads"]) == 1
    assert len(value["threads"][0]["messages"]) == 4
    assert value["missions"][0]["status"] == "En cours"
    assert "executed" not in value["missions"][0]


def test_unknown_thread_and_status_are_not_created_silently():
    value = state.new_state()
    with pytest.raises(state.StoreError):
        state.append_exchange(value, "missing", "Hello", "Answer")
    with pytest.raises(state.StoreError):
        state.set_mission_status(value, "missing", "executed")
    assert value == state.new_state()


def test_length_limit_does_not_truncate_private_data():
    value = state.new_state()
    with pytest.raises(state.StoreError):
        state.add_memory(value, "x" * 2001)
    assert value["memories"] == []


def test_free_manifest_and_cancelled_paid_blueprint():
    metadata = yaml.safe_load((SOURCE / "README.md").read_text().split("---")[1])
    assert metadata["sdk"] == "gradio"
    assert metadata["hf_oauth"] is True
    assert metadata["hf_oauth_scopes"] == ["write-repos"]
    assert not (ROOT / "render.yaml").exists()
    deploy = (ROOT / "scripts" / "deploy_free_space.py").read_text()
    assert 'hardware != "zero-a10g"' in deploy
    assert "runtime.storage is not None" in deploy
    assert "create_repo(" not in deploy


def test_no_paid_inference_fallback_or_arbitrary_model_code():
    inference = (SOURCE / "inference.py").read_text()
    assert 'MODEL_REVISION = "cdbee75f17c01a7cc42f958dc650907174af0554"' in inference
    assert "trust_remote_code=False" in inference
    assert "@GPU(duration=45)" in inference
    assert "api.openai.com" not in inference
    assert "router.huggingface.co" not in inference
