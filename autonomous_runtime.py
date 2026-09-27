from __future__ import annotations

import json
import os
import shlex
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


# ============================================================
# GAÏRUS / ZYRVION
# Autonomous Runtime
# ============================================================

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_DB = DATA_DIR / "autonomous_memory.db"
AUDIT_FILE = DATA_DIR / "autonomous_audit.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_json(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


# ============================================================
# EVENT BUS
# ============================================================

class EventBus:
    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[..., Any]]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        with self._lock:
            self._handlers.setdefault(event, []).append(handler)

    def publish(self, event: str, **payload: Any) -> None:
        with self._lock:
            handlers = list(self._handlers.get(event, []))

        for handler in handlers:
            try:
                handler(**payload)
            except Exception:
                traceback.print_exc()


# ============================================================
# PERSISTENT MEMORY
# ============================================================

class PersistentMemory:
    def __init__(self, db_path: Path = MEMORY_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    id TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_namespace
                ON memory(namespace)
                """
            )
            conn.commit()

    def put(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
    ) -> Dict[str, Any]:
        memory_id = f"{namespace}:{key}"
        encoded = json.dumps(
            safe_json(value),
            ensure_ascii=False,
            default=str,
        )
        timestamp = now_iso()

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO memory
                        (id, namespace, key, value, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at
                    """,
                    (
                        memory_id,
                        namespace,
                        key,
                        encoded,
                        timestamp,
                        timestamp,
                    ),
                )
                conn.commit()

        return {
            "id": memory_id,
            "namespace": namespace,
            "key": key,
            "value": safe_json(value),
            "updated_at": timestamp,
        }

    def get(
        self,
        key: str,
        namespace: str = "default",
        default: Any = None,
    ) -> Any:
        memory_id = f"{namespace}:{key}"

        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT value FROM memory WHERE id = ?",
                    (memory_id,),
                ).fetchone()

        if row is None:
            return default

        try:
            return json.loads(row["value"])
        except Exception:
            return row["value"]

    def search(
        self,
        query: str,
        namespace: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        pattern = f"%{query}%"

        sql = """
            SELECT id, namespace, key, value, created_at, updated_at
            FROM memory
            WHERE (key LIKE ? OR value LIKE ?)
        """
        params: List[Any] = [pattern, pattern]

        if namespace:
            sql += " AND namespace = ?"
            params.append(namespace)

        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(int(limit))

        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(sql, params).fetchall()

        results = []

        for row in rows:
            try:
                value = json.loads(row["value"])
            except Exception:
                value = row["value"]

            results.append(
                {
                    "id": row["id"],
                    "namespace": row["namespace"],
                    "key": row["key"],
                    "value": value,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )

        return results


# ============================================================
# AUDIT LOG
# ============================================================

class AuditLog:
    def __init__(self, path: Path = AUDIT_FILE) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def write(
        self,
        event: str,
        status: str = "ok",
        **payload: Any,
    ) -> Dict[str, Any]:
        record = {
            "timestamp": now_iso(),
            "event": event,
            "status": status,
            "payload": safe_json(payload),
        }

        line = json.dumps(
            record,
            ensure_ascii=False,
            default=str,
        )

        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

        return record


# ============================================================
# TOOL REGISTRY
# ============================================================

@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    dangerous: bool = False


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}
        self._lock = threading.RLock()

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        dangerous: bool = False,
    ) -> Tool:
        tool = Tool(
            name=name,
            description=description,
            handler=handler,
            dangerous=dangerous,
        )

        with self._lock:
            self._tools[name] = tool

        return tool

    def get(self, name: str) -> Optional[Tool]:
        with self._lock:
            return self._tools.get(name)

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            tools = list(self._tools.values())

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "dangerous": tool.dangerous,
            }
            for tool in tools
        ]

    def execute(
        self,
        name: str,
        **kwargs: Any,
    ) -> Any:
        tool = self.get(name)

        if tool is None:
            raise ValueError(f"Outil inconnu: {name}")

        return tool.handler(**kwargs)


# ============================================================
# GOVERNANCE
# ============================================================

