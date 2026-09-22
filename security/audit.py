from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    """
    Journal d'audit Enterprise append-only.

    Chaque événement conserve :
      - timestamp UTC
      - acteur
      - département
      - action
      - outil
      - montant éventuel
      - gouvernance
      - approbation
      - résultat
      - erreur éventuelle
      - métadonnées
    """

    def __init__(self, path=None):
        self.path = Path(
            path
            or os.getenv(
                "GAIRUS_AUDIT_LOG",
                "data/audit_enterprise.jsonl",
            )
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    @staticmethod
    def _timestamp():
        return datetime.now(timezone.utc).isoformat()

    def log(
        self,
        *,
        event="action",
        actor_id=None,
        actor_name=None,
        actor_level=None,
        department_id=None,
        department_name=None,
        action=None,
        tool=None,
        amount=None,
        status=None,
        authorization=None,
        approval=None,
        result=None,
        error=None,
        mission_id=None,
        metadata=None,
    ):
        record = {
            "timestamp": self._timestamp(),
            "event": event,
            "actor": {
                "id": actor_id,
                "name": actor_name,
                "level": actor_level,
            },
            "department": {
                "id": department_id,
                "name": department_name,
            },
            "action": action,
            "tool": tool,
            "amount": amount,
            "status": status,
            "authorization": authorization,
            "approval": approval,
            "mission_id": mission_id,
            "result": result,
            "error": error,
            "metadata": metadata or {},
        }

        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\n"
                )

        return record

    def read(self, limit=100):
        if not self.path.exists():
            return []

        records = []

        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return records[-int(limit):]

    def search(
        self,
        *,
        actor_id=None,
        action=None,
        status=None,
        tool=None,
        mission_id=None,
        limit=100,
    ):
        records = self.read(limit=100000)

        def match(r):
            if actor_id is not None:
                if r.get("actor", {}).get("id") != actor_id:
                    return False

            if action is not None and r.get("action") != action:
                return False

            if status is not None and r.get("status") != status:
                return False

            if tool is not None and r.get("tool") != tool:
                return False

            if mission_id is not None and r.get("mission_id") != mission_id:
                return False

            return True

        return [r for r in records if match(r)][-int(limit):]


_default_audit = None


def get_audit_logger():
    global _default_audit

    if _default_audit is None:
        _default_audit = AuditLogger()

    return _default_audit


def audit(**kwargs):
    return get_audit_logger().log(**kwargs)
