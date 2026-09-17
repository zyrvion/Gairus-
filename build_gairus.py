from pathlib import Path
import textwrap

FILES = {
"app.py": r'''
import os
import json
import time
import uuid
import threading
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
WORKSPACE = Path(os.getenv("GAIRUS_WORKSPACE", BASE)).resolve()
DATA.mkdir(exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

LOCK = threading.RLock()

DEFAULT_CONFIG = {
    "name": "Gaïrus",
    "version": "2.0",
    "autonomy": os.getenv("GAIRUS_AUTONOMY", "true").lower() != "false",
    "autonomy_interval": int(os.getenv("GAIRUS_AUTONOMY_INTERVAL", "30")),
    "max_parallel_tasks": int(os.getenv("GAIRUS_MAX_PARALLEL_TASKS", "3")),
}

BRAIN_DEFINITIONS = {
    "orchestrator": {
        "name": "Orchestrateur",
        "description": "Coordination générale des cerveaux et décisions de routage",
        "provider": "auto",
    },
    "reasoning": {
        "name": "Raisonnement",
        "description": "Analyse, logique, planification et résolution de problèmes",
        "provider": "auto",
    },
    "developer": {
        "name": "Développeur",
        "description": "Code, architecture, debugging, Git et automatisation",
        "provider": "auto",
    },
    "research": {
        "name": "Recherche",
        "description": "Recherche Web, documentation, synthèse et vérification",
        "provider": "auto",
    },
    "business": {
        "name": "Business",
        "description": "Stratégie, produits, opérations et entrepreneuriat",
        "provider": "auto",
    },
    "analyst": {
        "name": "Analyste",
        "description": "Données, calculs, tableaux, indicateurs et rapports",
        "provider": "auto",
    },
    "creative": {
        "name": "Créatif",
        "description": "Idéation, rédaction, design et communication",
        "provider": "auto",
    },
    "vision": {
        "name": "Vision",
        "description": "Analyse d'images et de documents visuels",
        "provider": "openai",
    },
    "voice": {
        "name": "Voix",
        "description": "Interaction vocale et synthèse vocale",
        "provider": "browser",
    },
    "memory": {
        "name": "Mémoire",
        "description": "Mémoire courte, longue durée et contexte",
        "provider": "local",
    },
    "security": {
        "name": "Sécurité",
        "description": "Permissions, validations et contrôle des actions",
        "provider": "local",
    },
    "autonomy": {
        "name": "Autonomie",
        "description": "Objectifs, missions, tâches, observation et boucles autonomes",
        "provider": "local",
    },
    "evaluator": {
        "name": "Évaluateur",
        "description": "Contrôle qualité, vérification et amélioration",
        "provider": "auto",
    },
}

BRAIN_KEYWORDS = {
    "developer": ["code", "python", "javascript", "typescript", "html", "css", "bug",
                  "debug", "github", "git", "programmer", "développe", "application",
                  "api", "serveur", "flask", "node", "render"],
    "research": ["cherche", "recherche", "web", "internet", "documentation", "source",
                 "actualité", "trouve", "vérifie", "information"],
    "business": ["business", "entreprise", "marché", "client", "vente", "produit",
                 "marketing", "startup", "stratégie", "revenu"],
    "analyst": ["analyse", "données", "data", "calcul", "statistique", "tableau",
                "rapport", "indicateur", "compare"],
    "creative": ["écris", "rédige", "créatif", "design", "logo", "publicité",
                 "contenu", "script", "idée"],
    "vision": ["image", "photo", "capture", "visuel", "screenshot", "regarde"],
}

class Store:
    def __init__(self):
        self.path = DATA / "gairus.json"
        self.state = {
            "memory": [],
            "missions": [],
            "tasks": [],
            "goals": [],
            "events": [],
            "approvals": [],
            "metrics": {"requests": 0, "errors": 0, "tasks_done": 0},
        }
        self.load()

    def load(self):
        if self.path.exists():
            try:
                self.state.update(json.loads(self.path.read_text(encoding="utf-8")))
            except Exception:
                pass

    def save(self):
        with LOCK:
            self.path.write_text(
                json.dumps(self.state, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

    def event(self, kind, data=None):
        item = {
            "id": str(uuid.uuid4()),
            "time": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "data": data or {},
        }
        self.state["events"].append(item)
        self.state["events"] = self.state["events"][-500:]
        self.save()
        return item

store = Store()

def env(name):
    value = os.getenv(name, "")
    return value.strip()

def provider_status():
    return {
        "openai": bool(env("OPENAI_API_KEY")),
        "anthropic": bool(env("ANTHROPIC_API_KEY")),
        "ollama": bool(env("OLLAMA_URL")),
        "local": True,
    }

def choose_brain(text):
    low = text.lower()
    scores = {name: 0 for name in BRAIN_DEFINITIONS}

    for brain, words in BRAIN_KEYWORDS.items():
        for word in words:
            if word in low:
                scores[brain] += 1

    winner = max(scores, key=scores.get)
    return winner if scores[winner] > 0 else "reasoning"

def select_model(brain):
    specific = env(f"GAIRUS_{brain.upper()}_MODEL")
    if specific:
        return specific

    defaults = {
        "reasoning": env("OPENAI_MODEL") or "gpt-4o-mini",
        "developer": env("GAIRUS_DEVELOPER_MODEL") or env("OPENAI_MODEL") or "gpt-4o-mini",
        "research": env("GAIRUS_RESEARCH_MODEL") or env("OPENAI_MODEL") or "gpt-4o-mini",
        "business": env("GAIRUS_BUSINESS_MODEL") or env("OPENAI_MODEL") or "gpt-4o-mini",
        "analyst": env("GAIRUS_ANALYST_MODEL") or env("OPENAI_MODEL") or "gpt-4o-mini",
        "creative": env("GAIRUS_CREATIVE_MODEL") or env("OPENAI_MODEL") or "gpt-4o-mini",
        "evaluator": env("GAIRUS_EVALUATOR_MODEL") or env("OPENAI_MODEL") or "gpt-4o-mini",
        "vision": env("GAIRUS_VISION_MODEL") or "gpt-4o-mini",
    }
    return defaults.get(brain, env("OPENAI_MODEL") or "gpt-4o-mini")

def recent_memory(limit=12):
    return store.state["memory"][-limit:]

def save_memory(role, content, brain=None):
    store.state["memory"].append({
        "id": str(uuid.uuid4()),
        "time": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "content": content,
        "brain": brain,
    })
    store.state["memory"] = store.state["memory"][-1000:]
    store.save()

def openai_chat(messages, model):
    import urllib.request

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": "Bearer " + env("OPENAI_API_KEY"),
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as response:
        data = json.loads(response.read().decode())

    return data["choices"][0]["message"]["content"]

def anthropic_chat(messages, model):
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [
            {"role": m["role"], "content": m["content"]}
            for m in messages if m["role"] != "system"
        ],
    }

    system = next(
        (m["content"] for m in messages if m["role"] == "system"),
        ""
    )
    if system:
        payload["system"] = system

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": env("ANTHROPIC_API_KEY"),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as response:
        data = json.loads(response.read().decode())

    return "".join(
        block.get("text", "")
        for block in data.get("content", [])
        if block.get("type") == "text"
    )

def ollama_chat(messages, model):
    url = env("OLLAMA_URL").rstrip("/") + "/api/chat"

    payload = {
        "model": model or env("OLLAMA_MODEL") or "llama3.2",
        "messages": messages,
        "stream": False,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=180) as response:
        data = json.loads(response.read().decode())

    return data["message"]["content"]

def llm(messages, brain="reasoning"):
    statuses = provider_status()
    model = select_model(brain)

    if statuses["openai"]:
        return openai_chat(messages, model), "openai", model

    if statuses["anthropic"]:
        anthropic_model = env(f"GAIRUS_{brain.upper()}_MODEL") or env(
            "ANTHROPIC_MODEL"
        ) or "claude-3-5-sonnet-latest"
        return anthropic_chat(messages, anthropic_model), "anthropic", anthropic_model

    if statuses["ollama"]:
        return ollama_chat(messages, env("OLLAMA_MODEL") or "llama3.2"), "ollama", model

    return local_fallback(messages[-1]["content"]), "local", "fallback"

def local_fallback(text):
    return (
        "Gaïrus est opérationnel, mais aucun fournisseur de modèle distant "
        "n'est configuré. La demande a été reçue par le cerveau local.\n\n"
        "Pour activer le raisonnement IA complet, configure OPENAI_API_KEY, "
        "ANTHROPIC_API_KEY ou OLLAMA_URL dans les variables d'environnement Render."
    )

def system_prompt(brain):
    definition = BRAIN_DEFINITIONS[brain]
    return f"""
Tu es {definition['name']}, un cerveau spécialisé de Gaïrus.
Gaïrus est un agent IA polyvalent, proactif, professionnel et orienté exécution.

Mission du cerveau:
{definition['description']}

Règles:
- Répondre en français sauf demande contraire.
- Être précis et concret.
- Ne jamais prétendre avoir exécuté une action qui ne l'a pas été.
- Utiliser le contexte mémoire fourni.
- Si une tâche dépasse ton rôle, signaler quel cerveau doit intervenir.
- Pour une action sensible, demander une validation.
- Pour du code, produire du code exploitable.
- Pour une mission complexe, décomposer en étapes vérifiables.
"""

def route_and_answer(text, history=None):
    brain = choose_brain(text)

    memory_context = "\n".join(
        f"{m['role']}: {m['content']}" for m in recent_memory(10)
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt(brain)
            + "\n\nMémoire récente:\n"
            + memory_context
        }
    ]

    if history:
        for item in history[-10:]:
            if item.get("role") in ("user", "assistant"):
                messages.append({
                    "role": item["role"],
                    "content": str(item.get("content", "")),
                })

    messages.append({"role": "user", "content": text})

    answer, provider, model = llm(messages, brain)

    save_memory("user", text, brain)
    save_memory("assistant", answer, brain)

    store.state["metrics"]["requests"] += 1
    store.event("chat.completed", {
        "brain": brain,
        "provider": provider,
        "model": model,
    })

    return {
        "answer": answer,
        "brain": brain,
        "brain_name": BRAIN_DEFINITIONS[brain]["name"],
        "provider": provider,
        "model": model,
    }

def create_mission(title, objective, priority="normal"):
    mission = {
        "id": str(uuid.uuid4()),
        "title": title,
        "objective": objective,
        "priority": priority,
        "status": "planned",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tasks": [],
    }

    store.state["missions"].append(mission)
    store.event("mission.created", mission)
    store.save()
    return mission

def create_task(mission_id, title, brain="reasoning"):
    task = {
        "id": str(uuid.uuid4()),
        "mission_id": mission_id,
        "title": title,
        "brain": brain,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    store.state["tasks"].append(task)

    for mission in store.state["missions"]:
        if mission["id"] == mission_id:
            mission["tasks"].append(task["id"])

    store.event("task.created", task)
    store.save()
    return task

def autonomous_cycle():
    if not DEFAULT_CONFIG["autonomy"]:
        return

    goals = [
        g for g in store.state["goals"]
        if g.get("status") == "active"
    ]

    for goal in goals:
        existing = [
            m for m in store.state["missions"]
            if m.get("objective") == goal["text"]
            and m.get("status") in ("planned", "running")
        ]

        if existing:
            continue

        mission = create_mission(
            "Objectif autonome",
            goal["text"],
            goal.get("priority", "normal")
        )

        create_task(
            mission["id"],
            "Analyser l'objectif et préparer le prochain plan d'action",
            "reasoning"
        )

def autonomy_loop():
    while True:
        try:
            autonomous_cycle()
        except Exception as exc:
            store.state["metrics"]["errors"] += 1
            store.event("autonomy.error", {"error": str(exc)})
        time.sleep(DEFAULT_CONFIG["autonomy_interval"])

@app.get("/")
def index():
    return render_template(
        "index.html",
        brains=BRAIN_DEFINITIONS,
        config=DEFAULT_CONFIG
    )

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "gairus",
        "version": DEFAULT_CONFIG["version"],
        "time": datetime.now(timezone.utc).isoformat(),
    })

@app.get("/api/status")
def status():
    return jsonify({
        "name": DEFAULT_CONFIG["name"],
        "version": DEFAULT_CONFIG["version"],
        "production": True,
        "autonomy": DEFAULT_CONFIG["autonomy"],
        "providers": provider_status(),
        "brains": len(BRAIN_DEFINITIONS),
        "missions": len(store.state["missions"]),
        "tasks": len(store.state["tasks"]),
        "memory": len(store.state["memory"]),
        "metrics": store.state["metrics"],
    })

@app.get("/api/capabilities")
def capabilities():
    return jsonify({
        "brains": BRAIN_DEFINITIONS,
        "capabilities": [
            "multi_brain",
            "reasoning",
            "coding",
            "research",
            "business",
            "analysis",
            "creative",
            "vision",
            "voice",
            "memory",
            "missions",
            "tasks",
            "autonomy",
            "evaluation",
            "security",
            "monitoring",
            "web",
            "files",
            "api",
        ]
    })

@app.post("/api/chat")
def chat():
    try:
        body = request.get_json(silent=True) or {}
        text = str(body.get("message", "")).strip()

        if not text:
            return jsonify({"error": "message_required"}), 400

        result = route_and_answer(
            text,
            body.get("history", [])
        )

        return jsonify(result)

    except Exception as exc:
        store.state["metrics"]["errors"] += 1
        store.save()
        return jsonify({"error": str(exc)}), 500

@app.get("/api/memory")
def memory():
    return jsonify(store.state["memory"][-100:])

@app.post("/api/memory")
def add_memory():
    body = request.get_json(silent=True) or {}
    content = str(body.get("content", "")).strip()

    if not content:
        return jsonify({"error": "content_required"}), 400

    save_memory("user", content, "memory")
    return jsonify({"ok": True})

@app.get("/api/missions")
def missions():
    return jsonify(store.state["missions"])

@app.post("/api/missions")
def missions_create():
    body = request.get_json(silent=True) or {}

    title = str(body.get("title", "Mission Gaïrus"))
    objective = str(body.get("objective", "")).strip()

    if not objective:
        return jsonify({"error": "objective_required"}), 400

    mission = create_mission(
        title,
        objective,
        body.get("priority", "normal")
    )

    return jsonify(mission), 201

@app.get("/api/tasks")
def tasks():
    return jsonify(store.state["tasks"])

@app.post("/api/tasks")
def tasks_create():
    body = request.get_json(silent=True) or {}

    mission_id = str(body.get("mission_id", ""))
    title = str(body.get("title", "")).strip()

    if not title:
        return jsonify({"error": "title_required"}), 400

    task = create_task(
        mission_id,
        title,
        body.get("brain", choose_brain(title))
    )

    return jsonify(task), 201

@app.post("/api/goals")
def goal_create():
    body = request.get_json(silent=True) or {}
    text = str(body.get("text", "")).strip()

    if not text:
        return jsonify({"error": "text_required"}), 400

    goal = {
        "id": str(uuid.uuid4()),
        "text": text,
        "priority": body.get("priority", "normal"),
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    store.state["goals"].append(goal)
    store.event("goal.created", goal)
    store.save()

    return jsonify(goal), 201

@app.get("/api/goals")
def goals():
    return jsonify(store.state["goals"])

@app.get("/api/events")
def events():
    return jsonify(store.state["events"][-200:])

@app.post("/api/autonomy/start")
def autonomy_start():
    DEFAULT_CONFIG["autonomy"] = True
    store.event("autonomy.started")
    return jsonify({"autonomy": True})

@app.post("/api/autonomy/stop")
def autonomy_stop():
    DEFAULT_CONFIG["autonomy"] = False
    store.event("autonomy.stopped")
    return jsonify({"autonomy": False})

@app.post("/api/web/search")
def web_search():
    body = request.get_json(silent=True) or {}
    query = str(body.get("query", "")).strip()

    if not query:
        return jsonify({"error": "query_required"}), 400

    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")

        return jsonify({
            "query": query,
            "results_available": True,
            "source": "Google",
            "preview": html[:5000],
        })

    except Exception as exc:
        return jsonify({
            "query": query,
            "results_available": False,
            "error": str(exc),
        }), 502

@app.post("/api/tools/file")
def file_tool():
    body = request.get_json(silent=True) or {}
    relative = str(body.get("path", "")).strip()

    if not relative:
        return jsonify({"error": "path_required"}), 400

    target = (WORKSPACE / relative).resolve()

    try:
        target.relative_to(WORKSPACE)
    except ValueError:
        return jsonify({"error": "path_outside_workspace"}), 403

    action = body.get("action", "read")

    if action == "read":
        if not target.exists() or not target.is_file():
            return jsonify({"error": "file_not_found"}), 404

        return jsonify({
            "path": str(target.relative_to(WORKSPACE)),
     cd ~/gairus && cat > BUILD_GAIRUS.py <<'PY'
from pathlib import Path

FILES = {}

FILES["requirements.txt"] = r'''
Flask==3.1.2
gunicorn==23.0.0
requests==2.32.5
python-dotenv==1.1.1
APScheduler==3.11.0
playwright==1.55.0
'''

FILES["render.yaml"] = r'''
services:
  - type: web
    name: gairus
    runtime: python
    buildCommand: pip install -r requirements.txt && playwright install chromium
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 180
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.10
      - key: GAIRUS_DATA_DIR
        value: ./data
      - key: GAIRUS_PROVIDER
        value: openai
      - key: GAIRUS_AUTONOMY
        value: "false"
      - key: GAIRUS_APPROVALS
        value: "true"
'''

FILES[".env.example"] = r'''
GAIRUS_NAME=Gaïrus
GAIRUS_PROVIDER=openai
GAIRUS_MODEL=gpt-5.6-luna
GAIRUS_AUTONOMY=false
GAIRUS_APPROVALS=true
GAIRUS_INTERVAL=30
GAIRUS_DATA_DIR=./data

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6-luna

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5

GOOGLE_API_KEY=
GOOGLE_MODEL=gemini-2.5-flash

OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2

SLACK_SIGNING_SECRET=
SLACK_BOT_TOKEN=

WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=

GAIRUS_BROWSER=true
GAIRUS_MAX_ACTIONS=25
'''

FILES[".gitignore"] = r'''
.env
data/
__pycache__/
*.pyc
.pytest_cache/
.playwright/
.DS_Store
'''

FILES["app.py"] = r'''
import os
import re
import json
import time
import uuid
import sqlite3
import hashlib
import secrets
import threading
import subprocess
import pathlib
import math
import traceback
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("GAIRUS_NAME", "Gaïrus")
DATA_DIR = pathlib.Path(os.getenv("GAIRUS_DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "gairus.db"

app = Flask(__name__)

DB_LOCK = threading.RLock()


# ============================================================
# DATABASE
# ============================================================

def db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with DB_LOCK:
        c = db()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS memories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT,
            text TEXT,
            embedding TEXT,
            importance REAL DEFAULT 0.5,
            created REAL
        );

        CREATE TABLE IF NOT EXISTS knowledge(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            source TEXT,
            text TEXT,
            embedding TEXT,
            created REAL
        );

        CREATE TABLE IF NOT EXISTS goals(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            status TEXT DEFAULT 'active',
            created REAL,
            updated REAL
        );

        CREATE TABLE IF NOT EXISTS missions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            objective TEXT,
            status TEXT DEFAULT 'planned',
            brain TEXT,
            plan TEXT,
            progress REAL DEFAULT 0,
            created REAL,
            updated REAL
        );

        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id INTEGER,
            title TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending',
            assigned_brain TEXT,
            result TEXT,
            attempts INTEGER DEFAULT 0,
            created REAL,
            updated REAL
        );

        CREATE TABLE IF NOT EXISTS actions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id INTEGER,
            task_id INTEGER,
            tool TEXT,
            action TEXT,
            input TEXT,
            output TEXT,
            status TEXT,
            approved INTEGER DEFAULT 0,
            created REAL
        );

        CREATE TABLE IF NOT EXISTS approvals(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            risk TEXT,
            payload TEXT,
            status TEXT DEFAULT 'pending',
            created REAL,
            resolved REAL
        );

        CREATE TABLE IF NOT EXISTS schedules(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            job TEXT,
            interval INTEGER,
            enabled INTEGER DEFAULT 1,
            last_run REAL,
            next_run REAL,
            created REAL
        );

        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            payload TEXT,
            created REAL
        );

        CREATE TABLE IF NOT EXISTS conversations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session TEXT,
            role TEXT,
            content TEXT,
            brain TEXT,
            created REAL
        );

        CREATE TABLE IF NOT EXISTS metrics(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            value REAL,
            created REAL
        );

        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)
        c.commit()
        c.close()


