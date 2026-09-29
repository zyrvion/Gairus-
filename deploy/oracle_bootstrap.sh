#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/opt/gairus"
REPO="https://github.com/zyrvion/Gairus-.git"

echo "[GAIRUS] Installation de la base serveur..."

if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y git curl ca-certificates
fi

if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sudo sh
fi

sudo systemctl enable docker || true
sudo systemctl start docker || true

sudo mkdir -p "$APP_DIR"

if [ ! -d "$APP_DIR/.git" ]; then
    sudo git clone --branch main "$REPO" "$APP_DIR"
else
    cd "$APP_DIR"
    sudo git fetch origin main
    sudo git reset --hard origin/main
fi

cd "$APP_DIR"

if [ ! -f .env ]; then
    sudo cp .env.example .env
    echo
    echo "ATTENTION: /opt/gairus/.env doit être rempli avec les secrets"
    echo "avant le premier démarrage."
fi

sudo docker compose up -d --build
sudo docker compose ps

echo "[GAIRUS] Bootstrap terminé."
