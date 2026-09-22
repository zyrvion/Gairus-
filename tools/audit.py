from __future__ import annotations

from security.audit import get_audit_logger


class AuditTool:
    name = "audit"

    def recent(self, limit=50):
        return get_audit_logger().read(limit=limit)

    def search(
        self,
        actor_id=None,
        action=None,
        status=None,
        tool=None,
        mission_id=None,
        limit=100,
    ):
        return get_audit_logger().search(
            actor_id=actor_id,
            action=action,
            status=status,
            tool=tool,
            mission_id=mission_id,
            limit=limit,
        )