def q(sql, args=(), fetch=False, one=False):
    with DB_LOCK:
        c = db()
        cur = c.execute(sql, args)
        c.commit()
        if fetch:
            rows = cur.fetchall()
            c.close()
            return rows[0] if rows and one else rows
        result = cur.lastrowid
        c.close()
        return result


def event(kind, payload=None):
    q(
        "INSERT INTO events(type,payload,created) VALUES(?,?,?)",
        (kind, json.dumps(payload or {}, ensure_ascii=False), time.time())
    )


def metric(name, value):
    q(
        "INSERT INTO metrics(name,value,created) VALUES(?,?,?)",
        (name, float(value), time.time())
    )


# ============================================================
# BRAINS
# ============================================================

BRAINS = {
    "orchestrator": "coordination globale et distribution des missions",
    "reasoning": "raisonnement complexe et stratégie",
    "developer": "développement logiciel, architecture, tests et débogage",
    "research": "recherche web, documentation et synthèse",
    "business": "business, produit, opérations et stratégie",
    "analyst": "analyse de données et métriques",
    "creative": "créativité, rédaction et conception",
    "vision": "vision multimodale et compréhension des images",
    "voice": "interaction vocale",
    "memory": "mémoire et connaissances",
    "security": "sécurité, permissions et risques",
    "autonomy": "objectifs, observation, planification et autonomie",
    "evaluator": "évaluation indépendante et contrôle qualité",
}


