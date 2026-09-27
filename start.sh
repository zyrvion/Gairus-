#!/bin/sh

set -u

echo "[GAIRUS][BOOT] Démarrage de Gaïrus..." >&2

SLACK_PID=""
GUNICORN_PID=""

cleanup() {
    echo "[GAIRUS][BOOT] Arrêt des processus..." >&2

    if [ -n "$SLACK_PID" ]; then
        kill "$SLACK_PID" 2>/dev/null || true
    fi

    if [ -n "$GUNICORN_PID" ]; then
        kill "$GUNICORN_PID" 2>/dev/null || true
    fi

    wait "$SLACK_PID" 2>/dev/null || true
    wait "$GUNICORN_PID" 2>/dev/null || true
}

trap cleanup EXIT TERM INT

start_slack() {
    echo "[GAIRUS][BOOT] Démarrage du superviseur Slack..." >&2
    python slack_worker.py &
    SLACK_PID=$!
    echo "[GAIRUS][BOOT] Slack PID=$SLACK_PID" >&2
}

start_gunicorn() {
    echo "[GAIRUS][BOOT] Démarrage de Gunicorn..." >&2

    gunicorn app:app \
        --workers=1 \
        --bind "0.0.0.0:${PORT}" &

    GUNICORN_PID=$!

    echo "[GAIRUS][BOOT] Gunicorn PID=$GUNICORN_PID" >&2
}

start_slack
start_gunicorn

while true
do
    if ! kill -0 "$GUNICORN_PID" 2>/dev/null; then
        echo "[GAIRUS][BOOT] Gunicorn arrêté. Arrêt du service." >&2
        exit 1
    fi

    if ! kill -0 "$SLACK_PID" 2>/dev/null; then
        echo "[GAIRUS][BOOT] Worker Slack arrêté. Redémarrage..." >&2

        start_slack
    fi

    sleep 5
done
