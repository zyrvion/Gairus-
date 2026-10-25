"""LOCAL QA ONLY. Not shipped to the Space. Synthetic inference, real Hub I/O."""

import importlib.util
from pathlib import Path
import sys

import gradio as gr
import gradio.oauth
from fastapi import FastAPI
import requests

SOURCE = Path(__file__).resolve().parents[1] / "deploy" / "huggingface"
sys.path.insert(0, str(SOURCE))

# The credential proxy authenticates HTTPS at the approved host; this value is
# not a real credential. No saved token is extracted or copied into the app.
gradio.oauth.get_token = lambda: "local-proxy-placeholder-not-a-credential"
gradio.oauth.whoami = lambda: requests.get(
    "https://huggingface.co/api/whoami-v2", timeout=30
).json()
spec = importlib.util.spec_from_file_location("gairus_free_qa", SOURCE / "app.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.inference.generate = lambda messages: (
    "Validation synthétique du parcours navigateur uniquement.\n\n"
    "1. Préparer les informations.\n2. Vérifier les contraintes.\n"
    "3. Faire valider le résultat.\n\nAucune action externe n'est exécutée."
)
demo = module.build_demo()
application = gr.mount_gradio_app(
    FastAPI(), demo, path="/", server_name="127.0.0.1", server_port=8792,
    footer_links=[], css_paths=SOURCE / "style.css", enable_monitoring=False,
    show_error=False, theme=gr.themes.Base(
        primary_hue="blue", neutral_hue="slate",
        font=[gr.themes.GoogleFont("Public Sans"), "sans-serif"],
    ),
)
