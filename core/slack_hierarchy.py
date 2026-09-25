from __future__ import annotations

from typing import Any, Dict, Optional

from config.slack_hierarchy import (
    get_channel,
    is_valid_reason,
    requires_human_escalation,
)


class SlackHierarchyRouter:
    """
    Routeur de communication hiérarchique de Gaïrus.

    Son rôle est de transformer une situation métier en
    communication Slack structurée.

    Exemple :

        employé
            ↓
        manager
            ↓
        directeur
            ↓
        directeur général
            ↓
        administrateur humain

    Le routeur ne contourne jamais la gouvernance.
    Il prépare ou transmet uniquement la communication.
    """

    def __init__(
        self,
        hierarchy,
        slack_gateway=None,
    ):
        self.hierarchy = hierarchy
        self.slack_gateway = slack_gateway

    # ------------------------------------------------------------------
    # ACTEURS
    # ------------------------------------------------------------------

    def actor(self, actor_id: str):
        return self.hierarchy.get(actor_id)

    def target(
        self,
        actor_id: str,
        reason: Optional[str] = None,
    ):
        return self.hierarchy.escalation_target(
            actor_id,
            reason,
        )

    # ------------------------------------------------------------------
    # CANAUX
    # ------------------------------------------------------------------

    def channel_for_actor(
        self,
        actor_id: str,
    ) -> str:

        actor = self.actor(actor_id)

        if actor is None:
            return get_channel("direction")

        return get_channel(
            actor.department_id
        )

    def channel_for_department(
        self,
        department_id: str,
    ) -> str:

        return get_channel(
            department_id
        )

    # ------------------------------------------------------------------
    # MENTIONS
    # ------------------------------------------------------------------

    def mention(
        self,
        actor,
    ) -> Optional[str]:

        if actor is None:
            return None

        slack_user_id = getattr(
            actor,
            "slack_user_id",
            None,
        )

        if not slack_user_id:
            return None

        return f"<@{slack_user_id}>"

    # ------------------------------------------------------------------
    # ROUTAGE
    # ------------------------------------------------------------------

    def route(
        self,
        actor_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:

        actor = self.actor(actor_id)

        if actor is None:
            return {
                "status": "unknown_actor",
                "actor_id": actor_id,
                "target": None,
            }

        target = self.target(
            actor_id,
            reason,
        )

        channel = self.channel_for_actor(
            actor_id
        )

        return {
            "status": "ok",
            "actor_id": actor.actor_id,
            "actor_name": actor.name,
            "actor_level": actor.level,
            "department_id": actor.department_id,
            "channel": channel,
            "reason": reason,
            "reason_known": is_valid_reason(
                reason
            ),
            "target_actor_id": (
                target.actor_id
                if target
                else None
            ),
            "target_name": (
                target.name
                if target
                else None
            ),
            "target_level": (
                target.level
                if target
                else None
            ),
            "target_slack_user_id": (
                target.slack_user_id
                if target
                else None
            ),
        }

    # ------------------------------------------------------------------
    # CONSTRUCTION DU MESSAGE
    # ------------------------------------------------------------------

    def build_message(
        self,
        actor_id: str,
        text: str,
        reason: Optional[str] = None,
        mission_id: Optional[str] = None,
        action: Optional[str] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:

        route = self.route(
            actor_id,
            reason,
        )

        if route["status"] != "ok":
            return route

        target = self.target(
            actor_id,
            reason,
        )

        mention = self.mention(
            target
        )

        prefix = ""

        if mention:
            prefix = mention + " "

        if priority == "high":
            prefix += "🚨 "

        elif priority == "urgent":
            prefix += "🔴 "

        message = (
            f"{prefix}[GAÏRUS] {text}"
        )

        return {
            "status": "prepared",
            "channel": route["channel"],
            "text": message,
            "actor_id": actor_id,
            "target_actor_id": (
                target.actor_id
                if target
                else None
            ),
            "target_slack_user_id": (
                target.slack_user_id
                if target
                else None
            ),
            "reason": reason,
            "mission_id": mission_id,
            "action": action,
            "priority": priority,
            "human_escalation": (
                requires_human_escalation(
                    action
                )
            ),
        }

    # ------------------------------------------------------------------
    # ENVOI
    # ------------------------------------------------------------------

    def send(
        self,
        actor_id: str,
        text: str,
        reason: Optional[str] = None,
        mission_id: Optional[str] = None,
        action: Optional[str] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:

        payload = self.build_message(
            actor_id=actor_id,
            text=text,
            reason=reason,
            mission_id=mission_id,
            action=action,
            priority=priority,
        )

        if payload.get("status") != "prepared":
            return payload

        if self.slack_gateway is None:
            return {
                **payload,
                "status": "prepared_no_gateway",
            }

        sender = getattr(
            self.slack_gateway,
            "send_message",
            None,
        )

        if not callable(sender):
            return {
                **payload,
                "status": "prepared_gateway_without_sender",
            }

        try:
            result = sender(
                channel=payload["channel"],
                text=payload["text"],
            )

            return {
                **payload,
                "status": "sent",
                "result": result,
            }

        except TypeError:
            # Compatibilité avec les gateways
            # utilisant une signature positionnelle.
            try:
                result = sender(
                    payload["channel"],
                    payload["text"],
                )

                return {
                    **payload,
                    "status": "sent",
                    "result": result,
                }

            except Exception as exc:
                return {
                    **payload,
                    "status": "error",
                    "error": str(exc),
                }

        except Exception as exc:
            return {
                **payload,
                "status": "error",
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # ESCALADE
    # ------------------------------------------------------------------

    def send_escalation(
        self,
        actor_id: str,
        text: str,
        reason: Optional[str] = None,
        mission_id: Optional[str] = None,
        action: Optional[str] = None,
        priority: str = "high",
    ) -> Dict[str, Any]:

        return self.send(
            actor_id=actor_id,
            text=text,
            reason=reason,
            mission_id=mission_id,
            action=action,
            priority=priority,
        )

    # ------------------------------------------------------------------
    # APPROBATION HUMAINE
    # ------------------------------------------------------------------

    def send_human_approval_request(
        self,
        actor_id: str,
        action: str,
        text: str,
        mission_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        return self.send(
            actor_id=actor_id,
            text=(
                "APPROBATION HUMAINE REQUISE | "
                f"Action: {action} | {text}"
            ),
            reason="human_required",
            mission_id=mission_id,
            action=action,
            priority="urgent",
        )
