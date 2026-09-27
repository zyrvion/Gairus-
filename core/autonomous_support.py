from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

MEMORY_DB = DATA_DIR / "gairus_persistent_memory.db"
AUDIT_FILE = DATA_DIR / "gairus_runtime_audit.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        return json.dumps(str(value), ensure_ascii=False)


class PersistentMemory:
    """
    Mémoire persistante de Gaïrus.

    Elle complète RuntimeMemory :
    - RuntimeMemory = contexte rapide en mémoire vive
    - PersistentMemory = connaissances et événements conservés sur disque
    """

    def __init__(self, path: Path = MEMORY_DB):
        self.path = Path(path)
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(
            str(self.path),
            timeout=30,
            check_same_thread=False,
        )

        connection.row_factory = sqlite3.Row

        return connection

    def _initialize(self):
        with self._lock:
            connection = self._connect()

            try:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        memory_key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        category TEXT,
                        actor_id TEXT,
                        mission_id TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )

                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_memory_key
                    ON memory(memory_key)
                    """
                )

                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_memory_category
                    ON memory(category)
                    """
                )

                connection.commit()

            finally:
                connection.close()

    def put(
        self,
        key: str,
        value: Any,
        category: Optional[str] = None,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        if not key:
            raise ValueError(
                "Memory key cannot be empty"
            )

        timestamp = utc_now()

        with self._lock:
            connection = self._connect()

            try:
                existing = connection.execute(
                    """
                    SELECT id
                    FROM memory
                    WHERE memory_key = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (key,),
                ).fetchone()

                if existing:
                    connection.execute(
                        """
                        UPDATE memory
                        SET value = ?,
                            category = ?,
                            actor_id = ?,
                            mission_id = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            _json(value),
                            category,
                            actor_id,
                            mission_id,
                            timestamp,
                            existing["id"],
                        ),
                    )

                    memory_id = existing["id"]

                else:
                    cursor = connection.execute(
                        """
                        INSERT INTO memory (
                            memory_key,
                            value,
                            category,
                            actor_id,
                            mission_id,
                            created_at,
                            updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            key,
                            _json(value),
                            category,
                            actor_id,
                            mission_id,
                            timestamp,
                            timestamp,
                        ),
                    )

                    memory_id = cursor.lastrowid

                connection.commit()

                return {
                    "id": memory_id,
                    "key": key,
                    "value": value,
                    "category": category,
                    "actor_id": actor_id,
                    "mission_id": mission_id,
                    "updated_at": timestamp,
                }

            finally:
                connection.close()

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:

        if not key:
            return default

        with self._lock:
            connection = self._connect()

            try:
                row = connection.execute(
                    """
                    SELECT value
                    FROM memory
                    WHERE memory_key = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (key,),
                ).fetchone()

                if row is None:
                    return default

                try:
                    return json.loads(row["value"])
                except Exception:
                    return row["value"]

            finally:
                connection.close()

    def has(self, key: str) -> bool:
        marker = object()

        return self.get(key, marker) is not marker

    def delete(self, key: str) -> bool:
        with self._lock:
            connection = self._connect()

            try:
                cursor = connection.execute(
                    """
                    DELETE FROM memory
                    WHERE memory_key = ?
                    """,
                    (key,),
                )

                connection.commit()

                return cursor.rowcount > 0

            finally:
                connection.close()

    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        if not query:
            return []

        limit = max(1, int(limit))
        needle = f"%{query.lower()}%"

        with self._lock:
            connection = self._connect()

            try:
                rows = connection.execute(
                    """
                    SELECT
                        id,
                        memory_key,
                        value,
                        category,
                        actor_id,
                        mission_id,
                        created_at,
                        updated_at
                    FROM memory
                    WHERE
                        lower(memory_key) LIKE ?
                        OR lower(value) LIKE ?
                        OR lower(COALESCE(category, '')) LIKE ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (
                        needle,
                        needle,
                        needle,
                        limit,
                    ),
                ).fetchall()

                results = []

                for row in rows:
                    try:
                        value = json.loads(
                            row["value"]
                        )
                    except Exception:
                        value = row["value"]

                    results.append(
                        {
                            "id": row["id"],
                            "key": row["memory_key"],
                            "value": value,
                            "category": row["category"],
                            "actor_id": row["actor_id"],
                            "mission_id": row["mission_id"],
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                        }
                    )

                return results

            finally:
                connection.close()

    def recent(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        limit = max(1, int(limit))

        with self._lock:
            connection = self._connect()

            try:
                rows = connection.execute(
                    """
                    SELECT
                        id,
                        memory_key,
                        value,
                        category,
                        actor_id,
                        mission_id,
                        created_at,
                        updated_at
                    FROM memory
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

                results = []

                for row in rows:
                    try:
                        value = json.loads(
                            row["value"]
                        )
                    except Exception:
                        value = row["value"]

                    results.append(
                        {
                            "id": row["id"],
                            "key": row["memory_key"],
                            "value": value,
                            "category": row["category"],
                            "actor_id": row["actor_id"],
                            "mission_id": row["mission_id"],
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                        }
                    )

                return results

            finally:
                connection.close()

    def count(self) -> int:
        with self._lock:
            connection = self._connect()

            try:
                row = connection.execute(
                    "SELECT COUNT(*) AS count FROM memory"
                ).fetchone()

                return int(row["count"])

            finally:
                connection.close()

    def status(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "type": "persistent_sqlite",
            "path": str(self.path),
            "entries": self.count(),
        }


class RuntimeAudit:
    """
    Journal persistant des événements importants de Gaïrus.

    Format JSONL :
    une ligne JSON = un événement.
    """

    def __init__(self, path: Path = AUDIT_FILE):
        self.path = Path(path)
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()

    def log(
        self,
        event: str,
        *,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        record = {
            "id": str(uuid.uuid4()),
            "timestamp": utc_now(),
            "event": event,
            "actor_id": actor_id,
            "mission_id": mission_id,
            "status": status,
            "metadata": metadata or {},
        }

        with self._lock:
            with self.path.open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    _json(record) + "\n"
                )

        return record

    def recent(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        limit = max(1, int(limit))

        if not self.path.exists():
            return []

        with self._lock:
            lines = self.path.read_text(
                encoding="utf-8"
            ).splitlines()

        results = []

        for line in reversed(lines):
            if not line.strip():
                continue

            try:
                results.append(
                    json.loads(line)
                )
            except Exception:
                continue

            if len(results) >= limit:
                break

        return results

    def count(self) -> int:
        if not self.path.exists():
            return 0

        with self._lock:
            return sum(
                1
                for line in self.path.open(
                    "r",
                    encoding="utf-8",
                )
                if line.strip()
            )

    def status(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "type": "jsonl",
            "path": str(self.path),
            "events": self.count(),
        }


class EventBus:
    """
    Bus d'événements interne.

    Permet aux composants de Gaïrus de communiquer
    sans créer de dépendances circulaires.
    """

    def __init__(self):
        self._subscribers: Dict[
            str,
            List[Callable[[Dict[str, Any]], Any]],
        ] = {}

        self._history = []
        self._lock = threading.RLock()

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], Any],
    ):

        if not event_type:
            raise ValueError(
                "event_type is required"
            )

        if not callable(handler):
            raise TypeError(
                "handler must be callable"
            )

        with self._lock:
            self._subscribers.setdefault(
                event_type,
                [],
            ).append(handler)

        return handler

    def unsubscribe(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], Any],
    ):

        with self._lock:
            handlers = self._subscribers.get(
                event_type,
                [],
            )

            if handler in handlers:
                handlers.remove(handler)

            if not handlers:
                self._subscribers.pop(
                    event_type,
                    None,
                )

    def emit(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        event = {
            "id": str(uuid.uuid4()),
            "timestamp": utc_now(),
            "type": event_type,
            "data": data or {},
        }

        with self._lock:
            self._history.append(event)

            handlers = list(
                self._subscribers.get(
                    event_type,
                    [],
                )
            )

            wildcard_handlers = list(
                self._subscribers.get(
                    "*",
                    [],
                )
            )

        errors = []

        for handler in handlers + wildcard_handlers:
            try:
                handler(event)
            except Exception as exc:
                errors.append(
                    {
                        "type": exc.__class__.__name__,
                        "error": str(exc),
                    }
                )

        if errors:
            event["handler_errors"] = errors

        return event

    def recent(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        limit = max(1, int(limit))

        with self._lock:
            return [
                dict(event)
                for event in self._history[-limit:]
            ]

    def clear(self):
        with self._lock:
            self._history.clear()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            subscriptions = sum(
                len(handlers)
                for handlers in self._subscribers.values()
            )

            history = len(self._history)

        return {
            "status": "ok",
            "subscriptions": subscriptions,
            "history": history,
            "event_types": list(
                self._subscribers.keys()
            ),
        }


class AutonomousSupport:
    """
    Couche de support autonome de Gaïrus.

    Cette couche ne remplace aucun moteur existant.

    Elle fournit :
    - mémoire persistante ;
    - audit persistant ;
    - bus d'événements ;
    - intégration avec RuntimeMemory lorsqu'elle existe ;
    - intégration avec MissionEngine / ToolRuntime / Operations
      lorsqu'ils sont présents.
    """

    def __init__(
        self,
        runtime: Any = None,
        *,
        memory_path: Path = MEMORY_DB,
        audit_path: Path = AUDIT_FILE,
    ):

        self.runtime = runtime

        self.memory = PersistentMemory(
            path=memory_path,
        )

        self.audit = RuntimeAudit(
            path=audit_path,
        )

        self.events = EventBus()

        self.created_at = utc_now()

        self._bind_runtime()

    def _bind_runtime(self):

        if self.runtime is None:
            return

        runtime_memory = getattr(
            self.runtime,
            "memory",
            None,
        )

        if runtime_memory is not None:
            self.runtime_memory = runtime_memory
        else:
            self.runtime_memory = None

        self._bind_mission_events()
        self._bind_tool_events()

    def _bind_mission_events(self):

        missions = getattr(
            self.runtime,
            "missions",
            None,
        )

        if missions is None:
            return

        self.missions = missions

    def _bind_tool_events(self):

        tools = getattr(
            self.runtime,
            "tools",
            None,
        )

        if tools is None:
            return

        self.tools = tools

    def remember(
        self,
        key: str,
        value: Any,
        *,
        category: Optional[str] = None,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
    ):

        result = self.memory.put(
            key,
            value,
            category=category,
            actor_id=actor_id,
            mission_id=mission_id,
        )

        self.audit.log(
            "memory_written",
            actor_id=actor_id,
            mission_id=mission_id,
            status="ok",
            metadata={
                "key": key,
                "category": category,
            },
        )

        self.events.emit(
            "memory_written",
            {
                "key": key,
                "category": category,
                "mission_id": mission_id,
            },
        )

        return result

    def recall(
        self,
        key: str,
        default: Any = None,
    ):

        return self.memory.get(
            key,
            default,
        )

    def search_memory(
        self,
        query: str,
        limit: int = 20,
    ):

        return self.memory.search(
            query,
            limit=limit,
        )

    def record_mission(
        self,
        mission: Dict[str, Any],
    ):

        mission_id = mission.get("id")

        self.memory.put(
            f"mission:{mission_id}",
            mission,
            category="mission",
                     mission_id=mission_id,
        )

        self.audit.log(
            "mission_recorded",
            mission_id=mission_id,
            status=mission.get("status"),
            metadata={
                "objective": mission.get("objective"),
            },
        )

        self.events.emit(
            "mission_recorded",
            {
                "mission_id": mission_id,
                "status": mission.get("status"),
            },
        )

        return mission

    def record_tool_call(
        self,
        tool_name: str,
        result: Any,
        *,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
    ):

        self.audit.log(
            "tool_executed",
            actor_id=actor_id,
            mission_id=mission_id,
            status="ok",
            metadata={
                "tool": tool_name,
            },
        )

        self.events.emit(
            "tool_executed",
            {
                "tool": tool_name,
                "mission_id": mission_id,
            },
        )

        return result

    def bridge_runtime_memory(
        self,
        event_type: str,
        content: Any,
        *,
        actor_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):

        runtime_memory = getattr(
            self,
            "runtime_memory",
            None,
        )

        if runtime_memory is None:
            return None

        remember = getattr(
            runtime_memory,
            "remember",
            None,
        )

        if not callable(remember):
            return None

        return remember(
            event_type=event_type,
            content=content,
            actor_id=actor_id,
            metadata=metadata,
        )

    def status(self) -> Dict[str, Any]:

        runtime_memory = getattr(
            self,
            "runtime_memory",
            None,
        )

        missions = getattr(
            self,
            "missions",
            None,
        )

        tools = getattr(
            self,
            "tools",
            None,
        )

        return {
            "status": "ok",
            "type": "autonomous_support",
            "created_at": self.created_at,
            "persistent_memory": self.memory.status(),
            "audit": self.audit.status(),
            "events": self.events.status(),
            "runtime_memory": (
                runtime_memory.status()
                if runtime_memory is not None
                and hasattr(runtime_memory, "status")
                else None
            ),
            "missions": (
                missions.status()
                if missions is not None
                and hasattr(missions, "status")
                else (
                    "available"
                    if missions is not None
                    else None
                )
            ),
            "tools": (
                tools.status()
                if tools is not None
                and hasattr(tools, "status")
                else (
                    "available"
                    if tools is not None
                    else None
                )
            ),
        }


_support = None


def get_support(
    runtime: Any = None,
) -> AutonomousSupport:

    global _support

    if _support is None:
        _support = AutonomousSupport(
            runtime=runtime,
        )

    elif runtime is not None:
        _support.runtime = runtime
        _support._bind_runtime()

    return _support


def remember(
    key: str,
    value: Any,
    *,
    category: Optional[str] = None,
    actor_id: Optional[str] = None,
    mission_id: Optional[str] = None,
):

    return get_support().remember(
        key,
        value,
        category=category,
        actor_id=actor_id,
        mission_id=mission_id,
    )


def recall(
    key: str,
    default: Any = None,
):

    return get_support().recall(
        key,
        default,
    )


def search_memory(
    query: str,
    limit: int = 20,
):

    return get_support().search_memory(
        query,
        limit=limit,
    )


def status():
    return get_support().status()
