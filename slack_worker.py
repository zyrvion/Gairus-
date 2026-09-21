from slack_gateway import start_slack_socket_mode
import time

print("[GAIRUS][SLACK WORKER] Démarrage...", flush=True)
start_slack_socket_mode()

while True:
    time.sleep(60)
