import os
import json
import sqlite3
import uuid
import threading
from datetime import datetime, timezone

DB_PATH = os.getenv("GAIRUS_DB", "data/gairus.db")

_ENGINE_LOCK = threading.Lock()


def now():
    return datetime.now(timezone.utc).isoformat()


def db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_autonomy():
    with _ENGINE_LOCK:
        conn = db()

        conn.executescript("""
        CREATE TABLE IF NOT EXISTS autonomy_missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            objective TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planning',
            plan TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS autonomy_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            mission_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            priority INTEGER NOT NULL DEFAULT 5,
            depends_on TEXT,
            result TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS autonomy_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id TEXT UNIQUE NOT NULL,
            task_id TEXT NOT NULL,
            tool TEXT NOT NULL,
            parameters TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            requires_approval INTEGER NOT NULL DEFAULT 0,
            approval_id TEXT,
            result TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS autonomy_approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            approval_id TEXT UNIQUE NOT NULL,
            action_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            reason TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT
        );

        CREATE TABLE IF NOT EXISTS autonomy_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id TEXT,
            task_id TEXT,
            action_id TEXT,
            event_type TEXT NOT NULL,
            message TEXT,
            data TEXT,
            created_at TEXT NOT NULL
        );
        """)

        conn.commit()
        conn.close()


