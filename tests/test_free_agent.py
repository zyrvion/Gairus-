import copy
import importlib
import io
import json
from pathlib import Path
import sys
import wave

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "deploy" / "huggingface"
sys.path.insert(0, str(SOURCE))
agent = importlib.import_module("free_agent")
media = importlib.import_module("media_tools")
agent_store = importlib.import_module("agent_store")
state = importlib.import_module("state")


def plan(kind="document"):
    return {"kind": kind, "title": "Essai français", "content": "Un résultat réellement produit.",
            "slides": ["Première étape", "Résultat"] if kind == "presentation" else []}


def audio():
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x10\x00" * 2400)
    return media.checked_file("narration.wav", stream.getvalue())


def test_document_is_actually_written_and_hash_verified():
    job, files = agent.execute("Écris un document", lambda _: json.dumps(plan()))
    assert job["status"] == "completed" and job["cost"] == 0
    assert files[0]["bytes"].startswith("# Essai français".encode())
    assert job["artifacts"][0]["sha256"] == files[0]["sha256"]
    assert [step["tool"] for step in job["journal"]] == ["write_document"]
    assert not job["external_actions"]


def test_full_pipeline_calls_tools_and_records_only_real_outputs():
    calls = []

    def speak(content):
        calls.append(("voice", content))
        return audio()

    def video(title, slides, wav):
        calls.append(("video", slides, wav))
        return media.checked_file("presentation.mp4", b"\x00\x00\x00\x18ftypisom-test")

    job, files = agent.execute(
        "Crée une présentation", lambda _: plan("presentation"),
        requested="presentation", speech_tool=speak, video_tool=video,
    )
    assert len(calls) == 2 and len(files) == 3
    assert [step["tool"] for step in job["journal"]] == [
        "write_document", "synthesize_speech", "render_presentation",
    ]


@pytest.mark.parametrize("raw", [
    "pas du JSON", {"kind": "send_slack"}, {**plan(), "shell": "touch /tmp/unsafe"},
    {**plan(), "kind": "neural_video"}, {**plan(), "kind": "unsupported"},
    {**plan(), "content": "x" * 1201},
    {**plan(), "slides": "not a list"}, {**plan("presentation"), "slides": []},
])
def test_invalid_model_plans_fail_before_any_tool(raw):
    called = []
    with pytest.raises(state.StoreError):
        agent.execute("Objectif", lambda _: raw, speech_tool=lambda _: called.append(1))
    assert called == []


@pytest.mark.parametrize("tool,source,cost", [
    ("send_slack", "local-cpu", 0), ("synthesize_speech", "elevenlabs", 0),
    ("render_presentation", "local-cpu", 0.01),
    ("write_document", "unverified-free-api", 0),
])
def test_unknown_or_paid_routes_are_rejected(tool, source, cost):
    with pytest.raises(state.StoreError):
        agent.assert_free(tool, source, cost)


def test_format_mismatch_is_not_silently_downgraded():
    with pytest.raises(state.StoreError, match="format demandé"):
        agent.execute("Vidéo", lambda _: plan("document"), requested="presentation")


def test_tool_failure_is_not_marked_complete():
    def failed(_):
        raise RuntimeError("CPU unavailable")

    with pytest.raises(RuntimeError):
        agent.execute("Audio", lambda _: plan("voice"), speech_tool=failed)


def test_wrong_file_cannot_be_claimed_as_voice():
    with pytest.raises(state.StoreError, match="fichier attendu"):
        agent.execute("Audio", lambda _: plan("voice"), speech_tool=lambda _: media.checked_file("document.md", b"text"))


def test_private_downloads_never_use_public_gradio_cache():
    rendered = media.private_preview([audio(), media.checked_file("document.md", b"Private content")])
    assert "data:audio/wav;base64," in rendered
    assert "download=" in rendered
    assert "/gradio_api/file" not in rendered and "https://" not in rendered


