from __future__ import annotations

import ast
import json
import os
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any


class GairusCognitiveEvolution:
    """
    Couche cognitive, identitaire, organisationnelle et d'évolution
    contrôlée de Gaïrus.

    Cette couche ne remplace ni le LLM, ni la mémoire existante,
    ni l'AutonomyEngine. Elle les complète.
    """

    def __init__(self, runtime=None, root=None):
        self.runtime = runtime
        self.root = Path(
            root or os.getenv(
                "GAIRUS_ROOT",
                Path(__file__).resolve().parent.parent,
            )
        ).resolve()

        self.data_dir = self.root / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.data_dir / "gairus_cognition.db"
        self.db = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
        )
        self.db.row_factory = sqlite3.Row

        self._init_db()

    def _init_db(self):
        cur = self.db.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS identities (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'identity',
                updated_at REAL NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS people (
                person_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT,
                department TEXT,
                manager_id TEXT,
                authority INTEGER DEFAULT 0,
                permissions TEXT DEFAULT '[]',
                skills TEXT DEFAULT '[]',
                channels TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                updated_at REAL NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cognitive_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at REAL NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS evolution_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                files TEXT DEFAULT '[]',
                status TEXT DEFAULT 'proposed',
                tests TEXT DEFAULT '[]',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        self.db.commit()

    # ---------------------------------------------------------
    # IDENTITÉ
    # ---------------------------------------------------------

    def set_identity(self, key: str, value: Any, category="identity"):
        now = time.time()
        self.db.execute(
            """
            INSERT INTO identities(key,value,category,updated_at)
            VALUES(?,?,?,?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                category=excluded.category,
                updated_at=excluded.updated_at
            """,
            (
                key,
                json.dumps(value, ensure_ascii=False),
                category,
                now,
            ),
        )
        self.db.commit()

        self._event(
            "identity.updated",
            {"key": key, "category": category},
        )

        return True

    def get_identity(self, key: str, default=None):
        row = self.db.execute(
            "SELECT value FROM identities WHERE key=?",
            (key,),
        ).fetchone()

        if not row:
            return default

        try:
            return json.loads(row["value"])
        except Exception:
            return row["value"]

    def identity(self):
        rows = self.db.execute(
            """
            SELECT key,value,category
            FROM identities
            ORDER BY key
            """
        ).fetchall()

        result = {}

        for row in rows:
            try:
                value = json.loads(row["value"])
            except Exception:
                value = row["value"]

            result[row["key"]] = {
                "value": value,
                "category": row["category"],
            }

        return result

    # ---------------------------------------------------------
    # PERSONNES / HIÉRARCHIE
    # ---------------------------------------------------------

    def register_person(
        self,
        person_id: str,
        name: str,
        role: str = "",
        department: str = "",
        manager_id: str | None = None,
        authority: int = 0,
        permissions=None,
        skills=None,
        channels=None,
        metadata=None,
    ):
        now = time.time()

        self.db.execute(
            """
            INSERT INTO people(
                person_id,name,role,department,manager_id,
                authority,permissions,skills,channels,metadata,
                updated_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(person_id) DO UPDATE SET
                name=excluded.name,
                role=excluded.role,
                department=excluded.department,
                manager_id=excluded.manager_id,
                authority=excluded.authority,
                permissions=excluded.permissions,
                skills=excluded.skills,
                channels=excluded.channels,
                metadata=excluded.metadata,
                updated_at=excluded.updated_at
            """,
            (
                person_id,
                name,
                role,
                department,
                manager_id,
                authority,
                json.dumps(permissions or [], ensure_ascii=False),
                json.dumps(skills or [], ensure_ascii=False),
                json.dumps(channels or [], ensure_ascii=False),
                json.dumps(metadata or {}, ensure_ascii=False),
                now,
            ),
        )

        self.db.commit()

        self._event(
            "organization.person_registered",
            {
                "person_id": person_id,
                "name": name,
                "role": role,
                "manager_id": manager_id,
            },
        )

        return self.get_person(person_id)

    def get_person(self, person_id: str):
        row = self.db.execute(
            "SELECT * FROM people WHERE person_id=?",
            (person_id,),
        ).fetchone()

        if not row:
            return None

        return self._person_dict(row)

    def _person_dict(self, row):
        result = dict(row)

        for key in (
            "permissions",
            "skills",
            "channels",
            "metadata",
        ):
            try:
                result[key] = json.loads(result[key])
            except Exception:
                pass

        return result

    def organization(self):
        rows = self.db.execute(
            "SELECT * FROM people ORDER BY authority DESC,name"
        ).fetchall()

        return [self._person_dict(row) for row in rows]

    def hierarchy_chain(self, person_id: str):
        chain = []
        current = self.get_person(person_id)
        seen = set()

        while current and current["person_id"] not in seen:
            seen.add(current["person_id"])
            chain.append(current)
            manager_id = current.get("manager_id")
            if not manager_id:
                break
            current = self.get_person(manager_id)

        return chain

    def can_act(self, person_id: str, action: str):
        person = self.get_person(person_id)

        if not person:
            return {
                "allowed": False,
                "reason": "unknown_person",
            }

        permissions = person.get("permissions", [])

        if "*" in permissions or action in permissions:
            return {
                "allowed": True,
                "reason": "explicit_permission",
            }

        return {
            "allowed": False,
            "reason": "permission_required",
        }

    # ---------------------------------------------------------
    # COGNITION
    # ---------------------------------------------------------

    def perceive(
        self,
        source=None,
        actor_id=None,
        message="",
        context=None,
    ):
        actor = self.get_person(actor_id) if actor_id else None

        return {
            "source": source,
            "actor": actor,
            "message": message,
            "context": context or {},
            "identity": self.identity(),
            "hierarchy": (
                self.hierarchy_chain(actor_id)
                if actor_id
                else []
            ),
            "timestamp": time.time(),
        }

    def reason(
        self,
        objective: str,
        actor_id: str | None = None,
        context=None,
    ):
        perception = self.perceive(
            actor_id=actor_id,
            message=objective,
            context=context,
        )

        actor = perception["actor"]

        return {
            "objective": objective,
            "actor": actor,
            "authority": (
                actor.get("authority", 0)
                if actor
                else None
            ),
            "hierarchy": perception["hierarchy"],
            "known_identity": bool(actor),
            "needs_llm_reasoning": True,
            "recommended_next_step": (
                "evaluate_permissions_and_plan"
            ),
        }

    # ---------------------------------------------------------
    # CONNAISSANCE DE SON PROPRE CODE
    # ---------------------------------------------------------

    def repository_status(self):
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=20,
            )

            return {
                "ok": result.returncode == 0,
                "root": str(self.root),
                "status": result.stdout.splitlines(),
                "error": result.stderr.strip(),
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
            }

    def repository_head(self):
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=20,
            )

            return result.stdout.strip()

        except Exception:
            return None

    def inspect_file(self, relative_path: str):
        path = (self.root / relative_path).resolve()

        if not str(path).startswith(str(self.root)):
            raise ValueError("path outside repository")

        if not path.exists():
            return {
                "ok": False,
                "error": "file_not_found",
            }

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        result = {
            "ok": True,
            "path": str(path.relative_to(self.root)),
            "size": len(text),
            "lines": len(text.splitlines()),
            "python": path.suffix == ".py",
        }

        if path.suffix == ".py":
            try:
                tree = ast.parse(text)
                result["syntax"] = "ok"
                result["classes"] = [
                    node.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ClassDef)
                ]
                result["functions"] = [
                    node.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef)
                ]
            except SyntaxError as exc:
                result["syntax"] = "error"
                result["syntax_error"] = str(exc)

        return result

    def inspect_repository(self, limit=200):
        files = []

        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            if any(
                part in {
                    ".git",
                    "__pycache__",
                    ".venv",
                    "node_modules",
                }
                for part in path.parts
            ):
                continue

            try:
                relative = path.relative_to(self.root)
            except ValueError:
                continue

            files.append(str(relative))

            if len(files) >= limit:
                break

        return {
            "ok": True,
            "root": str(self.root),
            "files": files,
            "count": len(files),
            "git_head": self.repository_head(),
        }

    # ---------------------------------------------------------
    # ÉVOLUTION CONTRÔLÉE
    # ---------------------------------------------------------

    def propose_evolution(
        self,
        title: str,
        description: str,
        files=None,
    ):
        now = time.time()

        cur = self.db.execute(
            """
            INSERT INTO evolution_proposals(
                title,description,files,status,
                created_at,updated_at
            )
            VALUES(?,?,?,?,?,?)
            """,
            (
                title,
                description,
                json.dumps(files or [], ensure_ascii=False),
                "proposed",
                now,
                now,
            ),
        )

        self.db.commit()

        proposal_id = cur.lastrowid

        self._event(
            "evolution.proposed",
            {
                "proposal_id": proposal_id,
                "title": title,
            },
        )

        return self.get_evolution(proposal_id)

    def get_evolution(self, proposal_id: int):
        row = self.db.execute(
            """
            SELECT * FROM evolution_proposals
            WHERE id=?
            """,
            (proposal_id,),
        ).fetchone()

        if not row:
            return None

        result = dict(row)

        try:
            result["files"] = json.loads(result["files"])
        except Exception:
            pass

        try:
            result["tests"] = json.loads(result["tests"])
        except Exception:
            pass

        return result

    def run_tests(self):
        """
        Vérification minimale avant toute évolution.
        """
        commands = [
            [
                "python",
                "-m",
                "py_compile",
                "autonomy.py",
            ],
            [
                "python",
                "-m",
                "py_compile",
                "core/autonomous_integration.py",
            ],
            [
                "python",
                "-m",
                "py_compile",
                "core/autonomous_runtime_bridge.py",
            ],
            [
                "python",
                "-m",
                "py_compile",
                "core/autonomous_support.py",
            ],
        ]

        results = []

        for command in commands:
            try:
                result = subprocess.run(
                    command,
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                results.append({
                    "command": " ".join(command),
                    "ok": result.returncode == 0,
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                })

            except Exception as exc:
                results.append({
                    "command": " ".join(command),
                    "ok": False,
                    "error": str(exc),
                })

        return {
            "ok": all(item["ok"] for item in results),
            "tests": results,
        }

    def status(self):
        return {
            "status": "ok",
            "type": "gairus_cognitive_evolution",
            "identity_entries": self.db.execute(
                "SELECT COUNT(*) FROM identities"
            ).fetchone()[0],
            "people": self.db.execute(
                "SELECT COUNT(*) FROM people"
            ).fetchone()[0],
            "evolution_proposals": self.db.execute(
                "SELECT COUNT(*) FROM evolution_proposals"
            ).fetchone()[0],
            "repository": self.repository_status(),
            "git_head": self.repository_head(),
        }

    # ---------------------------------------------------------
    # ÉVÉNEMENTS
    # ---------------------------------------------------------

    def _event(self, event_type, payload):
        self.db.execute(
            """
            INSERT INTO cognitive_events(
                event_type,payload,created_at
            )
            VALUES(?,?,?)
            """,
            (
                event_type,
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    default=str,
                ),
                time.time(),
            ),
        )
        self.db.commit()


_instance = None


def get_cognitive_evolution(runtime=None):
    global _instance

    if _instance is None:
        _instance = GairusCognitiveEvolution(runtime)

    return _instance