def event(mission_id, task_id, action_id, event_type, message, data=None):
    conn = db()

    conn.execute(
        """
        INSERT INTO autonomy_events
        (mission_id, task_id, action_id, event_type, message, data, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mission_id,
            task_id,
            action_id,
            event_type,
            message,
            json.dumps(data or {}, ensure_ascii=False),
            now(),
        ),
    )

    conn.commit()
    conn.close()


def create_mission(title, objective):
    mission_id = str(uuid.uuid4())
    timestamp = now()

    conn = db()

    conn.execute(
        """
        INSERT INTO autonomy_missions
        (mission_id, title, objective, status, created_at, updated_at)
        VALUES (?, ?, ?, 'planning', ?, ?)
        """,
        (
            mission_id,
            title,
            objective,
            timestamp,
            timestamp,
        ),
    )

    conn.commit()
    conn.close()

    event(
        mission_id,
        None,
        None,
        "mission.created",
        "Mission créée",
        {
            "title": title,
            "objective": objective,
        },
    )

    return mission_id


def create_task(
    mission_id,
    title,
    description="",
    priority=5,
    depends_on=None,
):
    task_id = str(uuid.uuid4())
    timestamp = now()

    conn = db()

    conn.execute(
        """
        INSERT INTO autonomy_tasks
        (task_id, mission_id, title, description, status,
         priority, depends_on, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """,
        (
            task_id,
            mission_id,
            title,
            description,
            priority,
            json.dumps(depends_on or []),
            timestamp,
            timestamp,
        ),
    )

    conn.commit()
    conn.close()

    event(
        mission_id,
        task_id,
        None,
        "task.created",
        "Tâche créée",
        {"title": title},
    )

    return task_id


def create_action(
    task_id,
    tool,
    parameters=None,
    requires_approval=False,
):
    action_id = str(uuid.uuid4())
    timestamp = now()

    conn = db()

    conn.execute(
        """
        INSERT INTO autonomy_actions
        (action_id, task_id, tool, parameters, status,
         requires_approval, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
        """,
        (
            action_id,
            task_id,
            tool,
            json.dumps(parameters or {}, ensure_ascii=False),
            int(bool(requires_approval)),
            timestamp,
            timestamp,
        ),
    )

    conn.commit()
    conn.close()

    if requires_approval:
        approval_id = str(uuid.uuid4())

        conn = db()

        conn.execute(
            """
            INSERT INTO autonomy_approvals
            (approval_id, action_id, status, reason, created_at)
            VALUES (?, ?, 'pending', ?, ?)
            """,
            (
                approval_id,
                action_id,
                f"L'action '{tool}' nécessite une approbation.",
                timestamp,
            ),
        )

        conn.execute(
            """
            UPDATE autonomy_actions
            SET status='waiting_approval',
                approval_id=?,
                updated_at=?
            WHERE action_id=?
            """,
            (
                approval_id,
                timestamp,
                action_id,
            ),
        )

        conn.commit()
        conn.close()

        event(
            None,
            task_id,
            action_id,
            "approval.requested",
            "Approbation requise",
            {
                "approval_id": approval_id,
                "tool": tool,
            },
        )

    else:
        event(
            None,
            task_id,
            action_id,
            "action.created",
            "Action créée",
            {"tool": tool},
        )

    return action_id


def update_status(table, key, value, status):
    allowed = {
        "autonomy_missions": "mission_id",
        "autonomy_tasks": "task_id",
        "autonomy_actions": "action_id",
    }

    if table not in allowed:
        raise ValueError("Table interdite")

    conn = db()

    conn.execute(
        f"""
        UPDATE {table}
        SET status=?, updated_at=?
        WHERE {allowed[table]}=?
        """,
        (
            status,
            now(),
            value,
        ),
    )

    conn.commit()
    conn.close()


def list_rows(table, limit=100):
    allowed = {
        "autonomy_missions",
        "autonomy_tasks",
        "autonomy_actions",
        "autonomy_approvals",
        "autonomy_events",
    }

    if table not in allowed:
        raise ValueError("Table interdite")

    conn = db()

    rows = conn.execute(
        f"""
        SELECT *
        FROM {table}
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def get_pending_actions():
    conn = db()

    rows = conn.execute(
        """
        SELECT *
        FROM autonomy_actions
        WHERE status='pending'
        ORDER BY id ASC
        """
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def get_action(action_id):
    conn = db()

    row = conn.execute(
        """
        SELECT *
        FROM autonomy_actions
        WHERE action_id=?
        """,
        (action_id,),
    ).fetchone()

    conn.close()

    return dict(row) if row else None


def approve(approval_id):
    conn = db()

    row = conn.execute(
        """
        SELECT action_id
        FROM autonomy_approvals
        WHERE approval_id=?
        AND status='pending'
        """,
        (approval_id,),
    ).fetchone()

    if not row:
        conn.close()
        return False

    timestamp = now()

    conn.execute(
        """
        UPDATE autonomy_approvals
        SET status='approved',
            resolved_at=?
        WHERE approval_id=?
        """,
        (
            timestamp,
            approval_id,
        ),
    )

    conn.execute(
        """
        UPDATE autonomy_actions
        SET status='pending',
            updated_at=?
        WHERE action_id=?
        """,
        (
            timestamp,
            row["action_id"],
        ),
    )

    conn.commit()
    conn.close()

    event(
        None,
        None,
        row["action_id"],
        "approval.approved",
        "Action approuvée",
        {"approval_id": approval_id},
    )

    return True


def reject(approval_id):
    conn = db()

    row = conn.execute(
        """
        SELECT action_id
        FROM autonomy_approvals
        WHERE approval_id=?
        AND status='pending'
        """,
        (approval_id,),
    ).fetchone()

    if not row:
        conn.close()
        return False

    timestamp = now()

    conn.execute(
        """
        UPDATE autonomy_approvals
        SET status='rejected',
            resolved_at=?
        WHERE approval_id=?
        """,
        (
            timestamp,
            approval_id,
        ),
    )

    conn.execute(
        """
        UPDATE autonomy_actions
        SET status='rejected',
            updated_at=?
        WHERE action_id=?
        """,
        (
            timestamp,
            row["action_id"],
        ),
    )

    conn.commit()
    conn.close()

    event(
        None,
        None,
        row["action_id"],
        "approval.rejected",
        "Action refusée",
        {"approval_id": approval_id},
    )

    return True


def execute_action(action_id, tool_registry=None):
    action = get_action(action_id)

    if not action:
        return {
            "ok": False,
            "error": "Action introuvable",
        }

    if action["status"] == "waiting_approval":
        return {
            "ok": False,
            "error": "Approbation requise",
            "approval_id": action["approval_id"],
        }

    if action["status"] not in ("pending", "approved"):
        return {
            "ok": False,
            "error": f"Action dans l'état {action['status']}",
        }

    tool = action["tool"]

    try:
        parameters = json.loads(
            action["parameters"] or "{}"
        )
    except Exception:
        parameters = {}

    update_status(
        "autonomy_actions",
        action_id,
        action_id,
        "running",
    )

    event(
        None,
        action["task_id"],
        action_id,
        "action.started",
        f"Exécution de {tool}",
        parameters,
    )

    try:
        registry = tool_registry or {}

        if tool not in registry:
            raise RuntimeError(
                f"Outil non disponible: {tool}"
            )

        result = registry[tool](**parameters)

        conn = db()

        conn.execute(
            """
            UPDATE autonomy_actions
            SET status='completed',
                result=?,
                updated_at=?
            WHERE action_id=?
            """,
            (
                json.dumps(
                    result,
                    ensure_ascii=False,
                    default=str,
                ),
                now(),
                action_id,
            ),
        )

        conn.commit()
        conn.close()

        event(
            None,
            action["task_id"],
            action_id,
            "action.completed",
            f"Action {tool} terminée",
            {"result": result},
        )

        return {
            "ok": True,
            "result": result,
        }

    except Exception as exc:
        conn = db()

        conn.execute(
            """
            UPDATE autonomy_actions
            SET status='failed',
                error=?,
                updated_at=?
            WHERE action_id=?
            """,
            (
                str(exc),
                now(),
                action_id,
            ),
        )

        conn.commit()
        conn.close()

        event(
            None,
            action["task_id"],
            action_id,
            "action.failed",
            str(exc),
        )

        return {
            "ok": False,
            "error": str(exc),
        }


def run_cycle(tool_registry=None):
    results = []

    for action in get_pending_actions():
        results.append(
            execute_action(
                action["action_id"],
                tool_registry=tool_registry,
            )
        )

    return results


init_autonomy()

# ============================================================
# GAÏRUS AI PLANNER
# ============================================================

def plan_mission(mission_id, planner=None):
    """
    Transforme automatiquement l'objectif d'une mission
    en tâches structurées.

    planner(prompt) doit retourner du JSON :
    {
      "tasks": [
        {
          "title": "...",
          "description": "...",
          "priority": 1,
          "tool": "...",
          "requires_approval": false,
          "parameters": {}
        }
      ]
    }
    """

    conn = db()

    mission = conn.execute(
        """
        SELECT *
        FROM autonomy_missions
        WHERE mission_id=?
        """,
        (mission_id,),
    ).fetchone()

    conn.close()

    if not mission:
        return {
            "ok": False,
            "error": "Mission introuvable"
        }

    if planner is None:
        return {
            "ok": False,
            "error": "Planner IA non connecté"
        }

    prompt = f"""
Tu es le planificateur autonome de Gaïrus.

Mission :
{mission["title"]}

Objectif :
{mission["objective"]}

Transforme cette mission en étapes exécutables.

Retourne UNIQUEMENT un JSON valide :

{{
  "tasks": [
    {{
      "title": "titre court",
      "description": "description précise",
      "priority": 1,
      "tool": "nom_outil",
      "requires_approval": false,
      "parameters": {{}}
    }}
  ]
}}

Règles :
- 1 à 10 tâches maximum.
- Les tâches doivent être concrètes.
- Utilise "none" si aucun outil n'est encore nécessaire.
- Ne prétends pas qu'une action a déjà été exécutée.
- Les actions externes ou potentiellement sensibles doivent avoir
  requires_approval=true.
"""

    try:
        raw = planner(prompt)

        if isinstance(raw, dict):
            data = raw
        else:
            text = str(raw).strip()

            if text.startswith("```"):
                text = text.replace("```json", "")
                text = text.replace("```", "")
                text = text.strip()

            data = json.loads(text)

        tasks = data.get("tasks", [])

        if not isinstance(tasks, list):
            raise ValueError("Format tasks invalide")

        created = []

        for item in tasks[:10]:
            title = str(
                item.get("title") or "Étape sans titre"
            ).strip()

            description = str(
                item.get("description") or ""
            ).strip()

            priority = int(
                item.get("priority") or 5
            )

            task_id = create_task(
                mission_id=mission_id,
                title=title,
                description=description,
                priority=priority,
            )

            tool = str(
                item.get("tool") or "none"
            ).strip()

            if tool and tool != "none":
                action_id = create_action(
                    task_id=task_id,
                    tool=tool,
                    parameters=item.get(
                        "parameters"
                    ) or {},
                    requires_approval=bool(
                        item.get(
                            "requires_approval",
                            False
                        )
                    ),
                )
            else:
                action_id = None

            created.append({
                "task_id": task_id,
                "action_id": action_id,
                "title": title,
                "tool": tool,
            })

        conn = db()

        conn.execute(
            """
            UPDATE autonomy_missions
            SET status='planned',
                plan=?,
                updated_at=?
            WHERE mission_id=?
            """,
            (
                json.dumps(
                    created,
                    ensure_ascii=False
                ),
                now(),
                mission_id,
            ),
        )

        conn.commit()
        conn.close()

        event(
            mission_id,
            None,
            None,
            "mission.planned",
            "Plan généré par Gaïrus",
            {"tasks": created},
        )

        return {
            "ok": True,
            "mission_id": mission_id,
            "tasks": created,
        }

    except Exception as exc:
        conn = db()

        conn.execute(
            """
            UPDATE autonomy_missions
            SET status='planning_failed',
                updated_at=?
            WHERE mission_id=?
            """,
            (
                now(),
                mission_id,
            ),
        )

        conn.commit()
        conn.close()

        event(
            mission_id,
            None,
            None,
            "mission.planning_failed",
            str(exc),
        )

        return {
            "ok": False,
            "error": str(exc),
        }


def start_mission(mission_id, planner):
    result = plan_mission(
        mission_id,
        planner=planner
    )

    if not result.get("ok"):
        return result

    conn = db()

    conn.execute(
        """
        UPDATE autonomy_missions
        SET status='ready',
            updated_at=?
        WHERE mission_id=?
        """,
        (
            now(),
            mission_id,
        ),
    )

    conn.commit()
    conn.close()

    event(
        mission_id,
        None,
        None,
        "mission.ready",
        "Mission prête pour exécution",
    )

    return result

# ============================================================
# GAÏRUS AUTONOMY RUNTIME
# Missions → planification → tâches → actions → outils
# → validation → exécution → suivi → reprise automatique
# ============================================================

import os
import json
import time
import threading
import traceback
from datetime import datetime, timezone

_RUNTIME_STARTED = False
_RUNTIME_LOCK = threading.Lock()
_RUNTIME_THREAD = None


def _runtime_now():
    return datetime.now(timezone.utc).isoformat()


def _safe_json(value):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False))
    except Exception:
        return str(value)


# ------------------------------------------------------------
# OUTILS NATIFS
# ------------------------------------------------------------

def tool_noop(parameters=None):
    return {
        "ok": True,
        "tool": "noop",
        "result": parameters or {}
    }


def tool_system_status(parameters=None):
    return {
        "ok": True,
        "tool": "system_status",
        "time": _runtime_now(),
        "pid": os.getpid(),
        "autonomy": os.getenv("GAIRUS_AUTONOMY", "false"),
        "approvals": os.getenv("GAIRUS_APPROVALS", "true")
    }


def tool_memory_write(parameters=None):
    parameters = parameters or {}

    content = str(
        parameters.get("content")
        or parameters.get("text")
        or ""
    ).strip()

    if not content:
        return {
            "ok": False,
            "error": "Contenu mémoire absent"
        }

    try:
        conn = db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO memories(content, created_at)
            VALUES (?, ?)
            """,
            (content, _runtime_now())
        )

        conn.commit()
        memory_id = cur.lastrowid
        conn.close()

        return {
            "ok": True,
            "tool": "memory_write",
            "memory_id": memory_id
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc)
        }


def tool_memory_read(parameters=None):
    parameters = parameters or {}
    limit = int(parameters.get("limit", 10))

    try:
        conn = db()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM memories
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )

        rows = [dict(row) for row in cur.fetchall()]
        conn.close()

        return {
            "ok": True,
            "tool": "memory_read",
            "memories": rows
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc)
        }


def tool_http_get(parameters=None):
    """
    Outil HTTP volontairement protégé.
    Les actions externes restent soumises à validation.
    """
    parameters = parameters or {}
    url = str(parameters.get("url") or "").strip()

    if not url:
        return {
            "ok": False,
            "error": "URL absente"
        }

    if not (
        url.startswith("https://")
        or url.startswith("http://")
    ):
        return {
            "ok": False,
            "error": "URL non autorisée"
        }

    try:
        import requests

        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": "Gairus-Autonomy/1.0"
            }
        )

        return {
            "ok": True,
            "tool": "http_get",
            "status_code": response.status_code,
            "url": url,
            "content": response.text[:20000]
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc)
        }


TOOL_REGISTRY = {
    "none": tool_noop,
    "noop": tool_noop,
    "system_status": tool_system_status,
    "memory_read": tool_memory_read,
    "memory_write": tool_memory_write,
    "http_get": tool_http_get,
}


APPROVAL_REQUIRED_TOOLS = {
    "http_get",
}


def execute_registered_tool(tool, parameters=None):
    tool = str(tool or "none").strip()

    fn = TOOL_REGISTRY.get(tool)

    if fn is None:
        return {
            "ok": False,
            "error": f"Outil inconnu: {tool}"
        }

    return fn(parameters or {})


# ------------------------------------------------------------
# PROPAGATION DES STATUTS
# ------------------------------------------------------------

def refresh_task_status(task_id):
    """
    Recalcule le statut d'une tâche à partir de ses actions.
    task_id est l'identifiant métier UUID, jamais l'id SQLite.
    """
    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT status
        FROM autonomy_actions
        WHERE task_id = ?
        ORDER BY created_at ASC
        """,
        (task_id,)
    )

    actions = [row["status"] for row in cur.fetchall()]

    if not actions:
        conn.close()
        return None

    if any(status == "failed" for status in actions):
        status = "failed"
    elif any(
        status in ("pending", "waiting_approval", "running")
        for status in actions
    ):
        status = "waiting_approval" if any(
            value == "waiting_approval" for value in actions
        ) else "running"
    elif all(status == "completed" for status in actions):
        status = "completed"
    elif all(status == "rejected" for status in actions):
        status = "rejected"
    else:
        status = "running"

    timestamp = now()

    cur.execute(
        """
        UPDATE autonomy_tasks
        SET status = ?, updated_at = ?
        WHERE task_id = ?
        """,
        (status, timestamp, task_id)
    )

    conn.commit()
    conn.close()

    return status

def refresh_mission_status(mission_id):
    """
    Recalcule le statut d'une mission à partir de ses tâches.
    mission_id est l'identifiant métier UUID.
    """
    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT status
        FROM autonomy_tasks
        WHERE mission_id = ?
        ORDER BY created_at ASC
        """,
        (mission_id,)
    )

    tasks = [row["status"] for row in cur.fetchall()]

    if not tasks:
        conn.close()
        return None

    if any(status == "failed" for status in tasks):
        status = "failed"
    elif any(status == "waiting_approval" for status in tasks):
        status = "waiting_approval"
    elif any(status in ("pending", "running") for status in tasks):
        status = "running"
    elif all(status == "completed" for status in tasks):
        status = "completed"
    elif all(status == "rejected" for status in tasks):
        status = "rejected"
    else:
        status = "running"

    timestamp = now()

    cur.execute(
        """
        UPDATE autonomy_missions
        SET status = ?, updated_at = ?
        WHERE mission_id = ?
        """,
        (status, timestamp, mission_id)
    )

    conn.commit()
    conn.close()

    return status

def recover_runtime():
    """
    Au démarrage, Gaïrus récupère les éléments interrompus.
    Les actions et tâches qui étaient en cours repassent en attente.
    """
    try:
        timestamp = now()

        conn = db()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE autonomy_actions
            SET status = 'pending',
                updated_at = ?
            WHERE status = 'running'
            """,
            (timestamp,)
        )

        cur.execute(
            """
            UPDATE autonomy_tasks
            SET status = 'pending',
                updated_at = ?
            WHERE status = 'running'
            """,
            (timestamp,)
        )

        conn.commit()
        conn.close()

        event(
            None,
            None,
            None,
            "runtime.recovery",
            "Reprise automatique du moteur",
            {
                "message": "Les actions et tâches interrompues ont été récupérées"
            },
        )

        return True

    except Exception as exc:
        return False

