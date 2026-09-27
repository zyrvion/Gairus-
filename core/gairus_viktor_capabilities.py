from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


# ============================================================
# GAÏRUS VIKTOR-CLASS CAPABILITIES
# ============================================================

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA / "gairus_viktor_capabilities.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Task:
    id: str
    title: str
    description: str
    status: str = "pending"
    priority: str = "normal"
    created_at: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    result: Any = None
    error: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = utc_now()


class PersistentCompanyMemory:
    """
    Mémoire persistante d'entreprise.

    Stocke :
    - personnes
    - préférences
    - processus
    - outils
    - décisions
    - contexte Slack
    - tâches
    - connaissances
    """

    def __init__(self, path: Path = DB_PATH):
        self.path = str(path)
        self.lock = threading.RLock()
        self._init()

    def _connect(self):
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self):
        with self.lock:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        namespace TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        category TEXT,
                        source TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(namespace, key)
                    );

                    CREATE TABLE IF NOT EXISTS people (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        external_id TEXT UNIQUE,
                        name TEXT NOT NULL,
                        role TEXT,
                        department TEXT,
                        manager_id TEXT,
                        email TEXT,
                        metadata TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT,
                        status TEXT,
                        priority TEXT,
                        payload TEXT,
                        result TEXT,
                        created_at TEXT,
                        started_at TEXT,
                        finished_at TEXT,
                        error TEXT
                    );

                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        actor TEXT,
                        channel TEXT,
                        payload TEXT,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_memory_namespace
                    ON memory(namespace);

                    CREATE INDEX IF NOT EXISTS idx_events_type
                    ON events(event_type);

                    CREATE INDEX IF NOT EXISTS idx_tasks_status
                    ON tasks(status);
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def remember(
        self,
        key: str,
        value: Any,
        *,
        namespace: str = "gairus",
        category: str = "general",
        source: str = "gairus",
    ):
        now = utc_now()

        with self.lock:
            conn = self._connect()
            try:
                encoded = json.dumps(
                    value,
                    ensure_ascii=False,
                    default=str,
                )

                conn.execute(
                    """
                    INSERT INTO memory
                    (namespace, key, value, category, source,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(namespace, key)
                    DO UPDATE SET
                        value=excluded.value,
                        category=excluded.category,
                        source=excluded.source,
                        updated_at=excluded.updated_at
                    """,
                    (
                        namespace,
                        key,
                        encoded,
                        category,
                        source,
                        now,
                        now,
                    ),
                )

                conn.commit()
            finally:
                conn.close()

    def recall(
        self,
        key: str,
        *,
        namespace: str = "gairus",
        default=None,
    ):
        with self.lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    """
                    SELECT value
                    FROM memory
                    WHERE namespace = ?
                    AND key = ?
                    """,
                    (namespace, key),
                ).fetchone()

                if row is None:
                    return default

                try:
                    return json.loads(row["value"])
                except Exception:
                    return row["value"]
            finally:
                conn.close()

    def search(self, query: str, limit: int = 50):
        query = f"%{query.lower()}%"

        with self.lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM memory
                    WHERE lower(key) LIKE ?
                       OR lower(value) LIKE ?
                       OR lower(category) LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (
                        query,
                        query,
                        query,
                        limit,
                    ),
                ).fetchall()

                result = []

                for row in rows:
                    item = dict(row)

                    try:
                        item["value"] = json.loads(item["value"])
                    except Exception:
                        pass

                    result.append(item)

                return result
            finally:
                conn.close()

    def register_person(
        self,
        external_id: str,
        name: str,
        *,
        role: Optional[str] = None,
        department: Optional[str] = None,
        manager_id: Optional[str] = None,
        email: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        now = utc_now()

        with self.lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO people
                    (
                        external_id,
                        name,
                        role,
                        department,
                        manager_id,
                        email,
                        metadata,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(external_id)
                    DO UPDATE SET
                        name=excluded.name,
                        role=excluded.role,
                        department=excluded.department,
                        manager_id=excluded.manager_id,
                        email=excluded.email,
                        metadata=excluded.metadata,
                        updated_at=excluded.updated_at
                    """,
                    (
                        external_id,
                        name,
                        role,
                        department,
                        manager_id,
                        email,
                        json.dumps(
                            metadata or {},
                            ensure_ascii=False,
                        ),
                        now,
                        now,
                    ),
                )

                conn.commit()
            finally:
                conn.close()

    def get_person(self, external_id: str):
        with self.lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    """
                    SELECT *
                    FROM people
                    WHERE external_id = ?
                    """,
                    (external_id,),
                ).fetchone()

                if row is None:
                    return None

                result = dict(row)

                try:
                    result["metadata"] = json.loads(
                        result["metadata"] or "{}"
                    )
                except Exception:
                    result["metadata"] = {}

                return result
            finally:
                conn.close()

    def people(self):
        with self.lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM people
                    ORDER BY name
                    """
                ).fetchall()

                return [dict(row) for row in rows]
            finally:
                conn.close()

    def event(
        self,
        event_type: str,
        *,
        actor: Optional[str] = None,
        channel: Optional[str] = None,
        payload: Optional[dict] = None,
    ):
        with self.lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO events
                    (
                        event_type,
                        actor,
                        channel,
                        payload,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event_type,
                        actor,
                        channel,
                        json.dumps(
                            payload or {},
                            ensure_ascii=False,
                            default=str,
                        ),
                        utc_now(),
                    ),
                )

                conn.commit()
            finally:
                conn.close()

    def create_task(
        self,
        title: str,
        description: str,
        *,
        priority: str = "normal",
        payload: Optional[dict] = None,
    ) -> Task:
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            priority=priority,
        )

        with self.lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO tasks
                    (
                        id,
                        title,
                        description,
                        status,
                        priority,
                        payload,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.id,
                        task.title,
                        task.description,
                        task.status,
                        task.priority,
                        json.dumps(
                            payload or {},
                            ensure_ascii=False,
                            default=str,
                        ),
                        task.created_at,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        return task


class CloudExecutionSandbox:
    """
    Environnement d'exécution local/cloud de Gaïrus.

    Peut :
    - créer des fichiers
    - lire/écrire du code
    - lancer des tests
    - exécuter des commandes autorisées
    - inspecter le dépôt
    - construire des livrables
    """

    def __init__(self, root: Path = ROOT):
        self.root = root.resolve()
        self.allowed_commands = {
            "python",
            "python3",
            "pip",
            "git",
            "pytest",
            "ruff",
            "npm",
            "node",
            "bash",
        }

    def safe_path(self, path: str | Path) -> Path:
        candidate = (self.root / Path(path)).resolve()

        if candidate != self.root and self.root not in candidate.parents:
            raise PermissionError(
                "Chemin hors du workspace Gaïrus"
            )

        return candidate

    def read(self, path: str):
        return self.safe_path(path).read_text(
            encoding="utf-8"
        )

    def write(self, path: str, content: str):
        target = self.safe_path(path)
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        target.write_text(
            content,
            encoding="utf-8",
        )
        return str(target)

    def execute(
        self,
        command: list[str],
        *,
        timeout: int = 120,
        cwd: Optional[str] = None,
    ):
        if not command:
            raise ValueError("Commande vide")

        executable = Path(command[0]).name

        if executable not in self.allowed_commands:
            raise PermissionError(
                f"Commande non autorisée: {executable}"
            )

        workdir = (
            self.safe_path(cwd)
            if cwd
            else self.root
        )

        result = subprocess.run(
            command,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "ok": result.returncode == 0,
        }

    def inspect_repository(self):
        return {
            "root": str(self.root),
            "git": self.execute(
                ["git", "status", "--short"]
            ),
            "branch": self.execute(
                ["git", "branch", "--show-current"]
            ),
            "head": self.execute(
                ["git", "rev-parse", "HEAD"]
            ),
        }

    def run_tests(self):
        return self.execute(
            [
                "python",
                "-m",
                "compileall",
                "-q",
                ".",
            ],
            timeout=300,
        )


class ToolRegistry:
    """
    Registre unifié de connecteurs.

    Les vrais connecteurs OAuth/API peuvent être ajoutés
    sans modifier le cerveau de Gaïrus.
    """

    def __init__(self):
        self.tools: dict[str, Callable] = {}
        self.metadata: dict[str, dict] = {}
        self.lock = threading.RLock()

    def register(
        self,
        name: str,
        handler: Callable,
        *,
        description: str = "",
        category: str = "general",
        requires_approval: bool = False,
    ):
        with self.lock:
            self.tools[name] = handler
            self.metadata[name] = {
                "name": name,
                "description": description,
                "category": category,
                "requires_approval": requires_approval,
            }

    def available(self):
        with self.lock:
            return dict(self.metadata)

    def execute(
        self,
        name: str,
        payload: Optional[dict] = None,
    ):
        with self.lock:
            handler = self.tools.get(name)

        if handler is None:
            raise KeyError(
                f"Outil inconnu: {name}"
            )

        return handler(
            payload or {}
        )


class ProactiveTaskEngine:
    """
    Moteur de tâches proactives.

    Gaïrus peut détecter un besoin dans un événement
    et transformer ce besoin en mission.
    """

    def __init__(
        self,
        memory: PersistentCompanyMemory,
        sandbox: CloudExecutionSandbox,
    ):
        self.memory = memory
        self.sandbox = sandbox
        self.lock = threading.RLock()

    def create_from_signal(
        self,
        signal: dict,
    ):
        title = signal.get(
            "title",
            "Mission proactive Gaïrus",
        )

        description = signal.get(
            "description",
            "",
        )

        priority = signal.get(
            "priority",
            "normal",
        )

        task = self.memory.create_task(
            title,
            description,
            priority=priority,
            payload=signal,
        )

        self.memory.event(
            "proactive.task.created",
            actor="gairus",
            payload=asdict(task),
        )

        return task

    def execute(
        self,
        task: Task,
        executor: Callable[[Task], Any],
    ):
        task.status = "running"
        task.started_at = utc_now()

        try:
            result = executor(task)

            task.result = result
            task.status = "completed"

        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)

        task.finished_at = utc_now()

        self.memory.event(
            "task.finished",
            actor="gairus",
            payload=asdict(task),
        )

        return task


class ScheduledAutomationEngine:
    """
    Planification persistante.

    Compatible avec le scheduler existant de Gaïrus.
    """

    def __init__(self):
        self.jobs: dict[str, dict] = {}
        self.lock = threading.RLock()

    def register(
        self,
        name: str,
        callback: Callable,
        *,
        interval_seconds: int,
        enabled: bool = True,
    ):
        with self.lock:
            self.jobs[name] = {
                "name": name,
                "callback": callback,
                "interval_seconds": max(
                    5,
                    interval_seconds,
                ),
                "enabled": enabled,
                "created_at": utc_now(),
                "last_run": None,
            }

    def run_once(self, name: str):
        with self.lock:
            job = self.jobs.get(name)

        if not job:
            raise KeyError(name)

        if not job["enabled"]:
            return {
                "ok": False,
                "reason": "disabled",
            }

        result = job["callback"]()

        job["last_run"] = utc_now()

        return {
            "ok": True,
            "name": name,
            "result": result,
        }

    def status(self):
        with se
