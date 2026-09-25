import os
import re
import time
import sqlite3
import threading
import requests
from pathlib import Path

# ============================================================
# GAÏRUS SLACK MEMORY
# Mémoire persistante du projet, des channels et des conversations.
# Base séparée pour ne jamais bloquer la base des missions.
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
MEMORY_DB = str(BASE_DIR / "slack_memory.db")

SLACK_TOKEN = (
    os.getenv("SLACK_BOT_TOKEN")
    or os.getenv("SLACK_TOKEN")
    or ""
).strip()

SLACK_API = "https://slack.com/api"

_MEMORY_LOCK = threading.RLock()
_SYNC_LOCK = threading.Lock()


def _db():
    conn = sqlite3.connect(
        MEMORY_DB,
        timeout=60,
        check_same_thread=False,
    )
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS slack_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            channel_name TEXT,
            user_id TEXT,
            ts TEXT NOT NULL,
            thread_ts TEXT,
            text TEXT NOT NULL,
            subtype TEXT,
            indexed_at REAL NOT NULL,
            UNIQUE(channel_id, ts)
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_slack_messages_channel
        ON slack_messages(channel_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_slack_messages_ts
        ON slack_messages(ts)
    """)

    conn.commit()
    return conn


def _slack(method, **params):
    if not SLACK_TOKEN:
        return {
            "ok": False,
            "error": "SLACK_BOT_TOKEN absent",
        }

    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    for attempt in range(5):
        try:
            response = requests.post(
                f"{SLACK_API}/{method}",
                headers=headers,
                data=params,
                timeout=45,
            )

            if response.status_code == 429:
                retry_after = int(
                    response.headers.get("Retry-After", "5")
                )
                time.sleep(max(1, retry_after))
                continue

            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                return data

            if data.get("error") == "ratelimited":
                time.sleep(5)
                continue

            return data

        except Exception as exc:
            if attempt >= 4:
                return {
                    "ok": False,
                    "error": str(exc),
                }
            time.sleep(2 ** attempt)

    return {
        "ok": False,
        "error": "Slack API indisponible",
    }


def _clean(text):
    text = str(text or "")
    text = re.sub(r"<@[^>]+>", " ", text)
    text = re.sub(r"<#[A-Z0-9]+\|([^>]+)>", r"\1", text)
    text = re.sub(r"<([^>|]+)\|([^>]+)>", r"\2", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remember_message(
    channel_id,
    channel_name,
    user_id,
    ts,
    text,
    thread_ts=None,
    subtype=None,
):
    text = _clean(text)

    if not channel_id or not ts or not text:
        return

    with _MEMORY_LOCK:
        conn = _db()
        try:
            conn.execute(
                """
                INSERT INTO slack_messages
                (
                    channel_id,
                    channel_name,
                    user_id,
                    ts,
                    thread_ts,
                    text,
                    subtype,
                    indexed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id, ts)
                DO UPDATE SET
                    channel_name=excluded.channel_name,
                    user_id=excluded.user_id,
                    thread_ts=excluded.thread_ts,
                    text=excluded.text,
                    subtype=excluded.subtype,
                    indexed_at=excluded.indexed_at
                """,
                (
                    channel_id,
                    channel_name or "",
                    user_id or "",
                    ts,
                    thread_ts or "",
                    text,
                    subtype or "",
                    time.time(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def _index_messages(channel, messages):
    channel_id = channel.get("id")
    channel_name = channel.get("name") or channel.get("user") or ""

    count = 0

    for message in messages or []:
        text = message.get("text", "")

        if not text:
            continue

        remember_message(
            channel_id=channel_id,
            channel_name=channel_name,
            user_id=message.get("user"),
            ts=message.get("ts"),
            thread_ts=message.get("thread_ts"),
            text=text,
            subtype=message.get("subtype"),
        )

        count += 1

    return count


def list_conversations():
    conversations = []
    cursor = ""

    while True:
        params = {
            "types": "public_channel,private_channel,mpim,im",
            "limit": "100",
        }

        if cursor:
            params["cursor"] = cursor

        data = _slack("conversations.list", **params)

        if not data.get("ok"):
            break

        conversations.extend(data.get("channels", []))

        cursor = (
            data.get("response_metadata", {})
            .get("next_cursor", "")
            .strip()
        )

        if not cursor:
            break

    return conversations


def sync_channel(channel):
    channel_id = channel.get("id")
    if not channel_id:
        return 0

    total = 0
    cursor = ""

    # On récupère l'historique accessible au bot.
    for _ in range(20):
        params = {
            "channel": channel_id,
            "limit": "100",
        }

        if cursor:
            params["cursor"] = cursor

        data = _slack("conversations.history", **params)

        if not data.get("ok"):
            break

        messages = data.get("messages", [])
        total += _index_messages(channel, messages)

        # Les réponses de threads sont également indexées.
        for parent in messages:
            if not parent.get("reply_count"):
                continue

            thread_ts = parent.get("ts")
            if not thread_ts:
                continue

            replies = _slack(
                "conversations.replies",
                channel=channel_id,
                ts=thread_ts,
                limit="100",
            )

            if replies.get("ok"):
                total += _index_messages(
                    channel,
                    replies.get("messages", []),
                )

        cursor = (
            data.get("response_metadata", {})
            .get("next_cursor", "")
            .strip()
        )

        if not cursor:
            break

    return total


def sync_all():
    if not _SYNC_LOCK.acquire(blocking=False):
        return {
            "ok": False,
            "error": "Synchronisation déjà en cours",
        }

    try:
        if not SLACK_TOKEN:
            return {
                "ok": False,
                "error": "SLACK_BOT_TOKEN absent",
            }

        channels = list_conversations()
        total = 0
        accessible = 0

        for channel in channels:
            try:
                count = sync_channel(channel)
                total += count
                accessible += 1
            except Exception:
                continue

        return {
            "ok": True,
            "channels": accessible,
            "messages": total,
        }

    finally:
        _SYNC_LOCK.release()


def search_memory(query, channel_id=None, limit=12):
    query = _clean(query).lower()

    if not query:
        return []

    words = [
        w for w in re.findall(r"[a-zA-ZÀ-ÿ0-9_'-]+", query)
        if len(w) >= 3
    ]

    if not words:
        return []

    with _MEMORY_LOCK:
        conn = _db()

        try:
            rows = conn.execute(
                """
                SELECT
                    channel_id,
                    channel_name,
                    user_id,
                    ts,
                    thread_ts,
                    text
                FROM slack_messages
                ORDER BY CAST(ts AS REAL) DESC
                LIMIT 5000
                """
            ).fetchall()
        finally:
            conn.close()

    scored = []

    for row in rows:
        (
            row_channel,
            channel_name,
            user_id,
            ts,
            thread_ts,
            text,
        ) = row

        if channel_id and row_channel != channel_id:
            continue

        haystack = (
            f"{channel_name} {text}"
        ).lower()

        score = 0

        for word in words:
            if word in haystack:
                score += 1

        if query in haystack:
            score += 5

        # Les termes projet/Sylvian gagnent du poids.
        important = (
            "sylvian",
            "sylvia",
            "zyrvion",
            "gairus",
            "gaïrus",
            "projet",
            "architecture",
            "code",
            "slack",
        )

        for term in important:
            if term in query and term in haystack:
                score += 3

        if score:
            scored.append(
                (
                    score,
                    {
                        "channel_id": row_channel,
                        "channel": channel_name,
                        "user": user_id,
                        "ts": ts,
                        "thread_ts": thread_ts,
                        "text": text,
                    },
                )
            )

    scored.sort(
        key=lambda item: (
            item[0],
            float(item[1]["ts"] or 0),
        ),
        reverse=True,
    )

    return [
        item[1]
        for item in scored[:limit]
    ]


def build_context(query, channel_id=None, limit=12):
    results = search_memory(
        query,
        channel_id=channel_id,
        limit=limit,
    )

    if not results:
        return ""

    lines = [
        "CONTEXTE SLACK PERTINENT",
        "Utilise ces éléments comme mémoire de projet. "
        "Ne prétends pas connaître une information absente.",
        "",
    ]

    for item in results:
        channel = item.get("channel") or item.get("channel_id")
        text = item.get("text") or ""

        lines.append(
            f"[#{channel}] {text}"
        )

    return "\n".join(lines)


def remember_event(event):
    if not isinstance(event, dict):
        return

    channel_id = event.get("channel")
    ts = event.get("ts")

    if not channel_id or not ts:
        return

    remember_message(
        channel_id=channel_id,
        channel_name="",
        user_id=event.get("user"),
        ts=ts,
        thread_ts=event.get("thread_ts"),
        text=event.get("text", ""),
        subtype=event.get("subtype"),
    )


def start_background_sync():
    def worker():
        # Laisse Slack Gateway finir son initialisation.
        time.sleep(15)

        while True:
            try:
                sync_all()
            except Exception:
                pass

            # Synchronisation périodique.
            time.sleep(
                int(
                    os.getenv(
                        "GAIRUS_SLACK_MEMORY_INTERVAL",
                        "900",
                    )
                )
            )

    thread = threading.Thread(
        target=worker,
        name="gairus-slack-memory",
        daemon=True,
    )
    thread.start()


# Recherche rapide depuis n'importe quel module.
__all__ = [
    "remember_message",
    "remember_event",
    "search_memory",
    "build_context",
    "sync_all",
    "start_background_sync",
]
