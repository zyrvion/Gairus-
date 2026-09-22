from __future__ import annotations

from typing import Any


class GovernanceBlocked(PermissionError):
    """Action refusée par la gouvernance Enterprise."""


class GovernanceGate:
    """
    Barrière centrale de sécurité Enterprise.

    Toutes les actions exécutables peuvent passer par cette classe.
    Les actions sensibles nécessitent une approbation humaine valide.
    """

    SENSITIVE_ACTIONS = {
        "legal_signature",
        "bank_transfer",
        "shareholder_decision",
        "capital_operation",
        "high_value_contract",
        "official_filing",
        "employment_contract",
        "termination",
    }

    TOOL_ACTIONS = {
        "terminal": "terminal_execute",
        "shell": "terminal_execute",
        "command": "terminal_execute",
        "git": "git_operation",
        "git_commit": "git_commit",
        "git_push": "git_push",
        "slack": "slack_send",
        "slack_message": "slack_send",
        "finance": "bank_transfer",
        "bank_transfer": "bank_transfer",
        "legal": "legal_signature",
        "signature": "legal_signature",
        "official_filing": "official_filing",
        "employment": "employment_contract",
        "termination": "termination",
        "shareholder": "shareholder_decision",
        "capital": "capital_operation",
    }

    def __init__(self, enterprise=None, controller=None):
        self.enterprise = enterprise
        self.controller = controller

    def _action_name(self, action: str, tool: str | None = None) -> str:
        raw = str(action or tool or "").strip().lower()

        if raw in self.TOOL_ACTIONS:
            return self.TOOL_ACTIONS[raw]

        return raw

    def _sensitive(self, action: str, amount: Any = None) -> bool:
        if action in self.SENSITIVE_ACTIONS:
            return True

        if amount is not None:
            try:
                return float(amount) > 0
            except (TypeError, ValueError):
                return False

        return False

    def preview(
        self,
        actor_id: str | None,
        action: str,
        amount: Any = None,
        tool: str | None = None,
    ) -> dict:
        action = self._action_name(action, tool)

        if self.enterprise is None:
            return {
                "status": "allowed",
                "approval_required": False,
                "action": action,
                "actor_id": actor_id,
                "reason": "governance_unconfigured",
            }

        if not actor_id:
            if self._sensitive(action, amount):
                return {
                    "status": "approval_required",
                    "approval_required": True,
                    "action": action,
                    "actor_id": None,
                    "message": "Actor Enterprise requis pour une action sensible.",
                }

            return {
                "status": "allowed",
                "approval_required": False,
                "action": action,
                "actor_id": None,
            }

        return self.enterprise.governance_check(
            actor_id=actor_id,
            action=action,
            amount=amount,
        )

    def check(
        self,
        actor_id: str | None,
        action: str,
        amount: Any = None,
        tool: str | None = None,
        require_approval: bool = True,
    ) -> dict:
        action = self._action_name(action, tool)

        result = self.preview(
            actor_id=actor_id,
            action=action,
            amount=amount,
            tool=tool,
        )

        if result.get("status") == "error":
            raise GovernanceBlocked(
                result.get("message", "Erreur de gouvernance.")
            )

        if require_approval and result.get("approval_required"):
            approval = result.get("approval")

            if not approval or approval.get("status") != "approved":
                raise GovernanceBlocked(
                    f"Action bloquée par la gouvernance : {action}. "
                    "Une approbation humaine valide est requise."
                )

        if result.get("status") != "allowed":
            raise GovernanceBlocked(
                result.get(
                    "message",
                    f"Action bloquée par la gouvernance : {action}.",
                )
            )

        return result

    def authorize_tool(
        self,
        actor_id: str | None,
        tool: str,
        action: str | None = None,
        amount: Any = None,
    ) -> dict:
        return self.check(
            actor_id=actor_id,
            action=action or tool,
            amount=amount,
            tool=tool,
            require_approval=True,
        )