@pytest.mark.parametrize("name,payload", [
    ("../private.env", b"x"), ("narration.wav", b"not-a-wave"),
    ("presentation.mp4", b"not-a-video"), ("document.md", b""),
])
def test_artifact_paths_formats_and_empty_files_are_rejected(name, payload):
    with pytest.raises(ValueError):
        media.checked_file(name, payload)


def test_model_json_fence_is_accepted_without_evaluation():
    assert agent.validate_plan("```json\n" + json.dumps(plan()) + "\n```")["kind"] == "document"


def test_persistence_adds_private_files_without_replacing_prior_data():
    class Store:
        def update(self, token, mutate, **kwargs):
            current = state.new_state()
            current["future"] = {"keep": True}
            state.add_memory(current, "Une note existante")
            mutate(current)
            assert current["future"] == {"keep": True}
            assert len(current["memories"]) == 1
            assert len(kwargs["artifact_files"]) == 1
            assert kwargs["artifact_files"][0][0].endswith("/document.md")
            return current

    job, files = agent.execute("Document", lambda _: plan())
    saved = agent_store.save_job(Store(), "test-only", job, files)
    assert saved["agent_runs"][0]["status"] == "completed"


def test_bad_artifact_manifest_cannot_be_saved():
    job, files = agent.execute("Document", lambda _: plan())
    altered = copy.deepcopy(job)
    altered["artifacts"][0]["sha256"] = "wrong"
    with pytest.raises(state.StoreError, match="preuves"):
        agent_store.save_job(None, "test-only", altered, files)


def test_onnx_adapter_matches_scalar_dtype_and_mono_shape():
    np = pytest.importorskip("numpy")
    from types import SimpleNamespace

    class Session:
        _model_path = "synthetic-test-model.onnx"

        def get_inputs(self):
            return [SimpleNamespace(name="speed", type="tensor(float)")]

        def run(self, outputs, inputs):
            assert inputs["speed"].dtype == np.float32
            return [np.ones((1, 24000), dtype=np.float32)]

    output = media._TypedSession(Session()).run(None, {"speed": np.array([1], dtype=np.int32)})
    assert output[0].shape == (24000,)


def test_binary_storage_is_bounded_text_not_public_media():
    import base64
    payload = b"RIFF" + b"\0" * 4 + b"WAVE" + b"\1" * 64
    name, encoded = agent_store.stored_file(media.checked_file("narration.wav", payload))
    assert name == "narration.wav.b64"
    assert encoded.isascii()
    assert base64.b64decode(encoded, validate=True) == payload


@pytest.mark.parametrize("tamper", ["none", "hash", "encoding"])
def test_private_reopen_checks_decoded_audio_integrity(monkeypatch, tamper):
    import base64
    from types import SimpleNamespace

    item = audio()
    metadata = {key: item[key] for key in ("name", "mime", "sha256", "size")}
    if tamper == "hash":
        metadata["sha256"] = "incorrect"
    run_id = "a" * 32
    job = {"id": run_id, "artifacts": [metadata]}

    class Store:
        repo_id = "test-only/private"

        def _client(self, token):
            return None

        def _read(self, client, token):
            return {"agent_runs": [job]}, "test-revision"

    def get(url, **kwargs):
        assert url.endswith(f"/raw/test-revision/artifacts/{run_id}/narration.wav.b64")
        payload = b"invalid base64!" if tamper == "encoding" else base64.b64encode(item["bytes"])
        return SimpleNamespace(content=payload, raise_for_status=lambda: None)

    monkeypatch.setattr(agent_store.requests, "get", get)
    if tamper == "none":
        reopened, files = agent_store.load_job(Store(), "test-only", run_id)
        assert reopened == job and files[0]["bytes"] == item["bytes"]
    else:
        with pytest.raises(state.StoreError):
            agent_store.load_job(Store(), "test-only", run_id)
