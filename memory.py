"""
GAÏRUS — Mémoire persistante (Section 13 / 14 / 40, version scaffold)
Stocke : messages, actions d'outils, résultats.
Ne stocke JAMAIS de mots de passe / tokens / clés (Section 13, 44).
"""
import sqlite3
import threading
import time
import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,        -- 'user' | 'assistant' | 'tool'
    content TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool TEXT NOT NULL,
    params TEXT NOT NULL,
    result TEXT,
    status TEXT NOT NULL,      -- 'ok' | 'error' | 'refused'
    created_at REAL NOT NULL
);
"""


class Memory:
    def __init__(self, db_path: str = config.DB_PATH):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self.conn.executescript(_SCHEMA)
            self.conn.commit()

    def add_message(self, role: str, content: str):
        with self._lock:
            self.conn.execute(
                "INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)",
                (role, content, time.time()),
            )
            self.conn.commit()

    def recent_messages(self, limit: int = 20):
        with self._lock:
            cur = self.conn.execute(
                "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
        rows.reverse()
        return [{"role": r, "content": c} for r, c in rows]

    def log_action(self, tool: str, params: str, result: str, status: str):
        with self._lock:
            self.conn.execute(
                "INSERT INTO agent_actions (tool, params, result, status, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (tool, params, result, status, time.time()),
            )
            self.conn.commit()
