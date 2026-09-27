import time
import traceback

import slack_gateway


CHECK_INTERVAL = 10


def reset_dead_socket():
    """
    Réinitialise l'état interne de Socket Mode lorsqu'un thread
    de connexion est mort. Cela permet à start_slack_socket_mode()
    de recréer une connexion.
    """
    slack_gateway._socket_handler_started = False
    slack_gateway._socket_thread = None


print("[GAIRUS][SLACK WORKER] Démarrage du superviseur Slack...", flush=True)

while True:
    try:
        slack_gateway.start_slack_socket_mode()

        thread = getattr(slack_gateway, "_socket_thread", None)

        if thread is None:
            print(
                "[GAIRUS][SLACK WORKER] Socket Mode non actif. "
                "Nouvelle tentative dans 10 secondes.",
                flush=True,
            )
            time.sleep(CHECK_INTERVAL)
            continue

        if not thread.is_alive():
            print(
                "[GAIRUS][SLACK WORKER] Thread Socket Mode arrêté. "
                "Réinitialisation et reconnexion...",
                flush=True,
            )
            reset_dead_socket()
            time.sleep(2)
            continue

        time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print(
            "[GAIRUS][SLACK WORKER] Arrêt demandé.",
            flush=True,
        )
        break

    except Exception as exc:
        print(
            f"[GAIRUS][SLACK WORKER] Exception superviseur : "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        traceback.print_exc()

        reset_dead_socket()

        time.sleep(5)
