from core.audit_gateway import AuditGateway
from core.action_gateway import ActionGateway


class Executor:
    """
    Moteur d'exécution compatible avec l'ancien système de permissions
    et avec le nouveau système Enterprise / Governance / Audit.
    """

    def __init__(self, permissions=None, enterprise=None, controller=None):
        self.permissions = permissions
        self.enterprise = enterprise
        self.controller = controller

        self.action_gateway = ActionGateway(
            enterprise=enterprise,
            controller=controller,
        )

        self.audit_gateway = AuditGateway(
            enterprise=enterprise,
        )

    def audit_execution(
        self,
        *,
        actor_id=None,
        action=None,
        tool=None,
        amount=None,
        status=None,
        result=None,
        error=None,
        mission_id=None,
        metadata=None,
    ):
        return self.audit_gateway.record(
            event="execution",
            actor_id=actor_id,
            action=action,
            tool=tool,
            amount=amount,
            status=status,
            result=result,
            error=error,
            mission_id=mission_id,
            metadata=metadata,
        )

    def authorize_action(
        self,
        actor_id=None,
        action="",
        tool=None,
        amount=None,
    ):
        """
        Contrôle Enterprise obligatoire lorsqu'un actor_id est fourni.
        """
        return self.action_gateway.authorize(
            actor_id=actor_id,
            action=action,
            tool=tool,
            amount=amount,
        )

    def execute(
        self,
        action,
        risk="medium",
        handler=None,
        actor_id=None,
        tool=None,
        amount=None,
        mission_id=None,
        metadata=None,
    ):
        """
        Exécute une action.

        Compatibilité :
        - ancien appel : permissions.allowed(action, risk)
        - appel Enterprise : actor_id déclenche Governance + Audit
        """

        authorization = None

        try:
            # =====================================================
            # ENTERPRISE GOVERNANCE GATE
            # =====================================================
            if actor_id is not None:
                authorization = self.authorize_action(
                    actor_id=actor_id,
                    action=action,
                    tool=tool,
                    amount=amount,
                )

                if authorization is None:
                    result = {
                        "status": "blocked",
                        "action": action,
                        "message": "Autorisation Enterprise invalide",
                    }

                    self.audit_execution(
                        actor_id=actor_id,
                        action=action,
                        tool=tool,
                        amount=amount,
                        status="blocked",
                        result=result,
                        mission_id=mission_id,
                        metadata=metadata,
                    )

                    return result

                if authorization.get("status") in {
                    "blocked",
                    "denied",
                    "error",
                    "approval_required",
                }:
                    result = {
                        "status": authorization.get("status"),
                        "action": action,
                        "authorization": authorization,
                    }

                    self.audit_execution(
                        actor_id=actor_id,
                        action=action,
                        tool=tool,
                        amount=amount,
                        status=result["status"],
                        result=result,
                        mission_id=mission_id,
                        metadata=metadata,
                    )

                    return result

            # =====================================================
            # ANCIEN SYSTEME DE PERMISSIONS
            # =====================================================
            if self.permissions is not None:
                allowed = self.permissions.allowed(action, risk)

                if not allowed:
                    result = {
                        "status": "approval_required",
                        "action": action,
                    }

                    self.audit_execution(
                        actor_id=actor_id,
                        action=action,
                        tool=tool,
                        amount=amount,
                        status="approval_required",
                        result=result,
                        mission_id=mission_id,
                        metadata=metadata,
                    )

                    return result

            # =====================================================
            # EXECUTION
            # =====================================================
            if handler:
                value = handler()

                result = {
                    "status": "completed",
                    "action": action,
                    "result": value,
                }
            else:
                result = {
                    "status": "completed",
                    "action": action,
                }

            self.audit_execution(
                actor_id=actor_id,
                action=action,
                tool=tool,
                amount=amount,
                status="completed",
                result=result,
                mission_id=mission_id,
                metadata=metadata,
            )

            return result

        except Exception as exc:
            result = {
                "status": "error",
                "action": action,
                "error": str(exc),
            }

            try:
                self.audit_execution(
                    actor_id=actor_id,
                    action=action,
                    tool=tool,
                    amount=amount,
                    status="error",
                    result=result,
                    error=str(exc),
                    mission_id=mission_id,
                    metadata=metadata,
                )
            except Exception:
                pass

            return result