ROUTES = {
    "developer": [
        "code", "python", "javascript", "bug", "programme",
        "programmer", "développe", "github", "render", "api",
        "application", "site", "fonction"
    ],
    "research": [
        "cherche", "recherche", "source", "documentation",
        "internet", "actualité", "informations", "trouve"
    ],
    "business": [
        "business", "entreprise", "client", "vente",
        "marketing", "marché", "produit", "prix"
    ],
    "analyst": [
        "analyse", "données", "statistique", "métrique",
        "rapport", "tableau", "calcul"
    ],
    "creative": [
        "écris", "rédige", "design", "idée", "créatif",
        "contenu", "nom", "logo"
    ],
    "vision": [
        "image", "photo", "capture", "visuel", "regarde",
        "analyse cette image"
    ],
    "security": [
        "sécurité", "permission", "secret", "clé", "risque",
        "authentification", "mot de passe"
    ],
    "memory": [
        "souviens", "mémoire", "rappelle", "retenir"
    ],
    "autonomy": [
        "autonome", "mission", "objectif", "surveille",
        "proactif", "planifie", "exécute"
    ]
}


def route_brain(text):
    t = text.lower()
    scores = {}
    for brain, words in ROUTES.items():
        scores[brain] = sum(1 for word in words if word in t)

    best = max(scores, key=scores.get) if scores else "orchestrator"
    if scores.get(best, 0) == 0:
        return "orchestrator"
    return best


