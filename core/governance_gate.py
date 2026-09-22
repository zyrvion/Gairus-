from __future__ import annotations

from typing import Any


class GovernanceBlocked(PermissionError):
    """Action bloquée par la gouvernance Enterprise."""


class GovernanceGate:
    """
    Barrière centrale avant toute action Enterprise sensible.

    Une action sensible ne peut pas être considérée comme exécutable
    simplement parce que l'acteur possède une permission technique.
    La gouvernance doit également l'autoriser.
    """

    def __init__(self, enterprise):
        self.enterprise = enterprise

    def check(
        self,
        actor_id: str,
        action: str,
        amount: Any = None,
        require_approval: bool = True,
    ) -> dict:
        result = self.enterprise.governance_check(
            actor_id=actor_id,
            action=action,
            amount=amount,
        )

        if result.get("status") == "error":
            raise GovernanceBlocked(result.get("message", "Gouvernance invalide"))

        if require_approval and result.get("approval_required"):
            approval = result.get("approval")

            if not approval or approval.get("status") != "approved":
                raise GovernanceBlocked(
                    "Action bloquée : approbation humaine requise."
                )

        if result.get("status") != "allowed":
            raise GovernanceBlocked(
                result.get("message", "Action bloquée par la gouvernance.")
            )

        return result

    def preview(
        self,
        actor_id: str,
        action: str,
        amount: Any = None,
    ) -> dict:
        return self.enterprise.governance_check(
            actor_id=actor_id,
            action=action,
            amount=amount,
        )
