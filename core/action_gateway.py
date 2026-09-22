from .audit_gateway import AuditGateway
from __future__ import annotations

from .governance_gate import GovernanceGate, GovernanceBlocked


class ActionGateway:
    """
    Point d'entrée commun pour les actions exécutables.

    Executor, CompanyController et les futurs outils peuvent utiliser
    la même politique sans dupliquer la logique de gouvernance.
    """

    def __init__(self, enterprise=None, controller=None):
        self.audit_gateway = AuditGateway(enterprise=enterprise)
        self.enterprise = enterprise
        self.controller = controller
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
        return self.governance.check(
            actor_id=actor_id,
            action=action or tool or "",
            tool=tool,
            amount=amount,
            require_approval=True,
        )

    def authorize_tool(
        self,
        actor_id=None,
        tool="",
        action=None,
        amount=None,
    ):
        return self.governance.authorize_tool(
            actor_id=actor_id,
            tool=tool,
            action=action,
            amount=amount,
        )

    @staticmethod
    def blocked(exc):
        return isinstance(exc, GovernanceBlocked)
