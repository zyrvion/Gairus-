from __future__ import annotations

from typing import Any, Dict, Optional

from core.slack_hierarchy import SlackHierarchyRouter


class SlackHierarchyTool:
    """
    Outil Gaïrus permettant d'utiliser la hiérarchie organisationnelle
    directement depuis le registre des outils.
    """

    name = "slack_hierarchy"
    description = (
        "Route les messages, escalades et demandes d'approbation "
        "dans Slack selon la hiérarchie de Gaïrus."
    )

    def __init__(self, router: SlackHierarchyRouter):
        if router is None:
            raise ValueError("SlackHierarchyTool requires a router")
        self.router = router

    def execute(
        self,
        action: str,
        actor_id: Optional[str] = None,
        target_id: Optional[str] = None,
        department_id: Optional[str] = None,
        reason: Optional[str] = None,
        message: Optional[str] = None,
        channel: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Exécute une opération Slack hiérarchique.

        Actions supportées :
        - route
        - build_message
        - send
        - escalation
        - human_approval
        - mention
        """

        action = (action or "").strip().lower()

        if action == "route":
            if not actor_id:
                raise ValueError("actor_id is required for route")

            return self.router.route(
                actor_id=actor_id,
                target_id=target_id,
                department_id=department_id,
                reason=reason,
            )

        if action == "build_message":
            if not actor_id:
                raise ValueError("actor_id is required for build_message")

            return self.router.build_message(
                actor_id=actor_id,
                target_id=target_id,
                reason=reason,
                message=message,
                **kwargs,
            )

        if action == "send":
            if not actor_id:
                raise ValueError("actor_id is required for send")

            return self.router.send(
                actor_id=actor_id,
                target_id=target_id,
                reason=reason,
                message=message,
                channel=channel,
                **kwargs,
            )

        if action in {"escalation", "escalate"}:
            if not actor_id:
                raise ValueError("actor_id is required for escalation")

            return self.router.send_escalation(
                actor_id=actor_id,
                reason=reason or "technical",
                message=message,
                **kwargs,
            )

        if action in {
            "human_approval",
            "human_approval_request",
            "approval",
        }:
            if not actor_id:
                raise ValueError(
                    "actor_id is required for human approval request"
                )

            return self.router.send_human_approval_request(
                actor_id=actor_id,
                action=kwargs.get("requested_action") or kwargs.get("action"),
                amount=kwargs.get("amount"),
                reason=reason,
                message=message,
                mission_id=kwargs.get("mission_id"),
                **{
                    key: value
                    for key, value in kwargs.items()
                    if key
                    not in {
                        "requested_action",
                        "action",
                        "amount",
                        "mission_id",
                    }
                },
            )

        if action == "mention":
            if not target_id:
                raise ValueError("target_id is required for mention")

            return {
                "status": "ok",
                "mention": self.router.mention(target_id),
            }

        raise ValueError(
            f"Unknown slack_hierarchy action: {action}"
        )


def register(registry, router: SlackHierarchyRouter):
    """
    Enregistre l'outil dans le ToolRegistry de Gaïrus.
    """

    tool = SlackHierarchyTool(router)

    registry.register(
        SlackHierarchyTool.name,
        tool,
        overwrite=True,
    )

    return tool
