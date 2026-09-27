cd ~/gairus

echo "===== ORCHESTRATOR ====="
sed -n '1,260p' core/orchestrator.py

echo
echo "===== MISSION ENGINE ====="
sed -n '1,260p' core/mission_engine.py

echo
echo "===== MISSION ORCHESTRATOR ====="
sed -n '1,260p' core/mission_orchestrator.py

echo
echo "===== PLANNER ====="
sed -n '1,260p' core/planner.py
echo "===== EXECUTOR ====="
sed -n '1,260p' core/executor.py

echo
echo "===== VERIFIER ====="
sed -n '1,260p' core/verifier.py

echo
echo "===== AGENT RUNTIME ====="
sed -n '1,260p' core/agent_runtime.py

echo
echo "===== TOOL RUNTIME ====="
sed -n '1,260p' core/tool_runtime.py
echo "===== FINAL WIRING ====="
sed -n '1,320p' core/final_wiring.py

echo
echo "===== FULL BOOTSTRAP ====="
sed -n '1,320p' core/full_bootstrap.py

echo
echo "===== GAIRUS OPERATIONS ====="
sed -n '1,320p' core/gairus_operations.py

cd ~/gairus || exit 1

mkdir -p core data logs

if [ -f core/autonomous_runtime.py ]; then
    cp core/autonomous_runtime.py "core/autonomous_runtime.py.before_autonomous_$(date +%Y%m%d_%H%M%S)"
fi

cat > core/autonomous_runtime.py <<'PY'
from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import sqlite3
import subprocess
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

try:
    import requests
except Exception:
    requests = None


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "autonomous_runtime.db"
AUDIT_PATH = DATA_DIR / "autonomous_audit.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def safe_json(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def on(self, event: str, callback: Callable):
        with self._lock:
            self._listeners.setdefault(event, []).append(callback)

    def emit(self, event: str, payload: Any = None):
        with self._lock:
            listeners = list(self._listeners.get(event, []))
            listeners += list(self._listeners.get("*", []))

        for callback in listeners:
            try:
                callback(payload)
            except Exception:
                pass


class PersistentMemory:
    def __init__(self, path: Path = DB_PATH):
        self.path = Path(path)
        self.lock = threading.RLock()
        self._init()

    def _connect(self):
        con = sqlite3.connect(str(self.path), timeout=30)
        con.row_factory = sqlite3.Row
        return con

    def _init(self):
        with self.lock, self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_namespace_key
                ON memories(namespace, key)
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS missions (
                    id TEXT PRIMARY KEY,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            con.commit()

    def put(self, key: str, value: Any, namespace: str = "default"):
        timestamp = now_iso()
        encoded = json.dumps(value, ensure_ascii=False, default=str)

        with self.lock, self._connect() as con:
            con.execute("""
                INSERT INTO memories(id, namespace, key, value, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at
            """, (
                f"{namespace}:{key}",
                namespace,
                key,
                encoded,
                timestamp,
                timestamp,
            ))
            con.commit()

    def get(self, key: str, namespace: str = "default", default=None):
        with self.lock, self._connect() as con:
            row = con.execute("""
                SELECT value
                FROM memories
                WHERE namespace=? AND key=?
            """, (namespace, key)).fetchone()

        if not row:
            return default

        try:
            return json.loads(row["value"])
        except Exception:
            return row["value"]

    def search(self, query: str, namespace: Optional[str] = None, limit: int = 20):
        pattern = f"%{query}%"

        with self.lock, self._connect() as con:
            if namespace:
                rows = con.execute("""
                    SELECT namespace,key,value,updated_at
                    FROM memories
                    WHERE namespace=? AND
                          (key LIKE ? OR value LIKE ?)
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (namespace, pattern, pattern, limit)).fetchall()
            else:
                rows = con.execute("""
                    SELECT namespace,key,value,updated_at
                    FROM memories
                    WHERE key LIKE ? OR value LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (pattern, pattern, limit)).fetchall()

        result = []
        for row in rows:
            try:
                value = json.loads(row["value"])
            except Exception:
                value = row["value"]

            result.append({
                "namespace": row["namespace"],
                "key": row["key"],
                "value": value,
                "updated_at": row["updated_at"],
            })

        return result

    def save_mission(self, mission: "Mission"):
        with self.lock, self._connect() as con:
            con.execute("""
                INSERT INTO missions
                (id,objective,status,result,error,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    result=excluded.result,
                    error=excluded.error,
                    updated_at=excluded.updated_at
            """, (
                mission.id,
                mission.objective,
                mission.status,
                json.dumps(mission.result, ensure_ascii=False, default=str)
                if mission.result is not None else None,
                mission.error,
                mission.created_at,
                mission.updated_at,
            ))
            con.commit()


class AuditLog:
    def __init__(self, path: Path = AUDIT_PATH):
        self.path = Path(path)
        self.lock = threading.RLock()

    def write(self, event: str, **payload):
        record = {
            "timestamp": now_iso(),
            "event": event,
            "payload": safe_json(payload),
        }

        with self.lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(
                    record,
                    ensure_ascii=False,
                    default=str,
                ) + "\n")


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable
    category: str = "general"
    dangerous: bool = False


