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
import requests

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


def _run_mission_async(objective, channel, thread_ts):
    try:
        from autonomy import create_autonomous_mission
        from autonomy import autonomous_mission_cycle

        mission = create_autonomous_mission(
            objective=objective,
            title=f"Mission Slack: {objective[:80]}",
        )

        mission_id = mission.get("mission_id")

        if not mission_id:
            send_message(
                channel,
                "❌ Gaïrus n'a pas pu créer la mission.",
                thread_ts,
            )
            return

        send_message(
            channel,
            f"🧠 Mission créée : `{mission_id}`\n"
            f"Je commence le travail sur : {objective}",
            thread_ts,
        )

        result = autonomous_mission_cycle(mission_id)

        send_message(
            channel,
            "✅ Cycle Gaïrus terminé.\n\n"
            f"```{str(result)[:5000]}```",
            thread_ts,
        )

    except Exception as exc:
        try:
            send_message(
                channel,
                f"⚠️ Erreur pendant la mission : `{exc}`",
                thread_ts,
            )
        except Exception:
            pass


def start_mission(objective, channel, thread_ts=None):
    thread = threading.Thread(
        target=_run_mission_async,
        args=(objective, channel, thread_ts),
        daemon=True,
    )
    thread.start()


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
                        "text": f"🧠 Gaïrus reçoit : {text_value}",
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


def start_slack_socket_mode():
    """
    Démarre l'écoute Slack en Socket Mode.
    L'endpoint HTTP /events reste également disponible.
    """
    global _socket_handler_started, _socket_thread

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
                    text=f"🧠 Gaïrus reçoit : {objective}",
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
                    text=f"🧠 Gaïrus reçoit : {text_value}",
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
            try:
                print("[GAIRUS][SLACK] Socket Mode démarrage...")
                print("[GAIRUS][SLACK] Connexion WebSocket Slack...")
                handler.start()
            except Exception as exc:
                print(f"[GAIRUS][SLACK] Socket Mode arrêté : {exc}")
                import traceback
                traceback.print_exc()

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
        )
    }

# === END GAIRUS_SLACK_HEALTH ===
