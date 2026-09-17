"""
GAÏRUS — Interface web minimale (Section 34 : PAGE CHAT)
Sert une page de chat sur http://127.0.0.1:8080, à ouvrir dans le
navigateur du même téléphone. Réutilise le même cerveau (router.py),
la même mémoire (memory.py) et les mêmes outils (tools.py) que la
version terminal — c'est le MÊME Gaïrus, juste une autre façade.
"""
import json
import struct
import zlib
from flask import Flask, request, jsonify, Response

import config
import router
import tools
from memory import Memory
from main import SYSTEM_PROMPT, try_parse_tool_call, check_permission

app = Flask(__name__)
mem = Memory()


def make_icon_png(size: int, bg=(45, 108, 223), fg=(255, 255, 255)) -> bytes:
    """
    Génère une icône PNG carrée en pur Python (aucune dépendance externe,
    donc ça tourne tel quel dans Termux) : fond bleu + cercle clair au
    centre pour évoquer un "œil/cerveau".
    """
    pixels = [[bg for _ in range(size)] for _ in range(size)]
    cx, cy, r = size / 2, size / 2, size * 0.28
    for y in range(size):
        for x in range(size):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                pixels[y][x] = fg

    raw = bytearray()
    for row in pixels:
        raw.append(0)  # filter type 0
        for (r_, g_, b_) in row:
            raw += bytes((r_, g_, b_))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    png = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    return png


_ICON_192 = make_icon_png(192)
_ICON_512 = make_icon_png(512)

MANIFEST = {
    "name": "Gaïrus",
    "short_name": "Gaïrus",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0f1115",
    "theme_color": "#161a22",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
    ],
}

SERVICE_WORKER = """
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => self.clients.claim());
self.addEventListener('fetch', e => {
  // Passthrough simple : pas de cache offline pour l'instant (Phase 1).
  e.respondWith(fetch(e.request));
});
"""

# Une seule "conversation" à la fois dans ce scaffold (usage perso).
# pending = action en attente de confirmation (Section 17 : CONFIRM)
pending = {"tool": None, "params": None}


def build_messages():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += mem.recent_messages(limit=12)
    return messages


def handle_message(user_input: str) -> str:
    # --- Cas 1 : une confirmation est en attente (Section 17) ----------
    if pending["tool"]:
        answer = user_input.strip().lower()
        tool_name, params = pending["tool"], pending["params"]
        if answer in ("oui", "o", "yes", "y"):
            result = tools.run_tool(tool_name, params)
            mem.log_action(tool_name, json.dumps(params), result, "ok")
        else:
            result = "Action annulée par l'utilisateur."
            mem.log_action(tool_name, json.dumps(params), result, "refused")
        pending["tool"], pending["params"] = None, None

        follow_up = build_messages() + [
            {"role": "user", "content": f"[Résultat de l'outil {tool_name}] : {result}\n"
                                         "Formule une réponse claire pour l'utilisateur."}
        ]
        final_answer = router.call_model(follow_up)
        mem.add_message("assistant", final_answer)
        return final_answer

    # --- Cas 2 : message normal -----------------------------------------
    mem.add_message("user", user_input)
    raw_response = router.call_model(build_messages())
    tool_call = try_parse_tool_call(raw_response)

    if not tool_call:
        mem.add_message("assistant", raw_response)
        return raw_response

    tool_name = tool_call.get("tool")
    params = tool_call.get("params", {})
    permission = check_permission(tool_name)

    if permission == "RESTRICTED":
        result = f"Action refusée (permission RESTRICTED) : {tool_name}"
        mem.log_action(tool_name, json.dumps(params), result, "refused")

    elif permission == "CONFIRM" and config.AUTONOMY_LEVEL != "AUTONOMOUS":
        pending["tool"], pending["params"] = tool_name, params
        msg = f"⚠️ Je veux exécuter : {tool_name}({params}). Réponds 'oui' pour confirmer ou 'non' pour annuler."
        mem.add_message("assistant", msg)
        return msg

    else:
        result = tools.run_tool(tool_name, params)
        mem.log_action(tool_name, json.dumps(params), result, "ok")

    follow_up = build_messages() + [
        {"role": "assistant", "content": raw_response},
        {"role": "user", "content": f"[Résultat de l'outil {tool_name}] : {result}\n"
                                     "Formule une réponse claire pour l'utilisateur."}
    ]
    final_answer = router.call_model(follow_up)
    mem.add_message("assistant", final_answer)
    return final_answer


PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gaïrus</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/icon-192.png">
<link rel="apple-touch-icon" href="/icon-192.png">
<meta name="theme-color" content="#161a22">
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, sans-serif; margin: 0; background:#0f1115; color:#eee; }
  header { padding: 14px 16px; background:#161a22; font-weight:600; border-bottom:1px solid #262b36; }
  #chat { padding: 12px; display:flex; flex-direction:column; gap:10px;
          height: calc(100vh - 130px); overflow-y:auto; }
  .msg { padding: 10px 14px; border-radius: 14px; max-width: 85%; white-space:pre-wrap; line-height:1.4; }
  .user { align-self:flex-end; background:#2d6cdf; color:white; }
  .bot  { align-self:flex-start; background:#1e222b; border:1px solid #2b303c; }
  form { display:flex; gap:8px; padding:12px; border-top:1px solid #262b36; background:#161a22; }
  input { flex:1; padding:12px 14px; border-radius:10px; border:1px solid #2b303c; background:#0f1115; color:#eee; font-size:16px; }
  button { padding:0 18px; border-radius:10px; border:none; background:#2d6cdf; color:white; font-size:16px; }
</style>
</head>
<body>
<header>🧠 GAÏRUS — Phase 1</header>
<div id="chat"></div>
<form id="f">
  <input id="i" autocomplete="off" placeholder="Écris à Gaïrus..." />
  <button type="submit">Envoyer</button>
</form>
<script>
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}
const chat = document.getElementById('chat');
const form = document.getElementById('f');
const input = document.getElementById('i');

function addMsg(text, cls) {
  const d = document.createElement('div');
  d.className = 'msg ' + cls;
  d.textContent = text;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  addMsg(text, 'user');
  input.value = '';
  addMsg('...', 'bot');
  const thinking = chat.lastChild;
  try {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await r.json();
    thinking.textContent = data.reply;
  } catch (err) {
    thinking.textContent = 'Erreur de connexion à Gaïrus.';
  }
});
</script>
</body>
</html>
"""


@app.route("/")
def home():
    return Response(PAGE, mimetype="text/html")


@app.route("/manifest.json")
def manifest():
    return jsonify(MANIFEST)


@app.route("/sw.js")
def service_worker():
    return Response(SERVICE_WORKER, mimetype="application/javascript")


@app.route("/icon-192.png")
def icon_192():
    return Response(_ICON_192, mimetype="image/png")


@app.route("/icon-512.png")
def icon_512():
    return Response(_ICON_512, mimetype="image/png")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(force=True)
    user_input = (data or {}).get("message", "").strip()
    if not user_input:
        return jsonify({"reply": "Message vide."})
    reply = handle_message(user_input)
    return jsonify({"reply": reply})


if __name__ == "__main__":
    print("Gaïrus web est prêt : ouvre http://127.0.0.1:8080 dans ton navigateur")
    app.run(host="127.0.0.1", port=8080)
