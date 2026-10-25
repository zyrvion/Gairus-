from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def service():
    manifest = yaml.safe_load((ROOT / "render.yaml").read_text(encoding="utf-8"))
    assert len(manifest["services"]) == 1
    return manifest["services"][0]


def test_render_uses_persistent_single_instance_docker(service):
    assert service["runtime"] == "docker"
    assert service["plan"] == "0.5c-512mb"
    assert service["numInstances"] == 1
    assert service["region"] == "frankfurt"
    assert service["disk"] == {
        "name": "gairus-data", "mountPath": "/app/data", "sizeGB": 1,
    }


def test_render_does_not_deploy_main_or_new_commits_automatically(service):
    assert service["repo"] == "https://github.com/zyrvion/Gairus-"
    assert service["branch"] == "repair/cloud-hardening-20261025"
    assert service["autoDeployTrigger"] == "off"
    assert service["healthCheckPath"] == "/healthz"
    assert "domains" not in service  # Add only after checking ownership and DNS.


def test_render_persists_all_configurable_databases(service):
    env = {item["key"]: item for item in service["envVars"]}
    assert env["GAIRUS_DATA_DIR"]["value"] == "/app/data"
    assert env["GAIRUS_DB"]["value"] == "/app/data/gairus.db"
    assert env["GAIRUS_SLACK_MEMORY_DB"]["value"] == "/app/data/slack_memory.db"
    # The mount must also catch legacy modules using PROJECT_ROOT / "data".
    assert "WORKDIR /app" in (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_render_secrets_are_generated_not_committed(service):
    env = {item["key"]: item for item in service["envVars"]}
    for key in ("GAIRUS_ADMIN_KEY", "GAIRUS_ORTA_API_KEY"):
        assert env[key] == {"key": key, "generateValue": True}
    for item in env.values():
        assert item.get("sync") is not False  # No mandatory unused provider keys.
    assert not any(key in env for key in (
        "OPENAI_API_KEY", "GEMINI_API_KEY", "SLACK_BOT_TOKEN", "SLACK_APP_TOKEN",
    ))


def test_render_starts_with_approvals_and_no_autonomy(service):
    env = {item["key"]: item for item in service["envVars"]}
    assert env["GAIRUS_AUTONOMY"]["value"] == "false"
    assert env["GAIRUS_APPROVALS"]["value"] == "true"
    assert env["GAIRUS_FREE_ONLY"]["value"] == "true"
    assert env["GAIRUS_ALLOWED_ORIGINS"]["value"] == "https://gairus.zyrvion.io"


def test_docker_build_excludes_committed_user_data(service):
    ignore = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())
    assert {"data", "**/*.db", "**/*.jsonl", ".env", ".git"} <= ignore
    assert service["dockerContext"] == "."
