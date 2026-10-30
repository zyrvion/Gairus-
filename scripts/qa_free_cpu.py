"""LOCAL QA ONLY: synthetic OAuth, in-memory state and model; real CPU media."""

import copy
import json
import os
import secrets
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy/huggingface"))
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
os.environ["GAIRUS_SERVICE_KEY"] = secrets.token_hex(32)

import gradio.oauth
import gradio as gr
from fastapi import FastAPI


def mocked_oauth():
    return {
        "access_token": "qa-only-not-a-real-credential",
        "token_type": "bearer", "expires_in": 3600,
        "expires_at": int(time.time()) + 3600, "scope": "openid profile",
        "userinfo": {
            "sub": "qa-only", "name": "QA uniquement",
            "preferred_username": "NostraEmpire",
            "profile": "", "picture": "", "website": "",
        },
    }


gradio.oauth._get_mocked_oauth_info = mocked_oauth

import app
import agent_store
from state import new_state, require_owner, validate_state


class MemoryStore:
    repo_id = "qa-only/no-real-dataset"

    def __init__(self):
        self.state = new_state()
        self.files = {}

    def read(self, token):
        return copy.deepcopy(self.state)

    def _client(self, token):
        return None

    def _read(self, client, token):
        return self.read(token), "qa-only"

    def update(self, token, mutate, message="", artifact_files=()):
        candidate = self.read(token)
        mutate(candidate)
        validate_state(candidate)
        self.files.update(dict(artifact_files))
        self.state = candidate
        return self.read(token)

    def get_artifact(self, url, **kwargs):
        path = "artifacts/" + url.split("/artifacts/", 1)[1]
        return SimpleNamespace(
            content=self.files[path], raise_for_status=lambda: None,
        )


store = MemoryStore()
app.STORE = store
app.authorized = lambda profile, token: require_owner(
    profile, token, identity_lookup=lambda _: {"name": "NostraEmpire"},
)
agent_store.requests = SimpleNamespace(get=store.get_artifact)


def fake_generate(messages):
    if "planificateur" in messages[0]["content"]:
        return json.dumps({
            "kind": "document", "title": "QA modèle synthétique",
            "content": "Document de test local, non produit par le modèle réel.",
            "slides": [],
        })
    return "Réponse de test locale. Aucun message externe envoyé."


app.inference.generate = fake_generate
application = gr.mount_gradio_app(
    FastAPI(), app.build_demo(), path="/",
    css_paths=Path(app.__file__).with_name("style.css"),
    theme=gr.themes.Base(
        primary_hue="blue", neutral_hue="slate",
        font=[gr.themes.GoogleFont("Public Sans"), "sans-serif"],
    ),
    footer_links=[],
)
