"""
GAÏRUS ONBOARDING

Gestion des inscriptions de fournisseurs.

Important :
Gaïrus peut préparer, suivre et tester les intégrations.
Les étapes nécessitant explicitement une validation humaine
(email de confirmation, 2FA, CAPTCHA, conditions d'utilisation,
paiement, etc.) sont présentées comme une action à valider.

Aucune clé secrète n'est envoyée dans Slack.
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime


DATA_DIR = Path(
    os.getenv("GAIRUS_DATA_DIR", "./data")
).resolve()

DB_PATH = DATA_DIR / "gairus.db"


def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_onboarding():
    with _connect() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS provider_onboarding (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id TEXT NOT NULL,
            status TEXT NOT NULL,
            email_hint TEXT,
            requires_human INTEGER DEFAULT 1,
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        db.commit()


def create_onboarding(provider_id, email_hint=None):
    now = datetime.utcnow().isoformat()

    with _connect() as db:
        cur = db.execute(
            """
            INSERT INTO provider_onboarding
            (provider_id, status, email_hint, requires_human,
             metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider_id,
                "pending",
                email_hint,
                1,
                json.dumps({}),
                now,
                now,
            ),
        )
        db.commit()
        return cur.lastrowid


def list_onboarding():
    with _connect() as db:
        rows = db.execute(
            "SELECT * FROM provider_onboarding ORDER BY id DESC"
        ).fetchall()

    return [dict(row) for row in rows]


init_onboarding()
