from __future__ import annotations

from typing import Any, Dict, Optional

from core.full_bootstrap import get_full_runtime
from core.capability_registry import default_capabilities


class Gairus:
    """
    Façade publique principale de Gaïrus.

    Toute l'architecture interne reste modulaire.
    Cette classe fournit une interface simple et stable.
    """

    def __init__(
        self,
        runtime: Any = None,
    ):
        self.runtime = runtime or get_full_runtime()

        self.capabilities = default_capabilities(
            runtime=self.runtime,
        )

    def ask(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        return self.runtime.think(
            prompt,
            context=context or {},
        )

    def execute(
        self,
        actor_id: str,
        action: str,
        **kwargs: Any,
    ):
        return self.runtime.run(
            actor_id=actor_id,
            action=action,
            **kwargs,
        )

    def mission(
        self,
        actor_id: str,
        title: str,
        objective: str,
        **kwargs: Any,
    ):
        return self.runtime.create_mission(
            actor_id=actor_id,
            title=title,
            objective=objective,
            **kwargs,
        )

    def delegate(
        self,
        mission_id: str,
        employee_id: str,
        delegator_id: Optional[str] = None,
    ):
        return self.runtime.delegate(
            mission_id=mission_id,
            employee_id=employee_id,
            delegator_id=delegator_id,
        )

    def escalate(
        self,
        actor_id: str,
        reason: str,
        **kwargs: Any,
    ):
        return self.runtime.escalate(
            actor_id=actor_id,
            reason=reason,
            **kwargs,
        )

    def slack(
        self,
        channel: str,
        text: str,
        **kwargs: Any,
    ):
        return self.runtime.send_slack(
            channel=channel,
            text=text,
            **kwargs,
        )

    def status(self):
        return self.runtime.status()

    def dashboard(self):
        return self.runtime.dashboard()

    def capabilities_catalog(self):
        return self.capabilities.catalog()

    def capabilities_status(self):
        return self.capabilities.status()


_gairus = None


def get_gairus():
    global _gairus

    if _gairus is None:
        _gairus = Gairus()

    return _gairus


def reset_gairus():
    global _gairus
    _gairus = None


__all__ = [
    "Gairus",
    "get_gairus",
    "reset_gairus",
]