# ============================================================
# VECTOR MEMORY
# ============================================================

def tokenize(text):
    return re.findall(r"[a-zA-ZÀ-ÿ0-9_]+", text.lower())


def vectorize(text):
    """
    Vecteur lexical déterministe.
    Il fonctionne sans service externe.
    Quand un fournisseur d'embeddings est disponible,
    le système peut évoluer vers de vrais embeddings.
    """
    words = tokenize(text)
    vec = {}
    for w in words:
        h = int(hashlib.sha256(w.encode()).hexdigest()[:8], 16)
        index = h % 256
        vec[index] = vec.get(index, 0.0) + 1.0

    norm = math.sqrt(sum(v*v for v in vec.values())) or 1.0
    return {str(k): v/norm for k,v in vec.items()}


def similarity(a, b):
    if not a or not b:
        return 0
    return sum(float(v) * float(b.get(k, 0)) for k,v in a.items())


def remember(text, kind="conversation", importance=0.5):
    emb = vectorize(text)
    q(
        """INSERT INTO memories(kind,text,embedding,importance,created)
           VALUES(?,?,?,?,?)""",
        (
            kind,
            text,
            json.dumps(emb),
            importance,
            time.time()
        )
    )


def semantic_memory(query_text, limit=12):
    target = vectorize(query_text)
    rows = q(
        "SELECT * FROM memories ORDER BY id DESC LIMIT 500",
        fetch=True
    )

    scored = []

    for row in rows:
        try:
            emb = json.loads(row["embedding"] or "{}")
            score = similarity(target, emb)
        except Exception:
            score = 0

        scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        dict(row) | {"score": score}
        for score,row in scored[:limit]
    ]


