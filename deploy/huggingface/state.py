"""Owner-only, private Hub persistence; no secrets or production seed data."""

import copy
import hashlib
import json
import os
import re
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone

OWNER = os.getenv("SPACE_AUTHOR_NAME", "NostraEmpire")
REPO_ID = f"{OWNER}/gairus-private-state"
MAX_STATE_BYTES = 2_000_000
STATUSES = ("À faire", "En cours", "Terminé")
_identities = {}
_identity_lock = threading.Lock()


class StoreError(RuntimeError):
    pass


class AccessDenied(StoreError):
    pass


def require_service_key(authorization, expected):
    scheme, _, supplied = str(authorization or "").partition(" ")
    if (
        not isinstance(expected, str)
        or len(expected) < 40
        or scheme.casefold() != "bearer"
        or not secrets.compare_digest(expected.encode(), supplied.encode())
    ):
        raise AccessDenied("Accès API non autorisé.")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_state():
    return {"version": 1, "threads": [], "missions": [], "memories": []}


def validate_state(value):
    if not isinstance(value, dict) or value.get("version") != 1:
        raise StoreError("Le format du dépôt de données n'est pas reconnu.")
    for field in ("threads", "missions", "memories"):
        if not isinstance(value.get(field), list):
            raise StoreError("Les données privées sont incomplètes.")
        if not all(isinstance(item, dict) for item in value[field]):
            raise StoreError("Les données privées sont invalides.")
    for thread in value["threads"]:
        if not isinstance(thread.get("messages"), list):
            raise StoreError("Une conversation n'est pas valide.")
        for message in thread["messages"]:
            if (
                not isinstance(message, dict)
                or message.get("role") not in ("user", "assistant")
                or not isinstance(message.get("content"), str)
            ):
                raise StoreError("Un message sauvegardé n'est pas valide.")
    return value


def text(value, label, limit=8000):
    if not isinstance(value, str) or not value.strip():
        raise StoreError(f"{label} est requis.")
    value = value.strip()
    if len(value) > limit:
        raise StoreError(f"{label} dépasse la limite de {limit} caractères.")
    return value


def require_owner(profile, oauth_token, identity_lookup=None):
    """Both the verified OAuth profile and the actual token must be the owner."""
    if profile is None or oauth_token is None:
        raise AccessDenied("Connecte-toi avec le compte Hugging Face propriétaire.")
    if getattr(profile, "username", "").casefold() != OWNER.casefold():
        raise AccessDenied("Cet espace est réservé à son propriétaire.")
    value = getattr(oauth_token, "token", "")
    expiry = getattr(oauth_token, "expires_at", 0)
    if not value or not isinstance(expiry, (int, float)) or expiry <= time.time():
        raise AccessDenied("La connexion a expiré. Déconnecte-toi puis reconnecte-toi.")
    digest = hashlib.sha256(value.encode()).hexdigest()
    with _identity_lock:
        cached = _identities.get(digest)
    if cached and cached > time.time():
        return value
    if identity_lookup is None:
        from huggingface_hub import HfApi

        identity_lookup = lambda token: HfApi(token=token).whoami()
    identity = identity_lookup(value)
    if str(identity.get("name", "")).casefold() != OWNER.casefold():
        raise AccessDenied("L'identité du compte n'a pas pu être confirmée.")
    with _identity_lock:
        # Cache only a hash and expiry, never the token or the full profile.
        _identities[digest] = min(time.time() + 180, expiry)
        for key in list(_identities):
            if _identities[key] <= time.time():
                _identities.pop(key, None)
    return value


