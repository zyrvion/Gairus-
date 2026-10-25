"""Deploy only the free adapter; run through the approved HF credential proxy."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile

from huggingface_hub import CommitOperationAdd, HfApi

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deploy" / "huggingface"
SPACE = "NostraEmpire/gairus"
DATASET = "NostraEmpire/gairus-private-state"
FILES = ("README.md", "requirements.txt", "state.py", "inference.py", "app.py", "style.css")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-file", type=Path)
    args = parser.parse_args()
    api = HfApi()
    identity = api.whoami()
    if identity.get("name") != "NostraEmpire":
        raise SystemExit("Wrong account; no deployment performed.")
    runtime = api.get_space_runtime(SPACE)
    for hardware in (runtime.hardware, runtime.requested_hardware):
        if hardware is not None and hardware != "zero-a10g":
            raise SystemExit("Non-free/unsupported hardware detected; refusing deployment.")
    if runtime.storage is not None:
        raise SystemExit("Persistent paid storage detected; refusing deployment.")
    if runtime.raw.get("replicas", {}).get("requested", 1) != 1:
        raise SystemExit("Unexpected replica count; refusing deployment.")
    if api.dataset_info(DATASET).private is not True:
        raise SystemExit("Dataset is not private; refusing deployment.")
    if "state.json" not in api.list_repo_files(DATASET, repo_type="dataset"):
        payload = json.dumps(
            {"version": 1, "threads": [], "missions": [], "memories": []},
            ensure_ascii=False,
        ).encode()
        api.create_commit(
            repo_id=DATASET,
            repo_type="dataset",
            commit_message="Initialize empty private Gaïrus state",
            operations=[CommitOperationAdd(path_in_repo="state.json", path_or_fileobj=payload)],
        )
        print("Initialized previously empty private state repository.")
    if args.key_file:
        key = args.key_file.read_text().strip()
        if len(key) < 40 or args.key_file.stat().st_mode & 0o077:
            raise SystemExit("Unsafe service-key file.")
        key_path = args.key_file
    else:
        key = secrets.token_urlsafe(48)
        fd, name = tempfile.mkstemp(prefix="gairus-cloud-key-")
        with os.fdopen(fd, "w") as stream:
            stream.write(key)
        key_path = Path(name)
    api.add_space_secret(SPACE, key="GAIRUS_SERVICE_KEY", value=key)
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    api.add_space_variable(SPACE, key="GAIRUS_BUILD_REVISION", value=revision)
    result = api.create_commit(
        repo_id=SPACE,
        repo_type="space",
        commit_message=f"Deploy zero-budget Gaïrus adapter from {revision[:12]}",
        operations=[
            CommitOperationAdd(path_in_repo=name, path_or_fileobj=SOURCE / name)
            for name in FILES
        ],
    )
    print("Space commit:", result.oid)
    print("Space:", f"https://huggingface.co/spaces/{SPACE}")
    print("Private service-key file:", key_path)
    print("Service-key fingerprint:", hashlib.sha256(key.encode()).hexdigest()[:12])
    print("No paid hardware, storage, subscription, credit or DNS change requested.")


if __name__ == "__main__":
    main()
