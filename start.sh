#!/usr/bin/env bash
set -Eeuo pipefail
: "${PORT:=10000}"
echo "[GAIRUS][BOOT] Démarrage sur le port ${PORT}."
pids=()
cleanup() {
    trap - EXIT TERM INT
    for pid in "${pids[@]}"; do kill -TERM "$pid" 2>/dev/null || true; done
    wait || true
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
if [[ -n "${SLACK_BOT_TOKEN:-}" && -n "${SLACK_APP_TOKEN:-}" ]]; then
    python slack_worker.py &
    pids+=("$!")
    echo "[GAIRUS][BOOT] Superviseur Slack démarré."
else
    echo "[GAIRUS][BOOT] Slack non configuré : aucun worker démarré."
fi
gunicorn --config gunicorn.conf.py --workers 1 --threads 4 \
    --timeout 120 --bind "0.0.0.0:${PORT}" app:app &
pids+=("$!")
set +e
wait -n "${pids[@]}"
status=$?
set -e
exit "$status"
