#!/bin/sh
set -e

python slack_worker.py &
SLACK_PID=$!

trap 'kill "$SLACK_PID" 2>/dev/null || true' EXIT TERM INT

exec gunicorn app:app --workers=1 --bind 0.0.0.0:$PORT
