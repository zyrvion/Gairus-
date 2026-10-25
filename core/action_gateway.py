from __future__ import annotations

from .governance_gate import GovernanceGate, GovernanceBlocked
from .audit_gateway import AuditGateway


class ActionGateway:
    """
    Point d'entrée commun pour les actions exécutables.

    Executor, CompanyController et les futurs outils peuvent utiliser
    la même politique sans dupliquer la logique de gouvernance.
    """

    def __init__(self, enterprise=None, controller=None):
        self.enterprise = enterprise
        self.controller = controller
        self.audit_gateway = AuditGateway(enterprise=enterprise)
        self.governance = GovernanceGate(
            enterprise=enterprise,
            controller=controller,
        )

    def authorize(
        self,
        actor_id=None,
        action="",
        tool=None,
        amount=None,
    ):
        action = action or tool or ""
        try:
            result = self.governance.check(
                actor_id=actor_id, action=action, tool=tool,
                amount=amount, require_approval=True,
            )
        except GovernanceBlocked as exc:
            self.audit_gateway.record(
                actor_id=actor_id, action=action, tool=tool,
                amount=amount, status="blocked", error=str(exc),
            )
            raise
        self.audit_gateway.record(
            actor_id=actor_id, action=action, tool=tool,
            amount=amount, status="allowed", authorization=result,
        )
        return result

    def authorize_tool(
        self,
        actor_id=None,
        tool="",
        action=None,
        amount=None,
    ):
        return self.authorize(
            actor_id=actor_id,
            tool=tool,
            action=action,
            amount=amount,
        )

    @staticmethod
    def blocked(exc):
        return isinstance(exc, GovernanceBlocked)