class ToolRegistry:
    def __init__(self, audit: AuditLog):
        self.audit = audit
        self.tools: Dict[str, Tool] = {}
        self.lock = threading.RLock()

    def register(
        self,
        name: str,
        description: str,
        handler: Callable,
        category: str = "general",
        dangerous: bool = False,
    ):
        with self.lock:
            self.tools[name] = Tool(
                name=name,
                description=description,
                handler=handler,
                category=category,
                dangerous=dangerous,
            )

        self.audit.write(
            "tool_registered",
            name=name,
            category=category,
            dangerous=dangerous,
        )

    def get(self, name: str) -> Optional[Tool]:
        with self.lock:
            return self.tools.get(name)

    def list(self):
        with self.lock:
            return [
                {
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                    "dangerous": t.dangerous,
                }
                for t in self.tools.values()
            ]

    def execute(self, name: str, **kwargs):
        tool = self.get(name)

        if not tool:
            raise KeyError(f"Outil inconnu: {name}")

        self.audit.write(
            "tool_start",
            name=name,
            arguments=kwargs,
        )

        started = time.time()

        try:
            result = tool.handler(**kwargs)

            self.audit.write(
                "tool_success",
                name=name,
                duration=time.time() - started,
            )

            return result

        except Exception as exc:
            self.audit.write(
                "tool_error",
                name=name,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            raise


class Governance:
    def __init__(self):
        self.autonomy = os.getenv(
            "GAIRUS_AUTONOMY",
            "true",
        ).lower() in {"1", "true", "yes", "on"}

        self.approvals = os.getenv(
            "GAIRUS_APPROVALS",
            "true",
        ).lower() in {"1", "true", "yes", "on"}

    def allowed(self, tool: Tool) -> bool:
        if not self.autonomy:
            return False

        return True


@dataclass
class Task:
    id: str
    description: str
    tool: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: str = "pending"
    attempts: int = 0
    max_attempts: int = 3
    result: Any = None
    error: Optional[str] = None


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


class Planner:
    """
    Planificateur générique.

    Il sait construire une mission simple à partir d'un objectif.
    Lorsqu'un LLM est disponible dans l'architecture Gaïrus existante,
    AutonomousRuntime tente de le détecter et de l'utiliser sans
    rendre ce moteur dépendant d'un fournisseur particulier.
    """

    def __init__(self, runtime: "AutonomousRuntime"):
        self.runtime = runtime

    def plan(self, objective: str) -> Mission:
        mission = Mission(
            id=new_id("mission"),
            objective=objective.strip(),
        )

        text = objective.strip()

        if not text:
            mission.error = "Objectif vide."
            mission.status = "failed"
            return mission

        mission.tasks.append(Task(
            id=new_id("task"),
            description=text,
        ))

        return mission


class Executor:
    def __init__(
        self,
        registry: ToolRegistry,
        governance: Governance,
        audit: AuditLog,
        workers: int = 4,
    ):
        self.registry = registry
        self.governance = governance
        self.audit = audit
        self.pool = ThreadPoolExecutor(max_workers=workers)

    def execute_task(self, task: Task):
        task.status = "running"

        if not task.tool:
            task.status = "completed"
            task.result = {
                "message": "Tâche créée mais aucun outil spécialisé n'a été associé.",
                "description": task.description,
            }
            return task.result

        tool = self.registry.get(task.tool)

        if not tool:
            raise KeyError(f"Outil introuvable: {task.tool}")

        if not self.governance.allowed(tool):
            raise PermissionError(
                f"Outil non autorisé dans la configuration actuelle: {task.tool}"
            )

        last_error = None

        for attempt in range(1, task.max_attempts + 1):
            task.attempts = attempt

            try:
                result = self.registry.execute(
                    task.tool,
                    **task.arguments,
                )

                task.result = result
                task.status = "completed"
                task.error = None

                return result

            except Exception as exc:
                last_error = exc
                task.error = str(exc)

                self.audit.write(
                    "task_retry",
                    task_id=task.id,
                    attempt=attempt,
                    error=str(exc),
                )

                if attempt < task.max_attempts:
                    time.sleep(min(attempt, 3))

        task.status = "failed"

        raise RuntimeError(
            f"Tâche échouée après {task.attempts} tentative(s): "
            f"{last_error}"
        )


class Verifier:
    def verify_task(self, task: Task) -> bool:
        if task.status != "completed":
            return False

        return task.error is None

    def verify_mission(self, mission: Mission) -> bool:
        if not mission.tasks:
            return False

        return all(self.verify_task(task) for task in mission.tasks)


class ExistingGaïrusBridge:
    """
    Découverte souple des composants déjà présents dans le dépôt.

    Le moteur ne remplace pas l'architecture existante.
    Il cherche les composants connus et les expose lorsqu'ils sont
    compatibles avec une interface simple.
    """

    MODULES = [
        "core.gairus",
        "core.orchestrator",
        "core.mission_engine",
        "core.mission_orchestrator",
        "core.agent_runtime",
        "core.tool_runtime",
        "core.autonomy",
        "autonomy",
        "gairus_engine",
        "router",
        "missions",
        "tools",
    ]

    def discover(self):
        discovered = {}

        import importlib

        for name in self.MODULES:
            try:
                module = importlib.import_module(name)
                discovered[name] = module
            except Exception as exc:
                discovered[name] = {
                    "error": str(exc),
                }

        return discovered

    def find_callable(self, names: Iterable[str]):
        import importlib

        for module_name in self.MODULES:
            try:
                module = importlib.import_module(module_name)
            except Exception:
                continue

            for name in names:
                candidate = getattr(module, name, None)

                if callable(candidate):
                    return candidate

        return None


class AutonomousRuntime:
    VERSION = "1.0.0"

    def __init__(self):
        self.started_at = now_iso()

        self.memory = PersistentMemory()
        self.audit = AuditLog()
        self.events = EventBus()
        self.governance = Governance()
        self.registry = ToolRegistry(self.audit)
        self.planner = Planner(self)
        self.executor = Executor(
            self.registry,
            self.governance,
            self.audit,
        )
        self.verifier = Verifier()
        self.bridge = ExistingGaïrusBridge()

        self.running = False
        self.lock = threading.RLock()

        self._register_builtin_tools()

        self.audit.write(
            "runtime_initialized",
            version=self.VERSION,
            autonomy=self.governance.autonomy,
            approvals=self.governance.approvals,
        )

    def _register_builtin_tools(self):
        self.registry.register(
            "system_info",
            "Informations sur l'environnement Gaïrus.",
            self.tool_system_info,
            category="system",
        )

        self.registry.register(
            "list_tools",
            "Liste les outils actuellement disponibles.",
            self.tool_list_tools,
            category="system",
        )

        self.registry.register(
            "memory_put",
            "Enregistre une donnée persistante.",
            self.tool_memory_put,
            category="memory",
        )

        self.registry.register(
            "memory_get",
            "Récupère une donnée persistante.",
            self.tool_memory_get,
            category="memory",
        )

        self.registry.register(
            "memory_search",
            "Recherche dans la mémoire persistante.",
            self.tool_memory_search,
            category="memory",
        )

        self.registry.register(
            "python_check",
            "Compile un fichier Python pour vérifier sa syntaxe.",
            self.tool_python_check,
            category="development",
        )

        self.registry.register(
            "shell",
            "Exécute une commande shell dans le répertoire du projet.",
            self.tool_shell,
            category="system",
            dangerous=True,
        )

        self.registry.register(
            "git_status",
            "Retourne l'état du dépôt Git.",
            self.tool_git_status,
            category="development",
        )

        self.registry.register(
            "git_log",
            "Retourne les derniers commits.",
            self.tool_git_log,
            category="development",
        )

        self.registry.register(
            "http_get",
            "Effectue une requête HTTP GET.",
            self.tool_http_get,
            category="network",
        )

        self.registry.register(
            "inspect_modules",
            "Inspecte les modules Gaïrus existants.",
            self.tool_inspect_modules,
            category="system",
        )

    def tool_system_info(self):
        return {
            "agent": os.getenv("GAIRUS_NAME", "Gaïrus"),
            "runtime": self.VERSION,
            "python": os.sys.version,
            "root": str(ROOT),
            "autonomy": self.governance.autonomy,
            "approvals": self.governance.approvals,
            "started_at": self.started_at,
        }

    def tool_list_tools(self):
        return self.registry.list()

    def tool_memory_put(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
    ):
        self.memory.put(
            key=key,
            value=value,
            namespace=namespace,
        )

        return {
            "ok": True,
            "namespace": namespace,
            "key": key,
        }

    def tool_memory_get(
        self,
        key: str,
        namespace: str = "default",
    ):
        return self.memory.get(
            key=key,
            namespace=namespace,
        )

    def tool_memory_search(
        self,
        query: str,
        namespace: Optional[str] = None,
        limit: int = 20,
    ):
        return self.memory.search(
            query=query,
            namespace=namespace,
            limit=limit,
        )

    def tool_python_check(self, path: str):
        target = (ROOT / path).resolve()

        if not str(target).startswith(str(ROOT.resolve())):
            raise ValueError("Chemin hors du projet.")

        process = subprocess.run(
            [
                os.sys.executable,
                "-m",
                "py_compile",
                str(target),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )

        return {
            "ok": process.returncode == 0,
            "path": str(target),
            "stdout": process.stdout,
            "stderr": process.stderr,
            "returncode": process.returncode,
        }

    def too
