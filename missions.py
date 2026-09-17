"""
GAÏRUS — MissionManager (Sections 5, 14, 28, 29, 30 du cahier des charges)
Une mission = un objectif de haut niveau que Gaïrus découpe en étapes,
exécute une par une (avec ses outils), puis vérifie.

Statuts : PENDING, RUNNING, WAITING, COMPLETED, FAILED, CANCELLED
- WAITING : une étape a demandé un outil CONFIRM, en attente de validation humaine.
"""
import json
import re
import sqlite3
import threading
import time

import config
import router
import tools

PLAN_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    plan TEXT,                 -- JSON: liste des étapes prévues
    steps_log TEXT,            -- JSON: liste des étapes déjà exécutées + résultat
    pending_tool TEXT,         -- JSON: outil en attente de confirmation (WAITING)
    result TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
"""

MISSION_PLAN_PROMPT = """Tu es GAÏRUS, un planificateur de missions.
Découpe l'objectif suivant en 2 à 5 étapes concrètes et actionnables.
Réponds UNIQUEMENT avec un JSON de cette forme, rien d'autre :
{{"steps": ["étape 1", "étape 2", "..."]}}

Objectif : {objective}
"""

STEP_EXECUTION_PROMPT = """Tu es GAÏRUS, en train d'exécuter une mission.
Objectif global : {objective}
Étape actuelle à réaliser : {step}

Tu peux utiliser un outil si nécessaire, avec ce format JSON exact et rien d'autre :
{{"tool": "<nom_outil>", "params": {{...}}}}

Outils disponibles :
{tools_list}

Si aucun outil n'est nécessaire, réponds directement en texte avec le résultat de l'étape.
"""


class MissionManager:
    def __init__(self, db_path: str = config.DB_PATH):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self.conn.executescript(_SCHEMA)
            self.conn.commit()

    # ---------- lecture ----------

    def list_missions(self):
        with self._lock:
            cur = self.conn.execute(
                "SELECT id, title, status, created_at, updated_at FROM missions "
                "ORDER BY id DESC LIMIT 50"
            )
            rows = cur.fetchall()
        return [
            {"id": r[0], "title": r[1], "status": r[2], "created_at": r[3], "updated_at": r[4]}
            for r in rows
        ]

    def get_mission(self, mission_id: int):
        with self._lock:
            cur = self.conn.execute(
                "SELECT id, title, status, plan, steps_log, pending_tool, result, "
                "created_at, updated_at FROM missions WHERE id = ?",
                (mission_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0], "title": row[1], "status": row[2],
            "plan": json.loads(row[3]) if row[3] else [],
            "steps_log": json.loads(row[4]) if row[4] else [],
            "pending_tool": json.loads(row[5]) if row[5] else None,
            "result": row[6], "created_at": row[7], "updated_at": row[8],
        }

    def counts(self):
        with self._lock:
            cur = self.conn.execute("SELECT status, COUNT(*) FROM missions GROUP BY status")
            rows = cur.fetchall()
        return {status: n for status, n in rows}

    # ---------- écriture ----------

    def _update(self, mission_id, **fields):
        fields["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [mission_id]
        with self._lock:
            self.conn.execute(f"UPDATE missions SET {set_clause} WHERE id = ?", values)
            self.conn.commit()

    def create_mission(self, title: str) -> int:
        now = time.time()
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO missions (title, status, steps_log, created_at, updated_at) "
                "VALUES (?, 'PENDING', '[]', ?, ?)",
                (title, now, now),
            )
            self.conn.commit()
            mission_id = cur.lastrowid
        # Exécution en tâche de fond : l'appel HTTP ne bloque pas dessus.
        threading.Thread(target=self._run, args=(mission_id,), daemon=True).start()
        return mission_id

    def confirm_pending_tool(self, mission_id: int, approve: bool):
        mission = self.get_mission(mission_id)
        if not mission or mission["status"] != "WAITING" or not mission["pending_tool"]:
            return False
        pending = mission["pending_tool"]
        if approve:
            result = tools.run_tool(pending["tool"], pending.get("params", {}))
        else:
            result = "Action annulée par l'utilisateur."
        steps_log = mission["steps_log"]
        steps_log.append({"step": pending["step"], "tool": pending["tool"], "result": result})
        self._update(mission_id, status="RUNNING", pending_tool=None,
                      steps_log=json.dumps(steps_log, ensure_ascii=False))
        threading.Thread(target=self._run, args=(mission_id,), daemon=True).start()
        return True

    def cancel_mission(self, mission_id: int):
        self._update(mission_id, status="CANCELLED", pending_tool=None)

    # ---------- exécution ----------

    def _extract_json(self, text: str):
        match = PLAN_JSON_RE.search(text)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    def _run(self, mission_id: int):
        mission = self.get_mission(mission_id)
        if not mission:
            return

        # Étape 1 : planifier, si ce n'est pas déjà fait (Section 29)
        if not mission["plan"]:
            self._update(mission_id, status="RUNNING")
            prompt = MISSION_PLAN_PROMPT.format(objective=mission["title"])
            raw = router.call_model([{"role": "user", "content": prompt}])
            parsed = self._extract_json(raw)
            steps = parsed.get("steps") if parsed and isinstance(parsed.get("steps"), list) else [mission["title"]]
            self._update(mission_id, plan=json.dumps(steps, ensure_ascii=False))
            mission = self.get_mission(mission_id)

        steps_log = mission["steps_log"]
        remaining = mission["plan"][len(steps_log):]

        for step in remaining:
            prompt = STEP_EXECUTION_PROMPT.format(
                objective=mission["title"], step=step,
                tools_list=tools.list_tools_for_model(),
            )
            raw = router.call_model([{"role": "user", "content": prompt}])
            tool_call = self._extract_json(raw) if '"tool"' in raw else None

            if tool_call and "tool" in tool_call:
                tool_name = tool_call["tool"]
                params = tool_call.get("params", {})
                permission = config.TOOL_PERMISSIONS.get(tool_name, "RESTRICTED")

                if permission == "RESTRICTED":
                    result = f"Action refusée (RESTRICTED) : {tool_name}"
                    steps_log.append({"step": step, "tool": tool_name, "result": result})
                elif permission == "CONFIRM" and config.AUTONOMY_LEVEL != "AUTONOMOUS":
                    self._update(
                        mission_id, status="WAITING",
                        pending_tool=json.dumps({"step": step, "tool": tool_name, "params": params}, ensure_ascii=False),
                        steps_log=json.dumps(steps_log, ensure_ascii=False),
                    )
                    return  # on s'arrête ici ; confirm_pending_tool() relancera _run()
                else:
                    result = tools.run_tool(tool_name, params)
                    steps_log.append({"step": step, "tool": tool_name, "result": result})
            else:
                steps_log.append({"step": step, "tool": None, "result": raw})

            self._update(mission_id, steps_log=json.dumps(steps_log, ensure_ascii=False))

        # Étape finale : vérification (Section 30 : ne jamais juste supposer un succès)
        summary_prompt = (
            f"Objectif : {mission['title']}\n"
            f"Étapes exécutées : {json.dumps(steps_log, ensure_ascii=False)}\n"
            "Rédige un court résumé final pour l'utilisateur, en confirmant si "
            "l'objectif est atteint ou en signalant ce qui a échoué."
        )
        final = router.call_model([{"role": "user", "content": summary_prompt}])
        self._update(mission_id, status="COMPLETED", result=final)
