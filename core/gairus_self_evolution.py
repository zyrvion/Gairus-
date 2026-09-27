from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional


class GairusSelfEvolution:
    """
    Moteur d'évolution contrôlée de Gaïrus.

    Cycle :
        inspecter
        -> préparer
        -> modifier
        -> tester
        -> valider
        -> commit
        -> rollback si nécessaire

    Aucune modification destructive n'est effectuée sans
    passage explicite par apply_change().
    """

    def __init__(self, runtime: Any = None, repository: Optional[str] = None):
        self.runtime = runtime
        self.root = Path(
            repository
            or os.getenv("GAIRUS_REPOSITORY")
            or Path(__file__).resolve().parents[1]
        ).resolve()

        self.state_dir = self.root / "data" / "evolution"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.state_dir / "state.json"

        self._state = self._load_state()

    # ---------------------------------------------------------
    # UTILITAIRES
    # ---------------------------------------------------------

    def _load_state(self) -> Dict[str, Any]:
        if not self.state_file.exists():
            return {
                "status": "idle",
                "last_operation": None,
                "last_commit": None,
                "last_error": None,
                "history": [],
            }

        try:
            return json.loads(
                self.state_file.read_text(encoding="utf-8")
            )
        except Exception:
            return {
                "status": "idle",
                "last_operation": None,
                "last_commit": None,
                "last_error": None,
                "history": [],
            }

    def _save_state(self) -> None:
        self.state_file.write_text(
            json.dumps(
                self._state,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _record(
        self,
        operation: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = {
            "timestamp": time.time(),
            "operation": operation,
            "status": status,
            "details": details or {},
        }

        self._state["status"] = status
        self._state["last_operation"] = operation
        self._state["last_error"] = (
            details.get("error")
            if details
            else None
        )

        self._state.setdefault("history", []).append(event)

        if len(self._state["history"]) > 100:
            self._state["history"] = self._state["history"][-100:]

        self._save_state()

    def _git(self, *args: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=120,
            )

            return {
                "ok": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }

        except Exception as exc:
            return {
                "ok": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(exc),
            }

    # ---------------------------------------------------------
    # INSPECTION
    # ---------------------------------------------------------

    def inspect(self) -> Dict[str, Any]:
        status = self._git("status", "--short")
        branch = self._git(
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        )
        head = self._git(
            "rev-parse",
            "HEAD",
        )

        return {
            "status": "ok",
            "repository": str(self.root),
            "branch": branch.get("stdout"),
            "head": head.get("stdout"),
            "changes": status.get("stdout", "").splitlines(),
        }

    def inspect_file(self, relative_path: str) -> Dict[str, Any]:
        path = self._safe_path(relative_path)

        if not path.exists():
            return {
                "ok": False,
                "error": "file_not_found",
                "path": relative_path,
            }

        if not path.is_file():
            return {
                "ok": False,
                "error": "not_a_file",
                "path": relative_path,
            }

        content = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        return {
            "ok": True,
            "path": relative_path,
            "size": len(content),
            "lines": len(content.splitlines()),
            "content": content,
        }

    def _safe_path(self, relative_path: str) -> Path:
        path = (
            self.root / relative_path
        ).resolve()

        if path != self.root and self.root not in path.parents:
            raise ValueError(
                "path_outside_repository"
            )

        return path

    # ---------------------------------------------------------
    # BRANCHE D'EVOLUTION
    # ---------------------------------------------------------

    def create_branch(
        self,
        name: str,
    ) -> Dict[str, Any]:
        if not name:
            raise ValueError("branch_name_required")

        clean = (
            name.strip()
            .replace(" ", "-")
            .replace("/", "-")
        )

        if not clean.startswith("gairus-evolution-"):
            clean = (
                "gairus-evolution-"
                + clean
            )

        result = self._git(
            "switch",
            "-c",
            clean,
        )

        if not result["ok"]:
            self._record(
                "create_branch",
                "error",
                {
                    "error": result["stderr"],
                    "branch": clean,
                },
            )
            return {
                "ok": False,
                "error": result["stderr"],
                "branch": clean,
            }

        self._record(
            "create_branch",
            "ok",
            {
                "branch": clean,
            },
        )

        return {
            "ok": True,
            "branch": clean,
        }

    # ---------------------------------------------------------
    # PROPOSITION
    # ---------------------------------------------------------

    def propose(
        self,
        title: str,
        reason: str,
        files: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        proposal = {
            "id": f"evolution-{int(time.time() * 1000)}",
            "title": title,
            "reason": reason,
            "files": files or [],
            "status": "proposed",
            "created_at": time.time(),
        }

        proposals_file = (
            self.state_dir
            / "proposals.json"
        )

        try:
            if proposals_file.exists():
                proposals = json.loads(
                    proposals_file.read_text(
                        encoding="utf-8"
                    )
                )
            else:
                proposals = []

            proposals.append(proposal)

            proposals_file.write_text(
                json.dumps(
                    proposals,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            self._record(
                "propose",
                "ok",
                proposal,
            )

            return proposal

        except Exception as exc:
            self._record(
                "propose",
                "error",
                {"error": str(exc)},
            )
            raise

    # ---------------------------------------------------------
    # MODIFICATION
    # ---------------------------------------------------------

    def apply_change(
        self,
        relative_path: str,
        content: str,
    ) -> Dict[str, Any]:
        """
        Applique une modification à un fichier du dépôt.

        Le fichier est sauvegardé avant modification.
        """

        path = self._safe_path(relative_path)

        backup_dir = (
            self.state_dir
            / "backups"
        )
        backup_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        backup = None

        try:
            if path.exists():
                backup = (
                    backup_dir
                    / (
                        path.name
                        + "."
                        + str(int(time.time()))
                        + ".bak"
                    )
                )

                backup.write_text(
                    path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    ),
                    encoding="utf-8",
                )

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            path.write_text(
                content,
                encoding="utf-8",
            )

            self._record(
                "apply_change",
                "changed",
                {
                    "file": relative_path,
                    "backup": (
                        str(backup)
                        if backup
                        else None
                    ),
                },
            )

            return {
                "ok": True,
                "file": relative_path,
                "backup": (
                    str(backup)
                    if backup
                    else None
                ),
            }

        except Exception as exc:
            self._record(
                "apply_change",
                "error",
                {
                    "file": relative_path,
                    "error": str(exc),
                },
            )
            return {
                "ok": False,
                "error": str(exc),
            }

    # ---------------------------------------------------------
    # TESTS
    # ---------------------------------------------------------

    def run_tests(
        self,
        targets: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        commands = targets or [
            "python -m compileall -q core",
        ]

        results = []

        for command in commands:
            try:
                result = subprocess.run(
                    command,
                    cwd=str(self.root),
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )

                item = {
                    "command": command,
                    "ok": result.returncode == 0,
                    "returncode": result.returncode,
                    "stdout": result.stdout[-4000:],
                    "stderr": result.stderr[-4000:],
                }

                results.append(item)

                if not item["ok"]:
                    self._record(
                        "run_tests",
                        "failed",
                        item,
                    )

                    return {
                        "ok": False,
                        "results": results,
                    }

            except Exception as exc:
                item = {
                    "command": command,
                    "ok": False,
                    "error": str(exc),
                }

                results.append(item)

                self._record(
                    "run_tests",
                    "failed",
                    item,
                )

                return {
                    "ok": False,
                    "results": results,
                }

        self._record(
            "run_tests",
            "passed",
            {
                "count": len(results),
            },
        )

        return {
            "ok": True,
            "results": results,
        }

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        tests = self.run_tests()

        if not tests["ok"]:
            return {
                "ok": False,
                "status": "tests_failed",
                "tests": tests,
            }

        status = self._git(
            "status",
            "--short",
        )

        return {
            "ok": True,
            "status": "validated",
            "tests": tests,
            "changes": status["stdout"].splitlines(),
        }

    # ---------------------------------------------------------
    # COMMIT
    # ---------------------------------------------------------

    def commit(
        self,
        message: str,
    ) -> Dict[str, Any]:
        if not message.strip():
            raise ValueError(
                "commit_message_required"
            )

        validation = self.validate()

        if not validation["ok"]:
            return {
                "ok": False,
                "status": "not_committed",
                "validation": validation,
            }

        add = self._git(
            "add",
            "-A",
        )

        if not add["ok"]:
            return {
                "ok": False,
                "error": add["stderr"],
            }

        commit = self._git(
            "commit",
            "-m",
            message,
        )

        if not commit["ok"]:
            self._record(
                "commit",
                "error",
                {
                    "error": commit["stderr"],
                },
            )

            return {
                "ok": False,
                "error": commit["stderr"],
            }

        head = self._git(
            "rev-parse",
            "HEAD",
        )

        self._state["last_commit"] = (
            head["stdout"]
        )

        self._record(
            "commit",
            "ok",
            {
                "commit": head["stdout"],
                "message": message,
            },
        )

        return {
            "ok": True,
            "commit": head["stdout"],
            "message": message,
        }

    # ---------------------------------------------------------
    # ROLLBACK
    # ---------------------------------------------------------

    def rollback(self) -> Dict[str, Any]:
        result = self._git(
            "reset",
            "--hard",
            "HEAD",
        )

        if not result["ok"]:
            self._record(
                "rollback",
                "error",
                {
                    "error": result["stderr"],
                },
            )

            return {
                "ok": False,
                "error": result["stderr"],
            }

        self._record(
            "rollback",
            "ok",
        )

        return {
            "ok": True,
            "status": "rolled_back",
        }

    # ---------------------------------------------------------
    # PIPELINE
    # ---------------------------------------------------------

    def evolve(
        self,
        title: str,
        reason: str,
        relative_path: str,
        content: str,
        branch: Optional[str] = None,
        commit_message: Optional[str] = None,
    ) -> Dict[str, Any]:

        proposal = self.propose(
            title=title,
            reason=reason,
            files=[relative_path],
        )

        if branch:
            branch_result = self.create_branch(
                branch
            )

            if not branch_result["ok"]:
                return {
                    "ok": False,
                    "proposal": proposal,
                    "stage": "branch",
                    "result": branch_result,
                }
        else:
            branch_result = {
                "ok": True,
                "skipped": True,
            }

        change = self.apply_change(
            relative_path,
            content,
        )

        if not change["ok"]:
            return {
                "ok": False,
                "proposal": proposal,
                "stage": "change",
                "result": change,
            }

        validation = self.validate()

        if not validation["ok"]:
            rollback = self.rollback()

            return {
                "ok": False,
                "proposal": proposal,
                "stage": "validation",
                "validation": validation,
                "rollback": rollback,
            }

        commit_result = None

        if commit_message:
            commit_result = self.commit(
                commit_message
            )

        return {
            "ok": True,
            "status": "evolution_validated",
            "proposal": proposal,
            "branch": branch_result,
            "change": change,
            "validation": validation,
            "commit": commit_result,
        }

    # ---------------------------------------------------------
    # STATUT
    # ---------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        repository = self.inspect()

        return {
            "status": "ok",
            "type": "gairus_self_evolution",
            "repository": repository,
            "state": self._state,
        }


_instance = None


def get_self_evolution(runtime: Any = None):
    global _instance

    if _instance is None:
        _instance = GairusSelfEvolution(
            runtime=runtime
        )

    elif runtime is not None:
        _instance.runtime = runtime

    return _instance
