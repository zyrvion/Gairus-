from pathlib import Path

ROOT = Path(__file__).resolve().parent

FILES = {
    "requirements.txt": """Flask==3.1.2
flask-cors==6.0.1
gunicorn==23.0.0
requests==2.32.5
python-dotenv==1.1.1
APScheduler==3.11.0
""",

    "render.yaml": """services:
  - type: web
    name: gairus
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 180
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.10
      - key: GAIRUS_NAME
        value: Gaïrus
      - key: GAIRUS_AUTONOMY
        value: "false"
      - key: GAIRUS_APPROVALS
        value: "true"
""",

    ".env.example": """GAIRUS_NAME=Gaïrus
GAIRUS_AUTONOMY=false
GAIRUS_APPROVALS=true
GAIRUS_INTERVAL=30
GAIRUS_PROVIDER=openai
GAIRUS_MODEL=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
OLLAMA_BASE_URL=http://127.0.0.1:11434
GAIRUS_DATA_DIR=./data
""",

    "app.py": r'''import os
import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

BASE = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("GAIRUS_DATA_DIR", BASE / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB = DATA_DIR / "gairus.db"

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

NAME = os.getenv("GAIRUS_NAME", "Gaïrus")
AUTONOMY = os.getenv("GAIRUS_AUTONOMY", "false").lower() == "true"
APPROVALS = os.getenv("GAIRUS_APPROVALS", "true").lower() == "true"


def now():
    return datetime.now(timezone.utc).isoformat()


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        kind TEXT DEFAULT 'general',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS missions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        objective TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        mission_id TEXT,
        title TEXT NOT NULL,
        status TEXT NOT NULL,
        result TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        details TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS approvals (
        id TEXT PRIMARY KEY,
        action TEXT NOT NULL,
        details TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event TEXT NOT NULL,
        details TEXT,
        created_at TEXT NOT NULL
    );
    """)
    con.commit()
    con.close()


def log_event(event, details=""):
    con = db()
    con.execute(
        "INSERT INTO events(event,details,created_at) VALUES(?,?,?)",
        (event, details, now()),
    )
    con.commit()
    con.close()


def save_message(role, content):
    con = db()
    con.execute(
        "INSERT INTO conversations(role,content,created_at) VALUES(?,?,?)",
        (role, content, now()),
    )
    con.commit()
    con.close()


def provider_openai(prompt):
    key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("GAIRUS_MODEL")

    if not key or not model:
        return None

    try:
        r = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": prompt,
            },
            timeout=120,
        )
        if not r.ok:
            return None

        data = r.json()

        if data.get("output_text"):
            return data["output_text"]

        parts = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    parts.append(text)

        return "\n".join(parts).strip() or None

    except Exception:
        return None


def provider_anthropic(prompt):
    key = os.getenv("ANTHROPIC_API_KEY")
    model = os.getenv("ANTHROPIC_MODEL")

    if not key or not model:
        return None

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )

        if not r.ok:
            return None

        data = r.json()
        return "\n".join(
            x.get("text", "")
            for x in data.get("content", [])
            if x.get("type") == "text"
        ).strip() or None

    except Exception:
        return None


def provider_ollama(prompt):
    base = os.getenv("OLLAMA_BASE_URL", "").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "")

    if not base or not model:
        return None

    try:
        r = requests.post(
            f"{base}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=180,
        )

        if not r.ok:
            return None

        return r.json().get("message", {}).get("content")

    except Exception:
        return None


def brain_for(prompt):
    p = prompt.lower()

    if any(x in p for x in ["code", "python", "javascript", "bug", "programm", "dévelop"]):
        return "developer"

    if any(x in p for x in ["business", "entreprise", "marché", "client", "vente"]):
        return "business"

    if any(x in p for x in ["cherche", "recherche", "internet", "source", "actual"]):
        return "research"

    if any(x in p for x in ["analyse", "compare", "calcul", "statistique"]):
        return "analyst"

    if any(x in p for x in ["image", "photo", "vision", "vidéo"]):
        return "vision"

    return "orchestrator"


def answer(prompt):
    brain = brain_for(prompt)

    memory = []
    con = db()
    rows = con.execute(
        "SELECT content FROM memories ORDER BY id DESC LIMIT 8"
    ).fetchall()
    memory = [r["content"] for r in rows]
    con.close()

    system = f"""
Tu es {NAME}, un agent IA polyvalent.
Cerveau actif : {brain}.

Tu dois être utile, précis, honnête sur tes capacités et orienté vers l'action.
Tu peux planifier une mission, analyser un problème, développer du logiciel,
faire de la recherche, travailler sur du business et organiser des tâches.

Mémoire disponible :
{chr(10).join(memory)}

Si une capacité externe n'est pas réellement disponible, ne prétends jamais
l'avoir exécutée.
"""

    full_prompt = system + "\n\nUtilisateur:\n" + prompt

    result = provider_openai(full_prompt)

    if not result:
        result = provider_anthropic(full_prompt)

    if not result:
        result = provider_ollama(full_prompt)

    if not result:
        result = (
            "Gaïrus est correctement démarré, mais aucun fournisseur IA "
            "n'est actuellement configuré. Ajoute une clé API et un modèle "
            "dans les variables d'environnement de Render."
        )

    return result, brain


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "agent": NAME,
        "autonomy": AUTONOMY,
        "approvals": APPROVALS,
    })


@app.route("/api/status")
def status():
    return jsonify({
        "agent": NAME,
        "version": "3.0",
        "status": "online",
        "autonomy": AUTONOMY,
        "approvals": APPROVALS,
        "brains": [
            "orchestrator",
            "reasoning",
            "developer",
            "research",
            "business",
            "analyst",
            "creative",
            "vision",
            "voice",
            "memory",
            "security",
            "autonomy",
            "evaluator",
        ],
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("message", "")).strip()

    if not prompt:
        return jsonify({"error": "message manquant"}), 400

    save_message("user", prompt)
    result, brain = answer(prompt)
    save_message("assistant", result)

    log_event("chat", json.dumps({"brain": brain}))

    return jsonify({
        "reply": result,
        "brain": brain,
        "agent": NAME,
    })


@app.route("/api/memory", methods=["GET", "POST"])
def memory():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        content = str(data.get("content", "")).strip()

        if not content:
            return jsonify({"error": "content manquant"}), 400

        con = db()
        con.execute(
            "INSERT INTO memories(content,kind,created_at) VALUES(?,?,?)",
            (content, data.get("kind", "general"), now()),
        )
        con.commit()
        con.close()

        return jsonify({"ok": True})

    con = db()
    rows = con.execute(
        "SELECT * FROM memories ORDER BY id DESC LIMIT 100"
    ).fetchall()
    con.close()

    return jsonify([dict(r) for r in rows])


@app.route("/api/missions", methods=["GET", "POST"])
def missions():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        title = str(data.get("title", "Mission Gaïrus")).strip()
        objective = str(data.get("objective", "")).strip()

        if not objective:
            return jsonify({"error": "objective manquant"}), 400

        mission_id = str(uuid.uuid4())
        t = now()

        con = db()
        con.execute(
            """INSERT INTO missions
            (id,title,objective,status,created_at,updated_at)
            VALUES(?,?,?,?,?,?)""",
            (mission_id, title, objective, "pending", t, t),
        )
        con.commit()
        con.close()

        log_event("mission_created", mission_id)

        return jsonify({
            "id": mission_id,
            "title": title,
            "objective": objective,
            "status": "pending",
        })

    con = db()
    rows = con.execute(
        "SELECT * FROM missions ORDER BY created_at DESC"
    ).fetchall()
    con.close()

    return jsonify([dict(r) for r in rows])


@app.route("/api/tasks", methods=["GET", "POST"])
def tasks():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        task_id = str(uuid.uuid4())
        t = now()

        con = db()
        con.execute(
            """INSERT INTO tasks
            (id,mission_id,title,status,result,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?)""",
            (
                task_id,
                data.get("mission_id"),
                data.get("title", "Nouvelle tâche"),
                "pending",
                None,
                t,
                t,
            ),
        )
        con.commit()
        con.close()

        return jsonify({"id": task_id, "status": "pending"})

    con = db()
    rows = con.execute(
        "SELECT * FROM tasks ORDER BY created_at DESC"
    ).fetchall()
    con.close()

    return jsonify([dict(r) for r in rows])


@app.route("/api/actions")
def actions():
    con = db()
    rows = con.execute(
        "SELECT * FROM actions ORDER BY id DESC LIMIT 200"
    ).fetchall()
    con.close()

    return jsonify([dict(r) for r in rows])


@app.route("/api/events")
def events():
    con = db()
    rows = con.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT 200"
    ).fetchall()
    con.close()

    return jsonify([dict(r) for r in rows])


@app.route("/api/approvals")
def approvals():
    con = db()
    rows = con.execute(
        "SELECT * FROM approvals ORDER BY created_at DESC"
    ).fetchall()
    con.close()

    return jsonify([dict(r) for r in rows])


def autonomy_loop():
    while True:
        try:
            if AUTONOMY:
                log_event("autonomy_cycle", "cycle")
        except Exception as exc:
            log_event("autonomy_error", str(exc))

        time.sleep(int(os.getenv("GAIRUS_INTERVAL", "30")))


init_db()

if AUTONOMY:
    threading.Thread(target=autonomy_loop, daemon=True).start()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False,
    )
''',

    "static/gairus.css": """*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#eef2ff;font-family:system-ui,-apple-system,sans-serif}.app{max-width:1200px;margin:auto;padding:24px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}.brand{font-size:28px;font-weight:800}.status{color:#7dd3fc}.panel{background:#11182d;border:1px solid #26304d;border-radius:18px;padding:20px}.chat{height:60vh;overflow:auto;margin-bottom:16px}.msg{padding:14px;margin:10px 0;border-radius:14px;white-space:pre-wrap}.user{background:#1d4ed8}.assistant{background:#1e293b}.input{display:flex;gap:10px}.input input{flex:1;background:#0f172a;color:white;border:1px solid #334155;border-radius:12px;padding:15px}.input button{border:0;border-radius:12px;padding:0 22px;background:#2563eb;color:white;font-weight:700}""",

    "templates/index.html": """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gaïrus</title>
<link rel="stylesheet" href="/static/gairus.css">
</head>
<body>
<div class="app">
  <div class="top">
    <div class="brand">◈ Gaïrus</div>
    <div class="status" id="status">● connexion...</div>
  </div>

  <div class="panel">
    <div id="chat" class="chat"></div>

    <form id="form" class="input">
      <input id="message" autocomplete="off"
             placeholder="Donne une mission à Gaïrus...">
      <button>Envoyer</button>
    </form>
  </div>
</div>

<script>
const chat=document.getElementById("chat");
const form=document.getElementById("form");
const input=document.getElementById("message");
const status=document.getElementById("status");

function add(role,text){
  const d=document.createElement("div");
  d.className="msg "+role;
  d.textContent=text;
  chat.appendChild(d);
  chat.scrollTop=chat.scrollHeight;
}

async function check(){
  try{
    const r=await fetch("/health");
    const d=await r.json();
    status.textContent="● "+d.agent+" en ligne";
  }catch(e){
    status.textContent="● hors ligne";
  }
}

form.addEventListener("submit",async e=>{
  e.preventDefault();
  const text=input.value.trim();
  if(!text)return;

  add("user",text);
  input.value="";
  add("assistant","Gaïrus réfléchit...");

  const placeholder=chat.lastChild;

  try{
    const r=await fetch("/api/chat",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message:text})
    });

    const d=await r.json();
    placeholder.textContent=d.reply||d.error||"Erreur";
  }catch(err){
    placeholder.textContent="Erreur de connexion à Gaïrus.";
  }
});

check();
</script>
</body>
</html>
"""
}


def write_files():
    for name, content in FILES.items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"✓ {name}")

    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / "uploads").mkdir(exist_ok=True)
    (ROOT / "workspace").mkdir(exist_ok=True)


if __name__ == "__main__":
    print("GAÏRUS | génération propre")
    write_files()
    print("GAÏRUS | génération terminée")
