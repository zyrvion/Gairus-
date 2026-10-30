"""Production guardrails and removal of this session's synthetic QA fixtures."""

import argparse
import copy
import json
from pathlib import Path
import sys

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "huggingface"))
from state import HubState

QA_IDS = {
    "26bcbde77f024f5d8e95835daee18c41",
    "27ab267f718e40ae86ea14cef22b08c4",
    "92ab7e40250f4245b8f10064ca15f4ed",
    "f56bcd5854614cbaaad594e07eafbd89",
}
CURRENT_QA_IDS = {
    "agent_runs": "33acf31eae304bbdac52e337d0ac2054",
    "threads": "6e9c580d6d58429e8b053d568c70b6c6",
    "missions": "1a3ec169a20f41d796e128972645c7f2",
    "memories": "b1fb5e3a922d4cc7a99456ac59376f31",
}
BASELINE_REVISION = "903d9d96c327dd8cb59194a0373a3c2b4273bbc8"
SYNTHETIC_REPLY = (
    "Validation synthétique du parcours navigateur uniquement.\n\n"
    "1. Préparer les informations.\n2. Vérifier les contraintes.\n"
    "3. Faire valider le résultat.\n\nAucune action externe n'est exécutée."
)


def cleanup_current(store, token):
    """Remove only exact fixtures, preserving any concurrent real user work."""
    from huggingface_hub import CommitOperationAdd, CommitOperationDelete

    api = store._client(token)
    current, revision = store._read(api, token)
    response = requests.get(
        f"https://huggingface.co/datasets/{store.repo_id}/resolve/{BASELINE_REVISION}/state.json",
        headers={"Authorization": f"Bearer {token}"}, timeout=30,
    )
    response.raise_for_status()
    baseline = response.json()
    candidate = copy.deepcopy(current)
    deletions = []
    removed = {}
    for field, own_id in CURRENT_QA_IDS.items():
        kept = []
        for item in candidate.get(field, []):
            marker = str(item.get("title", item.get("content", "")))
            if item.get("id") == own_id and marker.startswith("QA-20261030 :"):
                if field == "agent_runs":
                    deletions = [
                        f"artifacts/{own_id}/document.md",
                        f"artifacts/{own_id}/narration.wav.b64",
                        f"artifacts/{own_id}/presentation.mp4.b64",
                    ]
                removed[field] = removed.get(field, 0) + 1
            else:
                kept.append(item)
        candidate[field] = kept
    pairs_removed = 0
    for thread in candidate["threads"]:
        old = next((t for t in baseline["threads"] if t["id"] == thread["id"]), None)
        messages = thread["messages"]
        cleaned = []
        index = 0
        while index < len(messages):
            own_pair = (
                index + 1 < len(messages)
                and messages[index] == {
                    "role": "user",
                    "content": "QA-20261030 : conversation synthétique de validation.",
                }
                and messages[index + 1] == {"role": "assistant", "content": SYNTHETIC_REPLY}
            )
            if own_pair:
                pairs_removed += 1
                index += 2
            else:
                cleaned.append(messages[index])
                index += 1
        thread["messages"] = cleaned
        # Restore the timestamp only if all actual user messages are unchanged.
        if old and cleaned == old["messages"]:
            if "updated_at" in old:
                thread["updated_at"] = old["updated_at"]
            else:
                thread.pop("updated_at", None)
    existing = set(api.list_repo_files(store.repo_id, repo_type="dataset"))
    operations = [CommitOperationAdd(
        path_in_repo="state.json",
        path_or_fileobj=json.dumps(candidate, ensure_ascii=False, sort_keys=True).encode(),
    )] + [CommitOperationDelete(path_in_repo=path) for path in deletions if path in existing]
    api.create_commit(
        repo_id=store.repo_id, repo_type="dataset", parent_commit=revision,
        commit_message="Remove only identified October 30 synthetic QA fixtures",
        operations=operations,
    )
    assert store.read(token) == candidate
    print("Only exact current fixtures removed:", removed, "synthetic exchange pairs:", pairs_removed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleanup-qa", action="store_true")
    parser.add_argument("--cleanup-current-qa", action="store_true")
    args = parser.parse_args()
    response = requests.get(
        "https://huggingface.co/api/spaces/NostraEmpire/gairus/runtime", timeout=30
    )
    response.raise_for_status()
    runtime = response.json()
    assert runtime["stage"] == "RUNNING", runtime["stage"]
    assert runtime["hardware"]["current"] == "zero-a10g"
    assert runtime["hardware"]["requested"] == "zero-a10g"
    assert runtime["replicas"]["requested"] == 1
    print("Free Space RUNNING on zero-a10g, one replica.")
    store = HubState()
    # A non-secret placeholder lets the approved host proxy inject auth.
    token = "native-credential-proxy-placeholder"
    before = store.read(token)
    counts = {}
    if args.cleanup_current_qa:
        cleanup_current(store, token)
        return

    def remove_own_fixtures(state):
        for field in ("threads", "missions", "memories"):
            keep = []
            for item in state[field]:
                marker = str(item.get("title", item.get("content", "")))
                own = item.get("id") in QA_IDS and marker.startswith("QA-20261025 :")
                if field == "threads":
                    own = own and all(
                        message["content"].startswith(
                            "QA-20261025 :" if message["role"] == "user"
                            else "Validation synthétique du parcours navigateur"
                        )
                        for message in item.get("messages", [])
                    )
                if not own:
                    keep.append(item)
            counts[field] = len(state[field]) - len(keep)
            state[field] = keep

    if args.cleanup_qa:
        after = store.update(token, remove_own_fixtures, message="Gaïrus: retirer les essais synthétiques")
        assert store.read(token) == after
        print("Only known synthetic fixtures removed:", counts)
    else:
        print("Private storage readable; no mutation requested.")
    print("Stored counts:", {field: len(store.read(token)[field]) for field in before if field in ("threads", "missions", "memories")})


if __name__ == "__main__":
    main()