def autonomous_runtime_cycle():
    """
    Cycle global :
    1. récupère les missions actives
    2. planifie celles sans tâches
    3. exécute les actions disponibles
    4. met à jour les statuts
    """

    results = []

    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM autonomy_missions
        WHERE status IN ('pending', 'running')
        ORDER BY created_at ASC
        LIMIT 10
        """
    )

    missions = [
        dict(row)
        for row in cur.fetchall()
    ]

    conn.close()

    for mission in missions:

        mission_id = mission["id"]

        conn = db()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM autonomy_tasks
            WHERE mission_id = ?
            """,
            (mission_id,)
        )

        task_count = cur.fetchone()["count"]

        conn.close()

        if task_count == 0:

            plan_result = autonomous_plan_mission(
                mission_id
            )

            results.append({
                "mission_id": mission_id,
                "phase": "planning",
                "result": plan_result
            })

            if not plan_result.get("ok"):
                continue

        cycle_result = autonomous_mission_cycle(
            mission_id
        )

        results.append({
            "mission_id": mission_id,
            "phase": "execution",
            "result": cycle_result
        })

    return {
        "ok": True,
        "missions": len(missions),
        "results": results,
        "time": _runtime_now()
    }


# Remplace le cycle générique par le véritable orchestrateur.
autonomous_cycle = autonomous_runtime_cycle


