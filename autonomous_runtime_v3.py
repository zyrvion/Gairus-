import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
import urllib.request

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

DB = DATA / "autonomous_runtime.db"
AUDIT = DATA / "autonomous_runtime.jsonl"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


class EventBus:
    def __init__(self):
        self.listeners: Dict[str, List[Callable]] = {}
        self.lock = threading.Lock()

    def on(self, event: str, callback: Callable):
        with self.lock:
            self.listeners.setdefault(event, []).append(callback)

    def emit(self, event: str, payload: Any = None):
        with self.lock:
            callbacks = list(self.listeners.get(event, []))

        for callback in callbacks:
            try:
                callback(payload)
            except Exception:
                pass


class Memory:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

        with sqlite3.connect(self.path) as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            db.commit()

    def put(self, key: str, value: Any):
        encoded = json.dumps(value, ensure_ascii=False, default=str)

        with self.lock:
            with sqlite3.connect(self.path) as db:
                db.execute(
                    "INSERT INTO memory(key,value,created_at) VALUES(?,?,?)",
                    (key, encoded, now()),
                )
                db.commit()

        return True

    def get(self, key: str):
        with self.lock:
            with sqlite3.connect(self.path) as db:
                row = db.execute(
                    """
                    SELECT value
                    FROM memory
                    WHERE key=?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (key,),
                ).fetchone()

        if not row:
            return None

        try:
            return json.loads(row[0])
        except Exception:
            return row[0]

    def search(self, query: str, limit: int = 20):
        query = f"%{query}%"

        with self.lock:
            with sqlite3.connect(self.path) as db:
                rows = db.execute(
                    """
                    SELECT key,value,created_at
                    FROM memory
                    WHERE key LIKE ? OR value LIKE ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (query, query, limit),
                ).fetchall()

        result = []

        for key, value, created_at in rows:
            try:
                value = json.loads(value)
            except Exception:
                pass

            result.append(
                {
                    "key": key,
                    "value": value,
                    "created_at": created_at,
                }
            )

        return result


class Audit:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

    def write(self, event: str, payload: Any = None):
        record = {
            "timestamp": now(),
            "event": event,
            "payload": payload,
        }

        with self.lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str))
                f.write("\n")


@dataclass
class Tool:
    name: str
    description: str
    dangerous: bool
    handler: Callable


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable,
        dangerous: bool = False,
    ):
        self.tools[name] = Tool(
            name=name,
            description=description,
            dangerous=dangerous,
            handler=handler,
        )

    def get(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def list(self):
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "dangerous": tool.dangerous,
            }
            for tool in self.tools.values()
        ]


class Governance:
    def __init__(self):
        self.autonomy = os.getenv("GAIRUS_AUTONOMY", "true").lower() == "true"
        self.approvals = os.getenv("GAIRUS_APPROVALS", "true").lower() == "true"

    def allowed(self, tool: Tool, context: Optional[Dict[str, Any]] = None):
        context = context or {}

        if not self.autonomy:
            return False, "Autonomie désactivée."

        if tool.dangerous and self.approvals:
            if context.get("approved") is not True:
                return False, "Approbation requise."

        return True, "allowed"


@dataclass
class Task:
    id: str
    action: str
    arguments: Dict[str, Any]
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None


@dataclass
class Mission:
    id: str
    objective: str
    tasks: List[Task]
    status: str = "planned"


class Bridge:
    """
    Pont léger vers les modules existants de Gaïrus.
    Aucun module existant n'est modifié ici.
    """

    def __init__(self):
        self.modules = {}

        module_names = [
            "gairus_engine",
            "autonomy",
            "missions",
            "memory",
            "tools",
            "router",
            "providers",
            "resilience",
            "zyrvion_bible",
        ]

        for name in module_names:
            try:
                self.modules[name] = __import__(name)
            except Exception:
                pass

    def status(self):
        return {
            "loaded": sorted(self.modules.keys()),
            "count": len(self.modules),
        }


