"""
GAÏRUS ↔ SLACK

Slack devient une interface de mission pour Gaïrus.

Sécurité :
- vérification de la signature Slack
- aucun secret dans les messages
- les actions sensibles peuvent être placées en approbation
- les clés restent dans l'environnement de l'instance
"""

import os
import hmac
import hashlib
import time
import threading
from slack_memory import (
    remember_event,
    build_context,
    build_zyrvion_context,
    start_background_sync,
)

from queue import Queue

_GAIRUS_MISSION_QUEUE = Queue()

# Une seule mission autonome SQLite à la fois.
_MISSION_LOCK = threading.Lock()
import requests
from dotenv import load_dotenv
load_dotenv()

from flask import Blueprint, request, jsonify

try:
    from slack_bolt import App as SlackBoltApp
    from slack_bolt.adapter.socket_mode import SocketModeHandler
except ImportError:
    SlackBoltApp = None
    SocketModeHandler = None


slack_bp = Blueprint("gairus_slack", __name__, url_prefix="/api/slack")


def _signing_secret():
    return os.getenv("SLACK_SIGNING_SECRET", "").strip()


def verify_slack_request(req):
    secret = _signing_secret()

    if not secret:
        return False

    timestamp = req.headers.get("X-Slack-Request-Timestamp", "")
    signature = req.headers.get("X-Slack-Signature", "")

    if not timestamp or not signature:
        return False

    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False

    body = req.get_data(as_text=True)
    base = f"v0:{timestamp}:{body}"

    expected = "v0=" + hmac.new(
        secret.encode(),
        base.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def slack_api(method, payload):
    token = os.getenv("SLACK_BOT_TOKEN", "").strip()

    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN absent")

    response = requests.post(
        f"https://slack.com/api/{method}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json=payload,
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(data.get("error", "Erreur Slack"))

    return data


def send_message(channel, text_value, thread_ts=None):
    payload = {
        "channel": channel,
        "text": text_value,
    }

    if thread_ts:
        payload["thread_ts"] = thread_ts

    return slack_api("chat.postMessage", payload)


def _run_mission_async(objective, channel, thread_ts=None):
    """
    Exécute une mission Slack dans le même moteur pour :
    - DM
    - channels
    - threads
    - mentions
    """
    try:
        # Le contexte mémoire est construit hors du listener Slack.
        try:
            slack_context = build_zyrvion_context(
                objective,
                channel_id=channel,
            )

            if slack_context:
                objective = (
                    f"{objective}\n\n"
                    f"{slack_context}"
                )
        except Exception as context_exc:
            print(
                f"[GAIRUS][SLACK] Contexte mémoire indisponible : {context_exc}",
                flush=True,
            )

        from autonomy import create_autonomous_mission, autonomous_mission_cycle

        mission_id = create_autonomous_mission(objective)

        if not mission_id:
            send_message(
                channel,
                "Je n'ai pas pu lancer cette demande.",
                thread_ts,
            )
            return

        result = None

        for attempt in range(4):
            try:
                result = autonomous_mission_cycle(mission_id)

                if (
                    isinstance(result, dict)
                    and "database is locked" in str(
                        result.get("error", "")
                    ).lower()
                    and attempt < 3
                ):
                    time.sleep(2 ** attempt)
                    continue

                break

            except Exception as exc:
                if (
                    "database is locked" in str(exc).lower()
                    and attempt < 3
                ):
                    time.sleep(2 ** attempt)
                    continue
                raise

        if isinstance(result, dict):
            if result.get("ok"):
                reply = str(result.get("reply") or "").strip()

                if reply:
                    send_message(channel, reply, thread_ts)
                else:
                    send_message(
                        channel,
                        "Mission terminée.",
                        thread_ts,
                    )
                return

            error = str(
                result.get("error")
                or "Je n'ai pas pu terminer cette demande."
            ).strip()

            send_message(
                channel,
                f"⚠️ {error}",
                thread_ts,
            )
            return

        reply = str(result or "").strip()

        if reply:
            send_message(channel, reply, thread_ts)
        else:
            send_message(
                channel,
                "Mission terminée.",
                thread_ts,
            )

    except Exception as exc:
        try:
            send_message(
                channel,
                f"⚠️ Je n'ai pas pu terminer cette demande : {exc}",
                thread_ts,
            )
        except Exception:
            pass


def _gairus_mission_worker():
    """
    Worker Slack non bloquant.
    Chaque mission est déléguée à son propre thread afin qu'une mission
    longue ou bloquée ne puisse empêcher les messages Slack suivants.
    """
    while True:
        objective, channel, thread_ts = _GAIRUS_MISSION_QUEUE.get()

        try:
            threading.Thread(
                target=_run_mission_async,
                args=(objective, channel, thread_ts),
                name="gairus-mission-execution",
                daemon=True,
            ).start()
        except Exception as exc:
            print(
                f"[GAIRUS][SLACK] Impossible de lancer la mission : {exc}",
                flush=True,
            )
        finally:
            _GAIRUS_MISSION_QUEUE.task_done()


def start_mission(objective, channel, thread_ts=None):
    """
    Met une mission en file sans effectuer de travail bloquant dans le
    handler Slack.
    """
    objective = str(objective or "").strip()

    if not objective or not channel:
        return False

    _GAIRUS_MISSION_QUEUE.put(
        (objective, channel, thread_ts)
    )

    return True


if not any(
    t.name == "gairus-mission-worker"
    for t in threading.enumerate()
):
    threading.Thread(
        target=_gairus_mission_worker,
        name="gairus-mission-worker",
        daemon=True,
    ).start()


@slack_bp.route("/events", methods=["POST"])
def slack_events():
    if not verify_slack_request(request):
        return jsonify({"ok": False, "error": "signature_invalid"}), 401

    data = request.get_json(silent=True) or {}

    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge", "")})

    event = data.get("event", {})

    if event.get("type") == "app_mention":
        text_value = event.get("text", "")
        channel = event.get("channel")
        ts = event.get("ts")

        # Retire la mention Slack.
        objective = text_value
        if ">" in objective:
            objective = objective.split(">", 1)[1]

        objective = objective.strip()

        if objective:
            start_mission(objective, channel, ts)

        return jsonify({"ok": True})

    return jsonify({"ok": True})


@slack_bp.route("/commands", methods=["POST"])
def slack_command():
    if not verify_slack_request(request):
        return jsonify({"ok": False, "error": "signature_invalid"}), 401

    command = request.form.get("command", "")
    text_value = request.form.get("text", "").strip()
    channel = request.form.get("channel_id", "")
    response_url = request.form.get("response_url", "")

    if command == "/gairus":
        if not text_value:
            return jsonify({
                "response_type": "ephemeral",
                "text": "Utilisation : `/gairus fais quelque chose`",
            })

        # Accusé immédiat.
        if response_url:
            try:
                requests.post(
                    response_url,
                    json={
                        "response_type": "in_channel",
                        "text": "Bien reçu.",
                    },
                    timeout=10,
                )
            except Exception:
                pass

        start_mission(text_value, channel)
        return "", 200

    return jsonify({"ok": True})


# === GAIRUS_SLACK_SOCKET_MODE ===

_socket_handler_started = False
_socket_thread = None
_socket_error = None


def start_slack_socket_mode():
    """
    Démarre l'écoute Slack en Socket Mode.
    L'endpoint HTTP /events reste également disponible.
    """
    global _socket_handler_started, _socket_thread, _socket_error

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    if _socket_handler_started:
        return

    app_token = os.getenv("SLACK_APP_TOKEN", "").strip()
    bot_token = os.getenv("SLACK_BOT_TOKEN", "").strip()

    if not app_token or not bot_token:
        print("[GAIRUS][SLACK] Socket Mode non démarré : token manquant")
        return

    if SlackBoltApp is None or SocketModeHandler is None:
        print("[GAIRUS][SLACK] slack-bolt indisponible")
        return

    try:
        bolt_app = SlackBoltApp(token=bot_token)

        @bolt_app.event("message")
        def handle_message_events(body, event, say, logger):
            try:
                if event.get("bot_id") or event.get("subtype"):
                    return

                # Les messages de canaux sont gérés par app_mention.
                # Ici on ne traite que les conversations directes.
                if event.get("channel_type") not in ("im", "mpim"):
                    return

                text_value = event.get("text", "").strip()
                channel = event.get("channel")
                ts = event.get("ts")

                if not text_value or not channel:
                    return


                normalized = text_value.lower().strip()

                if normalized in {
                    "tu es là",
                    "tu es la",
                    "tu es là ?",
                    "tu es la ?",
                    "tu es là?",
                    "tu es la?",
                    "gaïrus",
                    "gairus",
                }:
                    say(
                        text="Oui, je suis là. Que veux-tu que je fasse ?",
                        thread_ts=ts,
                    )
                    return

                say(
                    text="Bien reçu.",
                    thread_ts=ts,
                )


                start_mission(text_value, channel, ts)

            except Exception as exc:
                logger.exception("[GAIRUS][SLACK] Erreur message")
                try:
                    say(
                        text=f"⚠️ Erreur Gaïrus : `{exc}`",
                        thread_ts=event.get("ts"),
                    )
                except Exception:
                    pass

        @bolt_app.event("app_mention")
        def handle_app_mention(body, event, say, logger):
            try:
                text_value = event.get("text", "")
                channel = event.get("channel")
                ts = event.get("ts")

                objective = text_value

                # Retire la mention du bot.
                if ">" in objective:
                    objective = objective.split(">", 1)[1]

                objective = objective.strip()

                if not objective:
                    say(
                        text="Je suis là. Donne-moi simplement la mission à accomplir.",
                        thread_ts=ts,
                    )
                    return

                say(
                    text="Bien reçu.",
                    thread_ts=ts,
                )

                start_mission(objective, channel, ts)

            except Exception as exc:
                logger.exception("[GAIRUS][SLACK] Erreur app_mention")
                try:
                    say(
                        text=f"⚠️ Erreur Gaïrus : `{exc}`",
                        thread_ts=event.get("ts"),
                    )
                except Exception:
                    pass

        @bolt_app.command("/gairus")
        def handle_gairus_command(ack, command, respond, logger):
            ack()

            try:
                text_value = (command.get("text") or "").strip()
                channel = command.get("channel_id", "")

                if not text_value:
                    respond(
                        response_type="ephemeral",
                        text="Utilisation : `/gairus fais quelque chose`",
                    )
                    return

                respond(
                    response_type="in_channel",
                    text="Bien reçu.",
                )

                start_mission(text_value, channel)

            except Exception as exc:
                logger.exception("[GAIRUS][SLACK] Erreur commande")
                try:
                    respond(
                        response_type="ephemeral",
                        text=f"⚠️ Erreur Gaïrus : `{exc}`",
                    )
                except Exception:
                    pass

        handler = SocketModeHandler(bolt_app, app_token)

        def _run():
            global _socket_error

            while True:
                try:
                    print("[GAIRUS][SLACK] Socket Mode démarrage...")
                    print("[GAIRUS][SLACK] Connexion WebSocket Slack...")
                    handler.connect()
                    print("[GAIRUS][SLACK] Socket Mode connecté")
                    _socket_error = None
                    while True:
                        time.sleep(30)
                        if not handler.client.is_connected():
                            print("[GAIRUS][SLACK] Connexion perdue, reconnexion...")
                            break
                except Exception as exc:
                    _socket_error = f"{type(exc).__name__}: {exc}"
                    print(f"[GAIRUS][SLACK] Socket Mode arrêté : {_socket_error}")
                    import traceback
                    traceback.print_exc()

                time.sleep(5)

        thread = threading.Thread(
            target=_run,
            name="gairus-slack-socket",
            daemon=True,
        )
        _socket_thread = thread
        thread.start()

        _socket_handler_started = True
        print("[GAIRUS][SLACK] Socket Mode activé")

    except Exception as exc:
        print(f"[GAIRUS][SLACK] Impossible de démarrer Socket Mode : {exc}")


# === END GAIRUS_SLACK_SOCKET_MODE ===

# === GAIRUS_SLACK_HEALTH ===
@slack_bp.get("/health")
def slack_health():
    import os

    return {
        "ok": True,
        "slack_configured": bool(
            os.getenv("SLACK_BOT_TOKEN", "").strip()
            and os.getenv("SLACK_SIGNING_SECRET", "").strip()
        ),
        "bot_token": bool(os.getenv("SLACK_BOT_TOKEN", "").strip()),
        "signing_secret": bool(os.getenv("SLACK_SIGNING_SECRET", "").strip()),
        "app_token": bool(os.getenv("SLACK_APP_TOKEN", "").strip()),
        "events_endpoint": "/api/slack/events",
        "commands_endpoint": "/api/slack/commands",
        "socket_mode_started": _socket_handler_started,
        "socket_thread_alive": bool(
            _socket_thread and _socket_thread.is_alive()
        ),
        "socket_error": _socket_error
    }

# === END GAIRUS_SLACK_HEALTH ===


# === GAIRUS_AGENT_BRIDGE ===

try:
    from core.slack_agent_bridge import SlackAgentBridge
    from core.final_operations_runtime import get_operations_gairus

    _gairus_bridge = None

    def _get_gairus_bridge():
        global _gairus_bridge

        if _gairus_bridge is None:
            agent = get_operations_gairus()

            integration = getattr(
                getattr(agent, "runtime", None),
                "slack",
                None,
            )

            _gairus_bridge = SlackAgentBridge(
                agent=agent,
                integration=integration,
            )

        return _gairus_bridge

except Exception:
    SlackAgentBridge = None
    _gairus_bridge = None

    def _get_gairus_bridge():
        return None


def process_gairus_slack_message(
    text,
    user_id=None,
    channel_id=None,
    team_id=None,
):
    bridge = _get_gairus_bridge()

    if bridge is None:
        return {
            "ok": False,
            "error": "gairus_bridge_unavailable",
        }

    return bridge.handle_event(
        {
            "text": text,
            "user_id": user_id,
            "channel_id": channel_id,
            "team_id": team_id,
        }
    )


# === END GAIRUS_AGENT_BRIDGE ===



# ============================================================
# GAÏRUS : mémoire Slack persistante
# ============================================================
try:
    start_background_sync()
except Exception:
    pass
