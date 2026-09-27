cd ~/gairus && cat > autonomous_runtime.py <<'PY'
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)

DB = DATA / "autonomous_memory.db"
AUDIT = DATA / "autonomous_audit.jsonl"


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(value):
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


class EventBus:
    def __init__(self):
        self.handlers = {}
        self.lock = threading.RLock()

    def subscribe(self, event, handler):
        with self.lock:
            self.handlers.setdefault(event, []).append(handler)

    def publish(self, event, **data):
        with self.lock:
            handlers = list(self.handlers.get(event, []))
        for handler in handlers:
            try:
                handler(**data)
            except Exception:
                pass


class Memory:
    def __init__(self, path=DB):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.init()

    def conn(self):
        c = sqlite3.connect(str(self.path), timeout=30)
        c.row_factory = sqlite3.Row
        return c

    def init(self):
        with self.conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    id TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            c.commit()

    def put(self, key, value, namespace="default"):
        ident = f"{namespace}:{key}"
        ts = now()
        with self.lock:
            with self.conn() as c:
                c.execute("""
                    INSERT INTO memory
                    (id, namespace, key, value, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at
                """, (ident, namespace, key, dump(value), ts, ts))
                c.commit()
        return {
            "id": ident,
            "namespace": namespace,
            "key": key,
            "value": value,
            "updated_at": ts,
        }

    def get(self, key, namespace="default", default=None):
        ident = f"{namespace}:{key}"
        with self.lock:
            with self.conn() as c:
                row = c.execute(
                    "SELECT value FROM memory WHERE id=?",
                    (ident,)
                ).fetchone()
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except Exception:
            return row["value"]

    def search(self, query, namespace=None, limit=20):
        pattern = f"%{query}%"
        sql = """
            SELECT id, namespace, key, value, created_at, updated_at
            FROM memory
            WHERE (key LIKE ? OR value LIKE ?)
        """
        args = [pattern, pattern]
        if namespace:
            sql += " AND namespace=?"
            args.append(namespace)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        args.append(int(limit))
        with self.conn() as c:
            rows = c.execute(sql, args).fetchall()
        result = []
        for r in rows:
            try:
                value = json.loads(r["value"])
            except Exception:
                value = r["value"]
            result.append({
                "id": r["id"],
                "namespace": r["namespace"],
                "key": r["key"],
                "value": value,
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        return result


class Audit:
    def __init__(self, path=AUDIT):
        self.path = Path(path)
        self.lock = threading.RLock()

    def write(self, event, status="ok", **payload):
        record = {
            "timestamp": now(),
            "event": event,
            "status": status,
            "payload": payload,
        }
        with self.lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(dump(record) + "\n")
        return record


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable
    dangerous: bool = False


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name, description, handler, dangerous=False):
        self.tools[name] = Tool(
            name, description, handler, dangerous
        )

    def get(self, name):
        return self.tools.get(name)

    def list(self):
        return [
            {
                "name": t.name,
                "description": t.description,
                "dangerous": t.dangerous,
            }
            for t in self.tools.values()
        ]

    def execute(self, name, **kwargs):
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Outil inconnu: {name}")
        return tool.handler(**kwargs)


class Governance:
    def __init__(self):
        self.autonomy = os.getenv(
            "GAIRUS_AUTONOMY", "true"
        ).lower() in {"1", "true", "yes", "on"}

        self.approvals = os.getenv(
            "GAIRUS_APPROVALS", "true"
        ).lower() in {"1", "true", "yes", "on"}

    def allowed(self, tool, context=None):
        context = context or {}
        if not self.autonomy:
            return False
        if tool.dangerous and self.approvals:
            return bool(context.get("approved"))
        return True


@dataclass
class Task:
    id: str
    description: str
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Mission:
    id: str
    objective: str
    status: str = "created"
    tasks: list = field(default_factory=list)
    result: Any = None
    error: Optional[str] = None
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)


class Bridge:
    def __init__(self):
        self.modules = {}
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
        for name in candidates:
            try:
                self.modules[name] = __import__(
                    name, fromlist=["*"]
                )
            except Exception:
                pass

    def status(self):
        return {
            "loaded_modules": sorted(self.modules),
            "count": len(self.modules),
        }