# ============================================================
# RAG KNOWLEDGE BASE
# ============================================================

def add_knowledge(title, source, text):
    emb = vectorize(text)
    q(
        """INSERT INTO knowledge(title,source,text,embedding,created)
           VALUES(?,?,?,?,?)""",
        (
            title,
            source,
            text,
            json.dumps(emb),
            time.time()
        )
    )


def search_knowledge(query_text, limit=8):
    target = vectorize(query_text)
    rows = q(
        "SELECT * FROM knowledge ORDER BY id DESC LIMIT 1000",
        fetch=True
    )

    result = []

    for row in rows:
        try:
            emb = json.loads(row["embedding"] or "{}")
            score = similarity(target, emb)
        except Exception:
            score = 0
        result.append((score,row))

    result.sort(key=lambda x:x[0], reverse=True)

    return [
        dict(row) | {"score": score}
        for score,row in result[:limit]
    ]


# ============================================================
# MODEL PROVIDERS
# ============================================================

def openai_chat(messages, model=None, image=None):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY non configurée")

    model = model or os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

    content = messages

    if image:
        content = []
        for m in messages:
            if m["role"] == "user":
                content.append({
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": m["content"]},
                        {
                            "type": "input_image",
                            "image_url": image
                        }
                    ]
                })
            else:
                content.append(m)

    r = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "input": content
        },
        timeout=180
    )

    r.raise_for_status()

    data = r.json()

    if data.get("output_text"):
        return data["output_text"]

    result = []

    for item in data.get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                result.append(c.get("text",""))

    return "\n".join(result)


