"""Real deployed inference/media smoke test. Never prints the service key."""

import argparse
import base64
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import time

from gradio_client import Client


class Downloads(HTMLParser):
    def __init__(self):
        super().__init__()
        self.files = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag != "a":
            return
        name = attributes.get("download")
        if name not in ("document.md", "narration.wav", "presentation.mp4"):
            return
        uri = attributes.get("href", "")
        prefix, separator, encoded = uri.partition(";base64,")
        if separator and prefix.startswith("data:"):
            self.files[name] = base64.b64decode(encoded, validate=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--url", default="https://nostraempire-gairus.hf.space")
    parser.add_argument("--kind", choices=("document", "voice", "presentation"), default="presentation")
    args = parser.parse_args()
    if args.key_file.stat().st_mode & 0o077:
        raise SystemExit("Unsafe service-key permissions.")
    client = Client(args.url, headers={"Authorization": f"Bearer {args.key_file.read_text().strip()}"})
    objectives = {
        "document": "Rédige trois phrases expliquant la différence entre un plan proposé et une action exécutée.",
        "voice": "Produis une voix française disant : Bonjour, je suis Gaïrus. "
                 "Je peux produire une voix et une présentation vidéo, mais Slack doit encore être connecté.",
        "presentation": "Crée une courte présentation narrée de Gaïrus : objectifs, outils gratuits et limites. "
                        "Deux diapositives. N'annonce aucune intégration Slack opérationnelle.",
    }
    started = time.monotonic()
    result = client.predict(objectives[args.kind], args.kind, api_name="/service_agent")
    job = result["job"]
    assert job["status"] == "completed" and job["cost"] == 0 and not result["saved"]
    assert not job["external_actions"] and job["kind"] == args.kind
    downloads = Downloads()
    downloads.feed(result["preview_html"])
    assert set(downloads.files) == {item["name"] for item in job["artifacts"]}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in job["artifacts"]:
        content = downloads.files[item["name"]]
        assert len(content) == item["size"]
        assert hashlib.sha256(content).hexdigest() == item["sha256"]
        (args.output_dir / item["name"]).write_bytes(content)
    print({
        "real_deployed_pipeline": True, "kind": job["kind"],
        "verified_files": [item["name"] for item in job["artifacts"]],
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "external_actions": False, "personal_storage_written": False,
    })


if __name__ == "__main__":
    main()
