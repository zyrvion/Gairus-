from __future__ import annotations

from typing import Any, Dict


class CapabilityRegistry:
    """
    Registre lisible par Gaïrus de toutes ses capacités.
    """

    def __init__(self):
        self._capabilities: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        description: str,
        category: str,
        handler: Any = None,
        enabled: bool = True,
    ):
        self._capabilities[name] = {
            "name": name,
            "description": description,
            "category": category,
            "enabled": enabled,
            "handler": handler,
        }

        return self._capabilities[name]

    def unregister(self, name: str):
        return self._capabilities.pop(name, None)

    def get(self, name: str):
        return self._capabilities.get(name)

    def has(self, name: str):
        return name in self._capabilities

    def enable(self, name: str):
        if name in self._capabilities:
            self._capabilities[name]["enabled"] = True

    def disable(self, name: str):
        if name in self._capabilities:
            self._capabilities[name]["enabled"] = False

    def list(self):
        return sorted(self._capabilities.keys())

    def catalog(self):
        result = []

        for name in self.list():
            item = self._capabilities[name]

            result.append({
                "name": item["name"],
                "description": item["description"],
                "category": item["category"],
                "enabled": item["enabled"],
            })

        return result

    def categories(self):
        result = {}

        for item in self._capabilities.values():
            category = item["category"]

            result.setdefault(category, [])
            result[category].append(item["name"])

        return result

    def count(self):
        return len(self._capabilities)

    def status(self):
        enabled = sum(
            1
            for item in self._capabilities.values()
            if item["enabled"]
        )

        return {
            "total": self.count(),
            "enabled": enabled,
            "disabled": self.count() - enabled,
            "categories": self.categories(),
        }


def default_capabilities(runtime=None):
    registry = CapabilityRegistry()

    registry.register(
        "reasoning",
        "Analyse, raisonnement et décomposition de problèmes.",
        "intelligence",
        runtime,
    )

    registry.register(
        "planning",
        "Planification multi-étapes et création de missions.",
        "intelligence",
        runtime,
    )

    registry.register(
        "autonomy",
        "Exécution autonome contrôlée avec gouvernance.",
        "autonomy",
        runtime,
    )

    registry.register(
        "enterprise",
        "Gestion de l'entreprise, rôles, départements et gouvernance.",
        "enterprise",
        runtime,
    )

    registry.register(
        "missions",
        "Création, délégation, suivi et exécution des missions.",
        "operations",
        runtime,
    )

    registry.register(
        "hierarchy",
        "Gestion de la hiérarchie et des escalades.",
        "enterprise",
        runtime,
    )

    registry.register(
        "tools",
        "Utilisation et orchestration des outils disponibles.",
        "tools",
        runtime,
    )

    registry.register(
        "llm",
        "Accès aux moteurs de langage configurés.",
        "intelligence",
        runtime,
    )

    registry.register(
        "slack",
        "Communication et orchestration via Slack.",
        "communication",
        runtime,
    )

    registry.register(
        "memory",
        "Mémoire runtime et contexte opérationnel.",
        "memory",
        runtime,
    )

    registry.register(
        "audit",
        "Traçabilité et journalisation des actions.",
        "security",
        runtime,
    )

    registry.register(
        "approvals",
        "Gestion des actions nécessitant une approbation humaine.",
        "governance",
        runtime,
    )

    return registry