def anthropic_chat(messages, model=None):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY non configurée")

    model = model or os.getenv(
        "ANTHROPIC_MODEL",
        "claude-sonnet-4-5"
    )

    system = "\n".join(
        m["content"]
        for m in messages
        if m["role"] == "system"
    )

    user_messages = [
        m for m in messages
        if m["role"] != "system"
    ]

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": model,
            "max_tokens": 8192,
            "system": system,
            "messages": user_messages
        },
        timeout=180
    )

    r.raise_for_status()

    data = r.json()

    return "".join(
        item.get("text","")
        for item in data.get("content", [])
    )


def ollama_chat(messages, model=None):
    url = os.getenv(
        "OLLAMA_URL",
        "http://127.0.0.1:11434"
    )

    model = model or os.getenv(
        "OLLAMA_MODEL",
        "llama3.2"
    )

    r = requests.post(
        url.rstrip("/") + "/api/chat",
        json={
            "model": model,
            "messages": messages,
            "stream": False
        },
        timeout=180
    )

    r.raise_for_status()

    return r.json()["message"]["content"]


def gemini_chat(messages, model=None):
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY non configurée")

    model = model or os.getenv(
        "GOOGLE_MODEL",
        "gemini-2.5-flash"
    )

    prompt = "\n\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in messages
    )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + model +
        ":generateContent?key=" + key
    )

    r = requests.post(
        url,
        json={
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        },
        timeout=180
    )

    r.raise_for_status()

    data = r.json()

    return (
        data.get("candidates",[{}])[0]
        .get("content",{})
        .get("parts",[{}])[0]
        .get("text","")
    )


