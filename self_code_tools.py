from __future__ import annotations

import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent


def _safe_path(path: str) -> Path:
    target = (WORKSPACE / str(path).lstrip("/")).resolve()

    if WORKSPACE not in target.parents and target != WORKSPACE:
        raise ValueError("Chemin hors du workspace interdit.")

    return target


def read_code(path: str) -> str:
    target = _safe_path(path)

    if not target.exists():
        raise FileNotFoundError(path)

    if not target.is_file():
        raise ValueError("Le chemin n'est pas un fichier.")

    return target.read_text(encoding="utf-8")


def write_code(path: str, content: str) -> str:
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    target.write_text(str(content), encoding="utf-8")

    return f"Fichier modifié : {target.relative_to(WORKSPACE)}"


def run_python_test(path: str) -> str:
    target = _safe_path(path)

    result = subprocess.run(
        ["python", "-m", "py_compile", str(target)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "Échec de la compilation."
        )

    return f"TEST OK : {target.relative_to(WORKSPACE)}"


def git_diff() -> str:
    result = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=30,
    )

    return result.stdout.strip() or "Aucune modification."


def git_commit(message: str) -> str:
    subprocess.run(
        ["git", "add", "-A"],
        cwd=WORKSPACE,
        check=True,
        timeout=30,
    )

    result = subprocess.run(
        ["git", "commit", "-m", str(message)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        return result.stdout.strip() or result.stderr.strip()

    return result.stdout.strip()


def self_repair(path: str, attempts: int = 3) -> str:
    """
    Vérifie un fichier Python et retourne un diagnostic exploitable
    par Gaïrus pour effectuer une nouvelle correction.
    """
    target = _safe_path(path)

    if not target.exists():
        raise FileNotFoundError(path)

    errors = []

    for attempt in range(1, int(attempts) + 1):
        result = subprocess.run(
            ["python", "-m", "py_compile", str(target)],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return f"AUTO-REPAIR OK après {attempt} tentative(s)."

        error = (
            result.stderr.strip()
            or result.stdout.strip()
            or "Erreur Python inconnue."
        )

        errors.append(f"Tentative {attempt}: {error}")

    return "\n".join(errors)


REGISTRY = {
    "read_code": read_code,
    "write_code": write_code,
    "run_python_test": run_python_test,
    "git_diff": git_diff,
    "git_commit": git_commit,
    "self_repair": self_repair,
}
