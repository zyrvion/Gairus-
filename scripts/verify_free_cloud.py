"""Production guardrails and removal of this session's synthetic QA fixtures."""

import argparse
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleanup-qa", action="store_true")
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
