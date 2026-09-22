from __future__ import annotations

from security.audit import get_audit_logger


class AuditGateway:
    """
    Couche commune entre gouvernance et journal d'audit.
    """

    def __init__(self, enterprise=None):
        self.enterprise = enterprise
        self.audit = get_audit_logger()

    def actor_context(self, actor_id):
        if self.enterprise is None or not actor_id:
            return {}

        actor = self.enterprise.employees.get(actor_id)

        if actor is None:
            return {}

        department = self.enterprise.departments.get(
            getattr(actor, "department_id", None)
        )

        return {
            "actor_id": actor.id,
            "actor_name": actor.name,
            "actor_level": actor.level,
            "department_id": getattr(
                actor,
                "department_id",
                None,
            ),
            "department_name": (
                getattr(department, "name", None)
                if department
                else None
            ),
        }

    def record(
        self,
        *,
        event="action",
        actor_id=None,
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
        context = self.actor_context(actor_id)

        return self.audit.log(
            event=event,
            actor_id=context.get("actor_id", actor_id),
            actor_name=context.get("actor_name"),
            actor_level=context.get("actor_level"),
            department_id=context.get("department_id"),
            department_name=context.get("department_name"),
            action=action,
            tool=tool,
            amount=amount,
            status=status,
            authorization=authorization,
            approval=approval,
            result=result,
            error=error,
            mission_id=mission_id,
            metadata=metadata,
        )
