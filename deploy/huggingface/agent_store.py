"""Private atomic artifact persistence; no public file-cache download URLs."""

import base64
import re

import requests

from media_tools import checked_file
from state import StoreError


def stored_file(item):
    # Bounded base64 text blobs keep authenticated I/O on the Hub HTTPS host,
    # without a second binary/Xet transport. User downloads remain WAV/MP4.
    if item["name"] == "document.md":
        return item["name"], item["bytes"]
    return item["name"] + ".b64", base64.b64encode(item["bytes"])


def runs(state):
    result = state.get("agent_runs", [])
    if not isinstance(result, list) or not all(isinstance(run, dict) for run in result):
        raise StoreError("Les travaux sauvegardés ont un format non reconnu.")
    return result


def save_job(store, token, job, files):
    if not re.fullmatch(r"[0-9a-f]{32}", job["id"]) or job["status"] != "completed":
        raise StoreError("Un travail incomplet n'est pas marqué comme terminé.")
    checked = [checked_file(item["name"], item["bytes"]) for item in files]
    if job["artifacts"] != [
        {key: item[key] for key in ("name", "mime", "sha256", "size")} for item in checked
    ]:
        raise StoreError("Les preuves des fichiers ne correspondent pas au travail.")

    def append(state):
        previous = runs(state)
        if len(previous) >= 50:
            raise StoreError("La limite de 50 travaux est atteinte. Aucun résultat précédent n'a été effacé.")
        if any(run["id"] == job["id"] for run in previous):
            raise StoreError("Ce travail est déjà sauvegardé.")
        state["agent_runs"] = [*previous, job]

    return store.update(
        token, append, message="Gaïrus: travail exécuté et fichiers privés",
        artifact_files=[
            (f'artifacts/{job["id"]}/{name}', payload)
            for item in checked for name, payload in [stored_file(item)]
        ],
    )


def load_job(store, token, run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise StoreError("Sélectionne un travail sauvegardé.")
    state, revision = store._read(store._client(token), token)
    job = next((run for run in runs(state) if run["id"] == run_id), None)
    if not job:
        raise StoreError("Ce travail n'existe pas.")
    if not isinstance(job.get("artifacts"), list) or len(job["artifacts"]) > 3:
        raise StoreError("Le manifeste des fichiers n'est pas valide.")
    files = []
    for metadata in job["artifacts"]:
        # Validate name before forming a URL; prevents traversal and remote reads.
        name = metadata.get("name")
        if name not in ("document.md", "narration.wav", "presentation.mp4"):
            raise StoreError("Le type de résultat n'est pas reconnu.")
        stored_name = name if name == "document.md" else name + ".b64"
        response = requests.get(
            f"https://huggingface.co/datasets/{store.repo_id}/raw/{revision}/artifacts/{run_id}/{stored_name}",
            headers={"Authorization": f"Bearer {token}"}, timeout=(10, 45),
        )
        response.raise_for_status()
        payload = response.content
        if len(payload) > 8_000_000:
            raise StoreError("Le fichier sauvegardé dépasse la limite autorisée.")
        if name != "document.md":
            try:
                payload = base64.b64decode(payload, validate=True)
            except ValueError:
                raise StoreError("Le fichier sauvegardé n'est pas valide.") from None
        item = checked_file(name, payload)
        if (
            item["sha256"] != metadata.get("sha256")
            or item["size"] != metadata.get("size")
            or item["mime"] != metadata.get("mime")
        ):
            raise StoreError("L'intégrité d'un résultat sauvegardé n'a pas pu être confirmée.")
        files.append(item)
    return job, files