def model_call(messages, provider=None, model=None, image=None):
    provider = (
        provider or
        os.getenv("GAIRUS_PROVIDER","openai")
    ).lower()

    attempts = []

    configured = [
        ("openai", lambda: openai_chat(messages, model, image)),
        ("anthropic", lambda: anthropic_chat(messages, model)),
        ("gemini", lambda: gemini_chat(messages, model)),
        ("ollama", lambda: ollama_chat(messages, model))
    ]

    order = []

    for name, fn in configured:
        if name == provider:
            order.insert(0,(name,fn))
        else:
            order.append((name,fn))

    for name, fn in order:
        try:
            result = fn()

            if result:
                metric("model_success",1)
                event(
                    "model_success",
                    {"provider":name}
                )
                return result, name

        except Exception as exc:
            attempts.append({
                "provider":name,
                "error":str(exc)
            })
            event(
                "model_fallback",
                {
                    "provider":name,
                    "error":str(exc)
                }
            )

    metric("model_failure",1)

    return (
        "Aucun fournisseur IA disponible.\n"
        + json.dumps(attempts,ensure_ascii=False),
        "fallback"
    )


# ============================================================
# CONTEXT + ORCHESTRATOR
# ============================================================

def context_for(text):
    memories = semantic_memory(text, 8)
    knowledge = search_knowledge(text, 6)

    m = "\n".join(
        f"- {x['kind']}: {x['text']}"
        for x in memories
    )

    k = "\n".join(
        f"- {x['title']} ({x['source']}): {x['text'][:2000]}"
        for x in knowledge
    )

    return (
        "MEMOIRE SEMANTIQUE:\n"
        + m
        + "\n\nBASE DE CONNAISSANCES:\n"
        + k
    )


