from __future__ import annotations

from typing import Any, Dict

from core.autonomous_support import AutonomousSupport


class AutonomousIntegration:
    """
    Pont entre le runtime complet de Gaïrus et les capacités autonomes
    persistantes.

    Cette couche ne remplace aucun composant existant.
    Elle ajoute :
      - mémoire persistante SQLite
      - audit JSONL
      - EventBus
      - accès aux missions existantes
      - accès aux outils existants
    """

    def __init__(self, runtime: Any):
        if runtime is None:
            raise ValueError("runtime is required")

        self.runtime = runtime
        self.support = AutonomousSupport(runtime)

        self._attach()

    def _attach(self) -> None:
        """
        Branche le support sans écraser RuntimeMemory.
        """

        # Support principal
        self.runtime.support = self.support

        # Mémoire persistante séparée de RuntimeMemory.
        self.runtime.persistent_memory = self.support.memory

        # Audit persistant.
        self.runtime.audit = self.support.audit

        # Bus d'événements.
        self.runtime.events = self.support.events

        # Références explicites vers les composants déjà existants.
        self.runtime.runtime_memory = getattr(
            self.runtime,
            "memory",
            None,
        )

        self.runtime.mission_engine = getattr(
            self.runtime,
            "missions",
            None,
        )

        self.runtime.tool_runtime = getattr(
            self.runtime,
            "tools",
            None,
        )

    def remember(
        self,
        key: str,
        value: Any,
        *,
        category: str = "general",
        actor_id: str | None = None,
        mission_id: str | None = None,
    ) -> Dict[str, Any]:
        return self.support.remember(
            key,
            value,
            category=category,
            actor_id=actor_id,
            mission_id=mission_id,
        )

    def recall(self, key: str) -> Any:
        return self.support.recall(key)

    def search_memory(
        self,
        query: str,
        *,
        category: str | None = None,
        limit: int = 20,
    ):
        results = self.support.search_memory(
            query,
            limit=limit,
        )

        if category is not None:
            results = [
                item
                for item in results
                if item.get('category') == category
            ]

        return results

    def record_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        return self.support.record_mission(mission)

    def record_tool_call(
        self,
        tool: str,
        *,
        actor_id: str | None = None,
        mission_id: str | None = None,
        arguments: Dict[str, Any] | None = None,
        result: Any = None,
        status: str = "ok",
    ) -> Dict[str, Any]:
        return self.support.record_tool_call(
            tool,
            actor_id=actor_id,
            mission_id=mission_id,
            arguments=arguments,
            result=result,
            status=status,
        )

    def emit(self, event_type: str, payload: Dict[str, Any] | None = None):
        return self.support.events.emit(
            event_type,
            payload or {},
        )

    def subscribe(self, event_type: str, callback):
        return self.support.events.subscribe(
            event_type,
            callback,
        )

    def status(self) -> Dict[str, Any]:
        support_status = self.support.status()

        return {
            "status": "ok",
            "type": "autonomous_integration",
            "runtime": {
                "type": type(self.runtime).__name__,
                "memory": getattr(self.runtime, "memory", None) is not None,
                "missions": getattr(self.runtime, "missions", None) is not None,
                "tools": getattr(self.runtime, "tools", None) is not None,
                "llm": getattr(self.runtime, "llm", None) is not None,
                "autonomy": getattr(self.runtime, "autonomy", None) is not None,
                "enterprise": getattr(self.runtime, "enterprise", None) is not None,
                "controller": getattr(self.runtime, "controller", None) is not None,
                "executor": getattr(self.runtime, "executor", None) is not None,
                "slack": getattr(self.runtime, "slack", None) is not None,
            },
            "support": support_status,
        }


_integration = None


def integrate_runtime(runtime: Any) -> AutonomousIntegration:
    """
    Installe l'intégration autonome sur une instance de runtime.
    """
    global _integration

    _integration = AutonomousIntegration(runtime)
    return _integration


def get_integration() -> AutonomousIntegration | None:
    """
    Retourne la dernière intégration installée.
    """
    return _integration


def integration_status() -> Dict[str, Any]:
    """
    Retourne l'état de l'intégration.
    """
    if _integration is None:
        return {
            "status": "not_initialized",
            "type": "autonomous_integration",
        }

    return _integration.status()