class AutonomousRuntime:
    def __init__(self):
        self.events = EventBus()
        self.memory = Memory(DB)
        self.audit = Audit(AUDIT)
        self.registry = ToolRegistry()
        self.governance = Governance()
        self.bridge = Bridge()

        self._register_tools()

        self.audit.write(
            "runtime_initialized",
            {
                "autonomy": self.governance.autonomy,
                "approvals": self.governance.approvals,
            },
        )

    def _register_tools(self):
        self.registry.register(
            "system_info",
            "Retourne les informations de base du runtime.",
            self.tool_system_info,
        )

        self.registry.register(
            "list_tools",
            "Liste les outils disponibles.",
            self.tool_list_tools,
        )

        self.registry.register(
            "memory_put",
            "Enregistre une information dans la mémoire.",
            self.tool_memory_put,
        )

        self.registry.register(
            "memory_get",
            "Récupère une information précise de la mémoire.",
            self.tool_memory_get,
        )

        self.registry.register(
            "memory_search",
            "Recherche dans la mémoire.",
            self.tool_memory_search,
        )

        self.registry.register(
            "python_check",
            "Vérifie la syntaxe d'un fichier Python.",
            self.tool_python_check,
        )

        self.registry.register(
            "shell",
            "Exécute une commande locale dans le projet Gaïrus.",
            self.tool_shell,
            dangerous=True,
        )

        self.registry.register(
            "git_status",
            "Retourne l'état Git du projet.",
            self.tool_git_status,
        )

        self.registry.register(
            "git_log",
            "Retourne les derniers commits Git.",
            self.tool_git_log,
        )

        self.registry.register(
            "http_get",
            "Effectue une requête HTTP GET.",
            self.tool_http_get,
        )

        self.registry.register(
            "inspect_modules",
            "Inspecte les modules Gaïrus chargés.",
            self.tool_inspect_modules,
        )

    def tool_system_info(self) -> Dict[str, Any]:
        return {
            "agent": os.getenv("GAIRUS_NAME", "Gaïrus"),
            "runtime": "autonomous_runtime_v3",
            "python": sys.version.split()[0],
            "root": str(ROOT),
            "autonomy": self.governance.autonomy,
            "approvals": self.governance.approvals,
            "tools": len(self.registry.tools),
            "timestamp": now(),
        }

    def tool_list_tools(self):
        return self.registry.list()

    def tool_memory_put(self, key: str, value: Any):
        self.memory.put(key, value)

        self.audit.write(
            "memory_put",
            {
                "key": key,
            },
        )

        return {
            "ok": True,
            "key": key,
        }

    def tool_memory_get(self, key: str):
        return {
            "key": key,
            "value": self.memory.get(key),
        }

    def tool_memory_search(self, query: str, limit: int = 20):
        return self.memory.search(query, limit)

    def tool_python_check(self, file: str):
        target = self._safe_path(file)

        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(target)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        return {
            "ok": result.returncode == 0,
            "file": str(target.relative_to(ROOT)),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def tool_shell(self, command: str):
        result = subprocess.run(
            command,
            shell=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )

        self.audit.write(
            "shell",
            {
                "command": command,
                "returncode": result.returncode,
            },
        )

        return {
            "ok": result.returncode == 0,
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def tool_git_status(self):
        return self.tool_shell(
            "git status --short --branch"
        )

    def tool_git_log(self):
        return self.tool_shell(
            "git log --oneline -10"
        )

    def tool_http_get(self, url: str, timeout: int = 20):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Gairus-Autonomous-Runtime/3.0"
            },
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(200000)

            return {
                "ok": True,
                "status": response.status,
                "url": response.geturl(),
                "content_type": response.headers.get("Content-Type"),
                "body": body.decode("utf-8", errors="replace"),
            }

    def tool_inspect_modules(self):
        return self.bridge.status()

    def _safe_path(self, file: str) -> Path:
        candidate = (ROOT / file).resolve()

        if candidate != ROOT and ROOT not in candidate.parents:
            raise ValueError("Chemin hors du projet Gaïrus interdit.")

        if not candidate.exists():
            raise FileNotFoundError(str(candidate))

        return candidate

    def plan(self, objective: str) -> Mission:
        objective = objective.strip()

        tasks = []

        if objective.startswith("shell:"):
            command = objective[len("shell:"):].strip()

            tasks.append(
                Task(
                    id=str(uuid.uuid4()),
                    action="shell",
                    arguments={
                        "command": command,
                    },
                )
            )

        elif objective.startswith("remember:"):
            content = objective[len("remember:"):].strip()

            tasks.append(
                Task(
                    id=str(uuid.uuid4()),
                    action="memory_put",
                    arguments={
                        "key": "mission_memory",
                        "value": content,
                    },
                )
            )

        elif objective.startswith("http://") or objective.startswith("https://"):
            tasks.append(
                Task(
                    id=str(uuid.uuid4()),
                    action="http_get",
                    arguments={
                        "url": objective,
                    },
                )
            )

        else:
            tasks.append(
                Task(
                    id=str(uuid.uuid4()),
                    action="system_info",
                    arguments={},
                )
            )

        mission = Mission(
            id=str(uuid.uuid4()),
            objective=objective,
            tasks=tasks,
        )

        self.audit.write(
            "mission_planned",
            {
                "mission_id": mission.id,
                "objective": objective,
                "task_count": len(tasks),
            },
        )

        return mission

    def run_task(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None,
    ):
        tool = self.registry.get(task.action)

        if not tool:
            task.status = "failed"
            task.error = f"Outil inconnu: {task.action}"
            return task

        allowed, reason = self.governance.allowed(
            tool,
            context,
        )

        if not allowed:
            task.status = "blocked"
            task.error = reason

            self.audit.write(
                "task_blocked",
                {
                    "task_id": task.id,
                    "tool": task.name if hasattr(task, "name") else task.action,
                    "reason": reason,
                },
            )

            return task

        try:
            task.status = "running"

            self.events.emit(
                "task_started",
                {
                    "task_id": task.id,
                    "action": task.action,
                },
            )

            task.result = tool.handler(**task.arguments)
            task.status = "completed"

            self.audit.write(
                "task_completed",
                {
                    "task_id": task.id,
                    "action": task.action,
                },
            )

        except Exception as exc:
            task.status = "failed"
            task.error = f"{type(exc).__name__}: {exc}"

            self.audit.write(
                "task_failed",
                {
                    "task_id": task.id,
                    "action": task.action,
                    "error": task.error,
                },
            )

        self.events.emit(
            "task_finished",
            {
                "task_id": task.id,
                "action": task.action,
                "status": task.status,
            },
        )

        return task

    def run(
        self,
        objective: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        mission = self.plan(objective)
        mission.status = "running"

        for task in mission.tasks:
            self.run_task(task, context)

            if task.status in ("failed", "blocked"):
                mission.status = task.status
                break
        else:
            mission.status = "completed"

        self.audit.write(
            "mission_finished",
            {
                "mission_id": mission.id,
                "status": mission.status,
            },
        )

        return {
            "mission": asdict(mission),
        }


_runtime: Optional[AutonomousRuntime] = None
_runtime_lock = threading.Lock()


def get_runtime() -> AutonomousRuntime:
    global _runtime

    if _runtime is None:
        with _runtime_lock:
            if _runtime is None:
                _runtime = AutonomousRuntime()

    return _runtime


def health():
    runtime = get_runtime()

    return {
        "ok": True,
        "agent": os.getenv("GAIRUS_NAME", "Gaïrus"),
        "runtime": "autonomous_runtime_v3",
        "autonomy": runtime.governance.autonomy,
        "approvals": runtime.governance.approvals,
        "tools": len(runtime.registry.tools),
        "modules": runtime.bridge.status(),
        "timestamp": now(),
    }


def run(objective: str, context: Optional[Dict[str, Any]] = None):
    return get_runtime().run(objective, context)


def execute(
    action: str,
    arguments: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
):
    runtime = get_runtime()

    task = Task(
        id=str(uuid.uuid4()),
        action=action,
        arguments=arguments or {},
    )

    return asdict(runtime.run_task(task, context))


def remember(key: str, value: Any):
    return get_runtime().tool_memory_put(key, value)


def recall(key: str):
    return get_runtime().tool_memory_get(key)


def search_memory(query: str, limit: int = 20):
    return get_runtime().tool_memory_search(query, limit)


def main():
    runtime = get_runtime()

    if len(sys.argv) < 2:
        print(
            "Usage: python autonomous_runtime_v3.py "
            "[health|tools|modules|run|shell|remember|recall|search-memory]"
        )
        return 0

    command = sys.argv[1]

    if command == "health":
        print(dump(health()))
        return 0

    if command == "tools":
        print(dump(runtime.registry.list()))
        return 0

    if command == "modules":
        print(dump(runtime.bridge.status()))
        return 0

    if command == "run":
        if len(sys.argv) < 3:
            print("Objectif manquant.")
            return 1

        objective = " ".join(sys.argv[2:])
        print(dump(run(objective)))
        return 0

    if command == "shell":
        if len(sys.argv) < 3:
            print("Commande manquante.")
            return 1

        command_text = " ".join(sys.argv[2:])

        result = execute(
            "shell",
            {
                "command": command_text,
            },
            {
                "approved": True,
            },
        )

        print(dump(result))
        return 0

    if command == "remember":
        if len(sys.argv) < 4:
            print("Usage: remember <key> <value>")
            return 1

        key = sys.argv[2]
        value = " ".join(sys.argv[3:])

        print(
            dump(
                remember(
                    key,
                    value,
                )
            )
        )

        return 0

    if command == "recall":
        if len(sys.argv) != 3:
            print("Usage: recall <key>")
            return 1

        print(dump(recall(sys.argv[2])))
        return 0

    if command == "search-memory":
        if len(sys.argv) < 3:
            print("Usage: search-memory <query>")
            return 1

        query = " ".join(sys.argv[2:])
        print(dump(search_memory(query)))
        return 0

    print(f"Commande inconnue: {command}")
    return 1