def specialist_prompt(brain):
    return f"""
Tu es Gaïrus, un employé IA professionnel, polyvalent et orienté résultat.

Cerveau actif:
{brain}

Fonction:
{BRAINS.get(brain,"coordination")}

Règles:
- raisonne avant d'agir;
- ne prétends jamais avoir effectué une action qui n'a pas été effectuée;
- demande une approbation avant une action à risque;
- conserve les informations importantes en mémoire;
- vérifie les résultats;
- si une action échoue, cherche une correction;
- quand une mission est longue, travaille par étapes;
- utilise les autres cerveaux quand nécessaire.
"""


def ask_agent(text, brain=None, session="default", image=None):
    brain = brain or route_brain(text)

    context = context_for(text)

    history = q(
        """
        SELECT role,content
        FROM conversations
        WHERE session=?
        ORDER BY id DESC LIMIT 12
        """,
        (session,),
        fetch=True
    )

    messages = [
        {
            "role":"system",
            "content":specialist_prompt(brain)
        },
        {
            "role":"system",
            "content":context
        }
    ]

    for h in reversed(history):
        messages.append({
            "role":h["role"],
            "content":h["content"]
        })

    messages.append({
        "role":"user",
        "content":text
    })

    answer, provider = model_call(
        messages,
        image=image
    )

    q(
        """
        INSERT INTO conversations
        (session,role,content,brain,created)
        VALUES(?,?,?,?,?)
        """,
        (
            session,
            "user",
            text,
            brain,
            time.time()
        )
    )

    q(
        """
        INSERT INTO conversations
        (session,role,content,brain,created)
        VALUES(?,?,?,?,?)
        """,
        (
            session,
            "assistant",
            answer,
            brain,
            time.time()
        )
    )

    remember(
        f"Utilisateur: {text}\nGaïrus: {answer}",
        "conversation"
    )

    return {
        "reply":answer,
        "brain":brain,
        "provider":provider
    }


# ============================================================
# MULTI-AGENT ORCHESTRATION
# ============================================================

def subagent(text, brain):
    return ask_agent(
        text,
        brain=brain,
        session="subagent-" + uuid.uuid4().hex
    )


def orchestrate(objective):
    """
    Plusieurs cerveaux travaillent sur la même mission.
    """

    selected = [
        "reasoning",
        "research",
        "developer",
        "business",
        "an
cd ~/gairus

cat > BRANCHER_TOUT_GAIRUS.sh <<'BASH'
#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "=============================================="
echo " GAÏRUS — BRANCHEMENT COMPLET"
echo "=============================================="

cd ~/gairus

echo "[1/9] Vérification Python..."
python --version

echo "[2/9] Installation des dépendances..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "[3/9] Installation navigateur Chromium..."
python -m playwright install chromium || true

echo "[4/9] Création de la configuration locale..."

if [ ! -f .env ]; then
cat > .env <<'EOF'
GAIRUS_NAME=Gaïrus

# IA principale
GAIRUS_PROVIDER=openai
GAIRUS_MODEL=gpt-5.6-luna

# Fallback automatique
OPENAI_MODEL=gpt-5.6-luna
ANTHROPIC_MODEL=claude-sonnet-4-5
GEMINI_MODEL=gemini-2.5-flash
OLLAMA_MODEL=llama3.2

# Autonomie
GAIRUS_AUTONOMY=false
GAIRUS_APPROVALS=true
GAIRUS_INTERVAL=30
GAIRUS_MAX_ACTIONS=25

# Données
GAIRUS_DATA_DIR=./data

# Navigateur
GAIRUS_BROWSER=true

# API keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

# Ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434

# Slack
SLACK_SIGNING_SECRET=
SLACK_BOT_TOKEN=

# WhatsApp / Meta
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
EOF
fi

mkdir -p data
mkdir -p logs
mkdir -p uploads
mkdir -p workspace

echo "[5/9] Vérification de la structure..."

python - <<'PY'
import os
import sqlite3

os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("workspace", exist_ok=True)

print("Répertoires Gaïrus: OK")