class AutonomousRuntime:
    def __init__(self):
        self.started_at = now()
        self.events = EventBus()
        self.memory = Memory()
        self.audit = Audit()
        self.tools = ToolRegistry()
        self.governance = Governance()
        self.bridge = Bridge()
        self.missions = {}
        self.lock = threading.RLock()
        self.register_tools()
        self.audit.write(
            "runtime_started",
            autonomy=self.governance.autonomy,
            approvals=self.governance.approvals,
        )

    def register_tools(self):
        self.tools.register(
            "system_info",
            "État du runtime Gaïrus.",
            self.system_info,
        )
        self.tools.register(
            "list_tools",
            "Liste les outils.",
            self.list_tools,
        )
        self.tools.register(
            "memory_put",
            "Écrit dans la mémoire persistante.",
            self.memory_put,
        )
        self.tools.register(
            "memory_get",
            "Lit la mémoire persistante.",
            self.memory_get,
        )
        self.tools.register(
            "memory_search",
            "Recherche dans la mémoire.",
            self.memory_search,
        )
        self.tools.register(
            "python_check",
            "Vérifie la syntaxe Python.",
            self.python_check,
        )
        self.tools.register(
            "shell",
            "Exécute une commande dans le projet.",
            self.shell,
            dangerous=True,
        )
        self.tools.register(
            "git_status",
            "État Git.",
            self.git_status,
        )
        self.tools.register(
            "git_log",
            "Historique Git.",
            self.git_log,
        )
        self.tools.register(
            "http_get",
            "Récupère une ressource HTTP.",
            self.http_get,
            dangerous=True,
        )
        self.tools.register(
            "inspect_modules",
            "Inspecte les modules Gaïrus.",
            self.inspect_modules,
        )

    def system_info(self):
        return {
            "agent": os.getenv("GAIRUS_NAME", "Gaïrus"),
            "runtime": "AutonomousRuntime",
            "version": "1.0",
            "root": str(ROOT),
            "autonomy": self.governance.autonomy,
            "approvals": self.governance.approvals,
            "started_at": self.started_at,
            "pid": os.getpid(),
            "python": sys.version,
            "bridge": self.bridge.status(),
            "tools": len(self.tools.tools),
        }

    def list_tools(self):
        return self.tools.list()

    def memory_put(
        self,
        key,
        value,
        namespace="default",
    ):
        return self.memory.put(key, value, namespace)

    def memory_get(
        self,
        key,
        namespace="default",
        default=None,
    ):
        return self.memory.get(key, namespace, default)

    def memory_search(
        self,
        query,
        namespace=None,
        limit=20,
    ):
        return self.memory.search(
            query, namespace, limit
        )

    def python_check(self, path):
        target = Path(path)
        if not target.is_absolute():
            target = ROOT / target
        target = target.resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            raise ValueError(
                "Le fichier doit rester dans le projet Gaïrus."
            )
        if not target.exists():
            raise FileNotFoundError(str(target))

        r = subprocess.run(
            [sys.executable, "-m", "py_compile", str(target)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        return {
            "ok": r.returncode == 0,
            "path": str(target),
            "stdout": r.stdout,
            "stderr": r.stderr,
            "returncode": r.returncode,
        }

    def shell(self, command, timeout=120):
        if not command.strip():
            raise ValueError("Commande vide.")
        r = subprocess.run(
            command,
            shell=True,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=int(timeout),
        )
        return {
            "ok": r.returncode == 0,
            "command": command,
            "stdout": r.stdout,
            "stderr": r.stderr,
            "returncode": r.returncode,
        }

    def git_status(self):
        r = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout,
            "stderr": r.stderr,
            "returncode": r.returncode,
        }

    def git_log(self, limit=10):
        r = subprocess.run(
            [
                "git",
                "log",
                f"-{int(limit)}",
                "--oneline",
                "--decorate",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout,
            "stderr": r.stderr,
            "returncode": r.returncode,
        }

    def http_get(self, url, timeout=20):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Gaïrus-AutonomousRuntime/1.0"
            },
        )
        with urllib.request.urlopen(
            req,
            timeout=int(timeout),
        ) as response:
            body = response.read().decode(
                "utf-8",
                errors="replace",
            )
            return {
                "ok": True,
                "status": response.status,
                "url": response.geturl(),
                "body": body,
            }

    def inspect_modules(self):
        return self.bridge.status()

    def health(self):
        return {
            "status": "ok",
            "agent": os.getenv(
                "GAIRUS_NAME",
                "Gaïrus",
            ),
            "autonomy": self.governance.autonomy,
            "approvals": self.governance.approvals,
            "tools": len(self.tools.tools),
            "memory": str(self.memory.path),
            "audit": str(self.audit.path),
            "bridge": self.bridge.status(),
        }

    def execute(self, name, _context=None, **kwargs):
        tool = self.tools.get(name)
        if not tool:
            raise ValueError(
                f"Outil inconnu: {name}"
            )

        if not self.governance.allowed(
            tool,
            _context or {},
        ):
            raise PermissionError(
                f"Action non autorisée: {name}"
            )

        self.audit.write(
            "tool_execution",
            tool=name,
            arguments=kwargs,
        )

        return self.tools.execute(
            name,
            **kwargs,
        )

    def plan(self, objective):
        mission = Mission(
            id=str(uuid.uuid4()),
            objective=objective,
        )

        text = objective.strip()
        lower = text.lower()

        if not text:
            mission.status = "failed"
            mission.error = "Objectif vide."
            return mission

        if lower.startswith("shell:"):
            command = text.split(":", 1)[1].strip()
            mission.tasks.append(
                Task(
                    id=str(uuid.uuid4()),
                    description=command,
                    metadata={
                        "tool": "shell",
                        "args": {"command": command},
                    },
                )
            )
        elif lower.startswith("remember:"):
            value = text.split(":", 1)[1].strip()
            mission.tasks.append(
                Task(
                    id=str(uuid.uuid4()),
                    description="Mémoriser",
                    metadata={
                        "tool": "memory_put",
                        "args": {
                            "key": f"note_{int(time.time())}",
                            "value": value,
                        },
                    },
                )
            )
        elif lower.startswith("http://") or \
                lower.startswith("https://"):
            mission.tasks.append(
                Task(
                    id=str(uuid.uuid4()),
                    description=text,
                    metadata={
                        "tool": "http_get",
                        "args": {"url": text},
                    },
                )
            )
        else:
            mission.tasks.append(
                Task(
                    id=str(uuid.uuid4()),
                    description=text,
                    metadata={
                        "tool": "system_info",
                        "args": {},
                    },
                )
            )

        return mission

    def run(self, objective, context=None):
        mission = self.plan(objective)

        with self.lock:
            self.missions[mission.id] = mission

        if mission.status == "failed":
            return mission

        mission.status = "running"
        mission.updated_at = now()

        for task in mission.tasks:
            try:
                task.status = "running"
                tool_name = task.metadata.get("tool")
                args = task.metadata.get("args", {})
                tool = self.tools.get(tool_name)

                if not tool:
                    raise ValueError(
                        f"Outil introuvable: {tool_name}"
                    )

                if not self.governance.allowed(
                    tool,
                    context or {},
                ):
                    raise PermissionError(
                        f"Action non autorisée: {tool_name}"
                    )

                task.result = self.tools.execute(
                    tool_name,
                    **args,
                )
                task.status = "completed"

            except Exception as exc:
                task.status = "failed"
                task.error = (
                    f"{type(exc).__name__}: {exc}"
                )
                mission.status = "failed"
                mission.error = task.error
                break

        if mission.status != "failed":
            mission.status = "completed"
            mission.result = [
                task.result for task in mission.tasks
            ]

        mission.updated_at = now()

        self.audit.write(
            "mission_finished",
            status=(
                "ok"
                if mission.status == "completed"
                else "error"
            ),
            mission_id=mission.id,
            mission_status=mission.status,
        )

        return mission

    def remember(
        self,
        key,
        value,
        namespace="default",
    ):
        return self.memory.put(
            key,
            value,
            namespace,
        )

    def recall(
        self,
        key,
        namespace="default",
        default=None,
    ):
        return self.memory.get(
            key,
            namespace,
            default,
        )

    def search_memory(
        self,
        query,
        namespace=None,
        limit=20,
    ):
        return self.memory.search(
            query,
            namespace,
            limit,
        )


_runtime = None
_runtime_lock = threading.RLock()


def get_runtime():
    global _runtime
    with _runtime_lock:
        if _runtime is None:
            _runtime = AutonomousRuntime()
        return _runtime


def health():
    return get_runtime().health()


def run(objective, context=None):
    return get_runtime().run(
        objective,
        context,
    )


def execute(name, **kwargs):
    return get_runtime().execute(
        name,
        **kwargs,
    )


def remember(key, value, namespace="default"):
    return get_runtime().remember(
        key,
        value,
        namespace,
    )


def recall(key, namespace="default", default=None):
    return get_runtime().recall(
        key,
        namespace,
        default,
    )


def search_memory(
    query,
    namespace=None,
    limit=20,
):
    return get_runtime().search_memory(
        query,
        namespace,
        limit,
    )


def main(argv=None):
    argv = list(
        argv if argv is not None
        else sys.argv[1:]
    )

    if not argv:
     