_AUTONOMY_SCHEDULER = None


def start_autonomy_runtime():
    global _AUTONOMY_SCHEDULER

    if _AUTONOMY_SCHEDULER is not None:
        return _AUTONOMY_SCHEDULER

    enabled = str(os.getenv("GAIRUS_AUTONOMY", "false")).strip().lower()
    if enabled not in ("1", "true", "yes", "on"):
        return None

    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        interval = int(os.getenv("GAIRUS_INTERVAL", "30"))

        recover_runtime()

        scheduler = BackgroundScheduler(
            daemon=True,
            timezone="UTC",
        )

        scheduler.add_job(
            autonomous_runtime_cycle,
            trigger="interval",
            seconds=max(5, interval),
            id="gairus_autonomy_runtime",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=max(30, interval),
        )

        scheduler.start()
        _AUTONOMY_SCHEDULER = scheduler

        event(
            None,
            None,
            None,
            "runtime.started",
            "Moteur d'autonomie démarré",
            {
                "interval": max(5, interval),
                "enabled": True,
            },
        )

        return scheduler

    except Exception as exc:
        try:
            event(
                None,
                None,
                None,
                "runtime.error",
                "Échec du démarrage du moteur d'autonomie",
                {
                    "error": str(exc),
                },
            )
        except Exception:
            pass

        return None


def stop_autonomy_runtime():
    global _AUTONOMY_SCHEDULER

    if _AUTONOMY_SCHEDULER is None:
        return False

    try:
        _AUTONOMY_SCHEDULER.shutdown(wait=False)
    except Exception:
        pass

    _AUTONOMY_SCHEDULER = None

    try:
        event(
            None,
            None,
            None,
            "runtime.stopped",
            "Moteur d'autonomie arrêté",
            {},
        )
    except Exception:
        pass

    return True
