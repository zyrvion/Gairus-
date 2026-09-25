from __future__ import annotations

from typing import Any, Dict, Optional

from tools.registry import ToolRegistry


class ToolRuntime:
    """
    Couche d'exécution des outils de Gaïrus.

    Responsabilités :
    - centraliser le registre des outils ;
    - enregistrer les outils du système ;
    - exposer un catalogue exploitable par l'IA ;
    - exécuter les outils de manière contrôlée ;
    - conserver un historique minimal des appels.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or ToolRegistry()
        self.history = []

    def register(
        self,
        name: str,
        tool: Any,
        overwrite: bool = False,
    ) -> Any:
        return self.registry.register(
            name,
            tool,
            overwrite=overwrite,
        )

    def unregister(self, name: str) -> Any:
        return self.registry.unregister(name)

    def has(self, name: str) -> bool:
        return self.registry.has(name)

    def get(self, name: str, default: Any = None) -> Any:
        return self.registry.get(name, default)

    def list_tools(self):
        return self.registry.list()

    def catalog(self):
        return self.registry.catalog()

    def ai_catalog(self):
        return self.registry.ai_catalog()

    def execute(
        self,
        name: str,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Exécute un outil et conserve la trace de l'appel.

        Les informations actor_id et mission_id sont conservées
        dans l'historique sans être imposées aux outils qui
        n'en ont pas besoin.
        """

        entry = {
            "tool": name,
            "actor_id": actor_id,
            "mission_id": mission_id,
            "status": "running",
            "arguments": dict(kwargs),
        }

        self.history.append(entry)

        try:
            result = self.registry.execute(
                name,
                **kwargs,
            )

            entry["status"] = "ok"
            entry["result"] = result

            return {
                "status": "ok",
                "tool": name,
                "actor_id": actor_id,
                "mission_id": mission_id,
                "result": result,
            }

        except Exception as exc:
            entry["status"] = "error"
            entry["error"] = str(exc)
            entry["error_type"] = exc.__class__.__name__

            return {
                "status": "error",
                "tool": name,
                "actor_id": actor_id,
                "mission_id": mission_id,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            }

    def safe_execute(
        self,
        name: str,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return self.execute(
            name,
            actor_id=actor_id,
            mission_id=mission_id,
            **kwargs,
        )

    def last_calls(self, limit: int = 20):
        if limit <= 0:
            return []

        return self.history[-limit:]

    def clear_history(self):
        self.history.clear()

    def status(self) -> Dict[str, Any]:
        return {
            "tools": self.registry.count(),
            "history": len(self.history),
            "catalog": self.registry.list(),
        }