class HubState:
    def __init__(self, repo_id=REPO_ID, client_factory=None, downloader=None):
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo_id):
            raise ValueError("Invalid state repository identifier")
        self.repo_id = repo_id
        self.client_factory = client_factory
        self.downloader = downloader

    def _client(self, token):
        if self.client_factory:
            return self.client_factory(token)
        from huggingface_hub import HfApi

        return HfApi(token=token)

    def _read(self, api, token):
        info = api.repo_info(self.repo_id, repo_type="dataset")
        if info.private is not True:
            raise AccessDenied("Le stockage doit rester privé. Aucune donnée n'a été écrite.")
        if not info.sha:
            raise StoreError("Le dépôt de données n'est pas initialisé.")
        if self.downloader:
            raw = self.downloader(self.repo_id, info.sha, token)
        else:
            import requests

            response = requests.get(
                f"https://huggingface.co/datasets/{self.repo_id}/resolve/{info.sha}/state.json",
                headers={"Authorization": f"Bearer {token}"},
                timeout=(10, 35),
            )
            response.raise_for_status()
            raw = response.content
        if len(raw) > MAX_STATE_BYTES:
            raise StoreError("La limite de taille du stockage de cette version est atteinte.")
        return validate_state(json.loads(raw)), info.sha

    def read(self, token):
        state, _ = self._read(self._client(token), token)
        return state

    def update(self, token, mutate, message="Gaïrus: mise à jour privée", artifact_files=()):
        from huggingface_hub import CommitOperationAdd

        artifacts = []
        for path, content in artifact_files:
            if (
                not re.fullmatch(r"artifacts/[0-9a-f]{32}/(document\.md|narration\.wav\.b64|presentation\.mp4\.b64)", path)
                or not isinstance(content, bytes) or not 1 <= len(content) <= 8_000_000
            ):
                raise StoreError("Le fichier de résultat n'est pas autorisé.")
            artifacts.append(CommitOperationAdd(path_in_repo=path, path_or_fileobj=content))
        if len(artifacts) > 3:
            raise StoreError("Un travail ne peut produire que trois fichiers.")
        api = self._client(token)
        for attempt in range(3):
            state, revision = self._read(api, token)
            candidate = copy.deepcopy(state)
            mutate(candidate)
            validate_state(candidate)
            payload = json.dumps(candidate, ensure_ascii=False, sort_keys=True).encode("utf-8")
            if len(payload) > MAX_STATE_BYTES:
                raise StoreError("Le stockage est plein. Rien n'a été effacé.")
            try:
                api.create_commit(
                    repo_id=self.repo_id,
                    repo_type="dataset",
                    operations=[CommitOperationAdd(path_in_repo="state.json", path_or_fileobj=payload), *artifacts],
                    commit_message=message,
                    parent_commit=revision,
                )
                return candidate
            except Exception as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status != 409 or attempt == 2:
                    raise StoreError(
                        "La sauvegarde privée a échoué. Les données précédentes sont conservées."
                    ) from exc
        raise StoreError("Une autre mise à jour est en cours. Réessaie.")


def append_exchange(state, thread_id, prompt, answer, exchange_id=None):
    prompt = text(prompt, "Le message")
    answer = text(answer, "La réponse", limit=32000)
    thread = next((t for t in state["threads"] if t.get("id") == thread_id), None)
    if thread is None:
        if thread_id:
            raise StoreError("Cette conversation n'existe pas.")
        if len(state["threads"]) >= 100:
            raise StoreError("La limite de 100 conversations est atteinte.")
        thread = {"id": exchange_id or uuid.uuid4().hex, "title": prompt[:70], "messages": []}
        state["threads"].append(thread)
    if len(thread["messages"]) >= 400:
        raise StoreError("Cette conversation est longue. Ouvre une nouvelle conversation.")
    thread["messages"].extend(
        [{"role": "user", "content": prompt}, {"role": "assistant", "content": answer}]
    )
    thread["updated_at"] = now()
    return thread["id"]


def add_memory(state, content, memory_id=None):
    if len(state["memories"]) >= 500:
        raise StoreError("La limite de 500 mémoires est atteinte.")
    state["memories"].append(
        {"id": memory_id or uuid.uuid4().hex, "content": text(content, "La mémoire", 2000), "created_at": now()}
    )


def add_mission(state, title, objective, plan, mission_id=None):
    if len(state["missions"]) >= 300:
        raise StoreError("La limite de 300 missions est atteinte.")
    state["missions"].append(
        {
            "id": mission_id or uuid.uuid4().hex,
            "title": text(title, "Le titre", 140),
            "objective": text(objective, "L'objectif"),
            "plan": text(plan, "Le plan", 32000),
            "status": STATUSES[0],
            "created_at": now(),
        }
    )


def set_mission_status(state, mission_id, status):
    if status not in STATUSES:
        raise StoreError("Ce statut n'est pas reconnu.")
    mission = next((m for m in state["missions"] if m.get("id") == mission_id), None)
    if mission is None:
        raise StoreError("Cette mission n'existe pas.")
    mission["status"] = status
    mission["updated_at"] = now()
