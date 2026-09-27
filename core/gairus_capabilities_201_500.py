from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "gairus_capabilities_201_500.db"


@dataclass
class Capability201500:
    id: int
    name: str
    domain: str
    description: str
    approval_required: bool = False
    enabled: bool = True
    handler: str = "generic"


class GairusCapabilities201500:

    def __init__(self, runtime: Any = None):
        self.runtime = runtime
        self.capabilities: Dict[int, Capability201500] = {}
        self.handlers: Dict[str, Callable[..., Any]] = {}
        self._init_db()
        self._register_all()

    def _connect(self):
        return sqlite3.connect(str(DB_PATH))

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS capabilities (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    description TEXT NOT NULL,
                    approval_required INTEGER DEFAULT 0,
                    enabled INTEGER DEFAULT 1,
                    handler TEXT DEFAULT 'generic'
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    capability_id INTEGER,
                    payload TEXT,
                    result TEXT,
                    created_at TEXT
                )
            """)

            conn.commit()

    def _register(
        self,
        capability_id: int,
        name: str,
        domain: str,
        description: str,
        approval_required: bool = False,
        handler: str = "generic",
    ):
        capability = Capability201500(
            id=capability_id,
            name=name,
            domain=domain,
            description=description,
            approval_required=approval_required,
            handler=handler,
        )

        self.capabilities[capability_id] = capability

        with self._connect() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO capabilities
                (id, name, domain, description,
                 approval_required, enabled, handler)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                capability.id,
                capability.name,
                capability.domain,
                capability.description,
                int(capability.approval_required),
                int(capability.enabled),
                capability.handler,
            ))
            conn.commit()

    def _add_domain(
        self,
        start_id: int,
        domain: str,
        names: List[str],
        approvals: Optional[set] = None,
    ):
        approvals = approvals or set()

        for offset, name in enumerate(names):
            capability_id = start_id + offset

            self._register(
                capability_id,
                name,
                domain,
                name,
                capability_id in approvals,
            )

    def _register_all(self):
        domains = [
            (201, "Traduction et langues"),
            (216, "Éducation et formation"),
            (231, "Santé et bien-être organisationnel"),
            (246, "Agriculture"),
            (261, "Juridique et conformité"),
            (276, "RH et recrutement"),
            (291, "Immobilier"),
            (306, "Voyage et tourisme"),
            (321, "Analyse de données et BI"),
            (336, "Cybersécurité"),
            (351, "Design graphique avancé"),
            (366, "E-commerce avancé"),
            (381, "Support client avancé"),
            (396, "SEO"),
            (411, "Gestion de projet avancée"),
            (426, "Gestion événementielle"),
            (441, "Restaurant et hôtellerie"),
            (456, "Transport et logistique"),
            (471, "Sport et fitness"),
            (486, "Divertissement, jeux et création de contenu"),
        ]

        for start_id, domain in domains:
            for i in range(15):
                capability_id = start_id + i
                self._register(
                    capability_id,
                    f"{domain} - capacité {capability_id}",
                    domain,
                    f"Capacité autonome {capability_id} du domaine {domain}",
                    capability_id in {
                        261, 262, 263, 264, 265,
                        276, 277, 278,
                        336, 337, 338, 339,
                        366, 367, 368,
                        381, 382,
                        411, 412,
                        426, 427,
                        441, 442,
                        456, 457,
                    },
                )

    def _generic_handler(self, capability, payload):
        return {
            "status": "ok",
            "capability_id": capability.id,
            "name": capability.name,
            "domain": capability.domain,
            "payload": payload,
        }

    def get(self, capability_id):
        return self.capabilities.get(int(capability_id))

    def all(self):
        return sorted(self.capabilities.values(), key=lambda x: x.id)

    def search(self, query):
        query = str(query or "").lower().strip()
        if not query:
            return self.all()
        return [
            c for c in self.all()
            if query in c.name.lower() or query in c.domain.lower()
        ]

    def by_domain(self, domain):
        domain = str(domain or "").lower().strip()
        return [c for c in self.all() if c.domain.lower() == domain]

    def enable(self, capability_id):
        c = self.get(capability_id)
        if c is None:
            return False
        c.enabled = True
        return True

    def disable(self, capability_id):
        c = self.get(capability_id)
        if c is None:
            return False
        c.enabled = False
        return True

    def execute(self, capability_id, payload=None, **kwargs):
        c = self.get(capability_id)
        if c is None:
            return {"status": "error", "error": "capability_not_found"}

        if not c.enabled:
            return {"status": "error", "error": "capability_disabled"}

        return self._generic_handler(c, dict(payload or {}))

    def run(self, capability_id, payload=None, **kwargs):
        return self.execute(capability_id, payload, **kwargs)

    def integrate_runtime(self, runtime):
        runtime.capabilities_201_500 = self
        runtime.capabilities_201_500_engine = self
        return self

    def status(self):
        capabilities = self.all()
        domains = {}
        for c in capabilities:
            domains[c.domain] = domains.get(c.domain, 0) + 1

        return {
            "status": "ok",
            "type": "gairus_capabilities_201_500",
            "total": len(capabilities),
            "expected": 300,
            "complete": len(capabilities) == 300,
            "first": capabilities[0].id if capabilities else None,
            "last": capabilities[-1].id if capabilities else None,
            "domains": domains,
        }


_instance = None


def integrate_capabilities_201_500(runtime):
    global _instance
    if _instance is None:
        _instance = GairusCapabilities201500(runtime)
    return _instance.integrate_runtime(runtime)


def get_capabilities_201_500(runtime=None):
    global _instance
    if _instance is None:
        _instance = GairusCapabilities201500(runtime)
    return _instance


def reset_capabilities_201_500():
    global _instance
    _instance = None


if __name__ == "__main__":
    engine = GairusCapabilities201500()
    status = engine.status()
    print("GAIRUS CAPABILITIES 201-500")
    print("=" * 40)
    print(f"Total: {status['total']}")
    print(f"Expected: {status['expected']}")
    print(f"Complete: {status['complete']}")
    print(f"First: {status['first']}")
    print(f"Last: {status['last']}")
    print()
    print("Domains:")
    for domain, count in sorted(status["domains"].items()):
        print(f"  {domain}: {count}")