class Governance:
    def __init__(self) -> None:
        self.autonomy = (
            os.getenv("GAIRUS_AUTONOMY", "true").lower()
            in {"1", "true", "yes", "on"}
        )

        self.approvals = (
            os.getenv("GAIRUS_APPROVALS", "true").lower()
            in {"1", "true", "yes", "on"}
        )

    def allowed(
        self,
        tool: Tool,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        context = context or {}

        if not self.autonomy:
            return False

        if tool.dangerous and self.approvals:
            return bool(context.get("approved", False))

        return True


# ============================================================
# TASK / MISSION
# ============================================================

@dataclass
class Task:
    id: str
    description: str
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Mission:
    id: str
    objective: str
    status: str = "created"
    tasks: List[Task] = field(default_factory=list)
    result: Any = None
    error: Optional[str] = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


# ============================================================
# PLANNER
# ============================================================

class Planner:
    """
    Planificateur minimal mais extensible.

    Il peut être remplacé ou enrichi par le moteur de planification
    existant de Gaïrus / ZYRVION sans modifier l'API du runtime.
    """

    def __init__(self, runtime: "AutonomousRuntime") -> None:
        self.runtime = runtime

    def plan(self, objective: str) -> Mission:
        mission = Mission(
            id=str(uuid.uuid4()),
            objective=objective,
        )

        normalized = objective.strip()

        if not normalized:
            mission.error = "Objectif vide"
            mission.status = "failed"
            return mission

        lower = normalized.lower()

        if lower.startswith("shell:"):
            command = normalized.split(":", 1)[1].strip()

            mission.tasks.append(
                Task(
                    id=str(uuid.uuid4()),
                    description=f"Exécuter: {command}",
                    metadata={
                        "tool": "shell",
                        "args": {"command": command},
                    },
                )
            )
            return mission

        if lower.startswith("remember:"):
            content = normalized.split(":", 1)[1].strip()

            mission.tasks.append(
                Task(
                    id=str(uuid.uuid4()),
                    description="Mémoriser l'information",
                    metadata={
                        "tool": "memory_put",
                        "args": {
                            "key": f"note_{int(time.time())}",
                            "value": content,
                        },
                    },
                )
            )
            return mission

        if lower.startswith("http:") or lower.startswith("https:"):
            mission.tasks.append(
                Task(
                    id=str(uuid.uuid4()),
                    description=f"Lire {normalized}",
                    metadata={
                        "tool": "http_get",
                        "args": {"url": normalized},
                    },
                )
            )
            return mission

        mission.tasks.append(
            Task(
                id=str(uuid.uuid4()),
                description=normalized,
                metadata={
                    "tool": "system_info",
                    "args": {},
                },
            )
        )

        return mission


# ============================================================
# EXECUTOR
# ============================================================

class Executor:
    def __init__(self, runtime: "AutonomousRuntime") -> None:
        self.runtime = runtime

    def execute_task(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None,
    ) -> Task:
        context = context or {}

        task.status = "running"

        tool_name = task.metadata.get("tool")

        if not tool_name:
            task.status = "completed"
            task.result = {
                "message": task.description,
            }
            return task

        try:
            tool = self.runtime.tools.get(tool_name)

            if tool is None:
                raise ValueError(
                    f"Outil introuvable: {tool_name}"
                )

            if not self.runtime.governance.allowed(
                tool,
                context,
            ):
                raise PermissionError(
                    f"Action non autorisée: {tool_name}"
                )

            args = task.metadata.get("args", {})

            result = self.runtime.tools.execute(
                tool_name,
                **args,
            )

            task.result = safe_json(result)
            task.status = "completed"

            self.runtime.audit.write(
                "task_completed",
                task_id=task.id,
                tool=tool_name,
            )

        except Exception as exc:
            task.status = "failed"
            task.error = f"{type(exc).__name__}: {exc}"

            self.runtime.audit.write(
                "task_failed",
                status="error",
                task_id=task.id,
                tool=tool_name,
                error=task.error,
            )

        return task


# ============================================================
# VERIFIER
# ============================================================

class Verifier:
    def __init__(self, runtime: "AutonomousRuntime") -> None:
        self.runtime = runtime

    def verify_task(self, task: Task) -> bool:
        if task.status != "completed":
            return False

        return task.error is None

    def verify_mission(self, mission: Mission) -> bool:
        if mission.status != "completed":
            return False

        return all(
            self.verify_task(task)
            for task in mission.tasks
        )


# ============================================================
# BRIDGE TO EXISTING GAÏRUS
# ============================================================

class ExistingGaïrusBridge:
    """
    Pont souple vers les modules existants.

    Aucun module existant n'est remplacé.
    Le runtime tente de réutiliser les capacités déjà présentes.
    """

    def __init__(self) -> None:
        self.modules: Dict[str, Any] = {}

        candidates = [
            "gairus_engine",
            "autonomy",
            "missions",
            "router",
            "providers",
            "memory",
            "tools",
            "core.orchestrator",
            "core.executor",
            "core.planner",
            "core.verifier",
        ]

        for module_name in candidates:
            try:
                module = __import__(
                    module_name,
                    fromlist=["*"],
                )
                self.modules[module_name] = module
            except Exception:
                continue

    def status(self) -> Dict[str, Any]:
        return {
            "loaded_modules": sorted(
                self.modules.keys()
            ),
            "count": len(self.modules),
        }

    def call_existing(
        self,
        module_name: str,
        function_name: str,
        **kwargs: Any,
    ) -> Any:
        module = self.modules.get(module_name)

        if module is None:
            raise ValueError(
                f"Module non chargé: {module_name}"
            )

        function = getattr(
            module,
            function_name,
            None,
        )

        if not callable(function):
            raise ValueError(
                f"Fonction inexistante: "
                f"{module_name}.{function_name}"
            )

        return function(**kwargs)


# ============================================================
# AUTONOMOUS RUNTIME
# ============================================================

class AutonomousRuntime:
    def __init__(self) -> None:
        self.started_at = now_iso()

        self.events = EventBus()
        self.memory = PersistentMemory()
        self.audit = AuditLog()
        self.tools = ToolRegistry()
        self.governance = Governance()
        self.bridge = ExistingGaïrusBridge()

        self.planner = Planner(self)
        self.executor = Executor(self)
        self.verifier = Verifier(self)

        self._missions: Dict[str, Mission] = {}
        self._lock = threading.RLock()

        self._register_builtin_tools()

        self.audit.write(
            "runtime_started",
            autonomy=self.governance.autonomy,
            approvals=self.governance.approvals,
        )

    # --------------------------------------------------------
    # Built-in tools
    # --------------------------------------------------------

    def _register_builtin_tools(self) -> None:
        self.tools.register(
            "system_info",
            "Retourne l'état du runtime Gaïrus.",
            self.tool_system_info,
        )

        self.tools.register(
            "list_tools",
            "Liste les outils disponibles.",
            self.tool_list_tools,
        )

        self.tools.register(
            "memory_put",
            "Enregistre une information dans la mémoire persistante.",
            self.tool_memory_put,
        )

        self.tools.register(
            "memory_get",
            "Récupère une information depuis la mémoire.",
            self.tool_memory_get,
        )

        self.tools.register(
            "memory_search",
            "Recherche dans la mémoire persistante.",
            self.tool_memory_search,
        )

        self.tools.register(
            "python_check",
            "Vérifie syntaxiquement un fichier Python.",
            self.tool_python_check,
        )

        self.tools.register(
            "shell",
            "Exécute une commande shell dans le projet Gaïrus.",
            self.tool_shell,
            dangerous=True,
        )

        self.tools.register(
            "git_status",
            "Retourne le statut Git du projet.",
            self.tool_git_status,
        )

        self.tools.register(
            "git_log",
            "Retourne l'historique Git récent.",
            self.tool_git_log,
        )

        self.tools.register(
            "http_get",
            "Récupère une ressource HTTP.",
            self.tool_http_get,
            dangerous=True,
        )

        self.tools.register(
            "inspect_modules",
            "Inspecte les modules existants de Gaïrus.",
            self.tool_inspect_modules,
        )

    def tool_system_info(self) -> Dict[str, Any]:
        return {
            "agent": os.getenv(
                "GAIRUS_NAME",
                "Gaïrus",
            ),
            "runtime": "AutonomousRuntime",
            "version": "1.0",
            "root": str(ROOT),
            "autonomy": self.governance.autonomy,
            "approvals": self.governance.approva
