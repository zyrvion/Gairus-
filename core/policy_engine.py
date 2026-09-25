from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set


@dataclass
class AccessDecision:
    allowed: bool
    reason: str
    requires_approval: bool = False


@dataclass
class GairusPolicy:
    """
    Politique centrale de Gaïrus.

    Les données sensibles ne sont jamais considérées comme
    publiables par défaut.
    """

    founder_ids: Set[str] = field(default_factory=set)
    ceo_ids: Set[str] = field(default_factory=set)
    privileged_ids: Set[str] = field(default_factory=set)

    sensitive_categories: Set[str] = field(
        default_factory=lambda: {
            "secrets",
            "credentials",
            "api_keys",
            "tokens",
            "passwords",
            "private_keys",
            "hierarchy",
            "internal_org_chart",
            "security_configuration",
            "financial_private_data",
            "legal_private_data",
            "employee_private_data",
        }
    )

    approval_categories: Set[str] = field(
        default_factory=lambda: {
            "bank_transfer",
            "legal_signature",
            "shareholder_decision",
            "capital_operation",
            "high_value_contract",
            "official_filing",
            "employment_contract",
            "termination",
        }
    )


class PolicyEngine:

    def __init__(
        self,
        *,
        founder_ids=None,
        ceo_ids=None,
        privileged_ids=None,
        audit=None,
    ):

        self.policy = GairusPolicy(
            founder_ids=set(founder_ids or []),
            ceo_ids=set(ceo_ids or []),
            privileged_ids=set(privileged_ids or []),
        )

        self.audit = audit

    # ---------------------------------------------------------
    # IDENTITÉ
    # ---------------------------------------------------------

    def is_founder(self, actor_id: Optional[str]) -> bool:
        return bool(
            actor_id
            and actor_id in self.policy.founder_ids
        )

    def is_ceo(self, actor_id: Optional[str]) -> bool:
        return bool(
            actor_id
            and actor_id in self.policy.ceo_ids
        )

    def is_privileged(self, actor_id: Optional[str]) -> bool:
        return bool(
            actor_id
            and actor_id in self.policy.privileged_ids
        )

    # ---------------------------------------------------------
    # DONNÉES SENSIBLES
    # ---------------------------------------------------------

    def is_sensitive(
        self,
        category: Optional[str],
    ) -> bool:

        if not category:
            return False

        return category in self.policy.sensitive_categories

    def can_read_sensitive(
        self,
        actor_id: Optional[str],
        category: str,
    ) -> AccessDecision:

        if not self.is_sensitive(category):
            return AccessDecision(
                allowed=True,
                reason="non_sensitive",
            )

        if self.is_founder(actor_id):
            return AccessDecision(
                allowed=True,
                reason="founder_authorized",
            )

        if self.is_ceo(actor_id):
            return AccessDecision(
                allowed=True,
                reason="ceo_authorized",
            )

        if self.is_privileged(actor_id):
            return AccessDecision(
                allowed=True,
                reason="privileged_authorized",
            )

        return AccessDecision(
            allowed=False,
            reason="sensitive_information_restricted",
        )

    # ---------------------------------------------------------
    # ACTIONS
    # ---------------------------------------------------------

    def check_action(
        self,
        actor_id: Optional[str],
        action: str,
        *,
        category: Optional[str] = None,
    ) -> AccessDecision:

        if category and self.is_sensitive(category):
            return self.can_read_sensitive(
                actor_id,
                category,
            )

        if action in self.policy.approval_categories:
            return AccessDecision(
                allowed=False,
                requires_approval=True,
                reason="human_approval_required",
            )

        return AccessDecision(
            allowed=True,
            reason="action_allowed",
        )

    # ---------------------------------------------------------
    # FILTRAGE DE SORTIE
    # ---------------------------------------------------------

    def sanitize_output(
        self,
        actor_id: Optional[str],
        data: Any,
        category: Optional[str] = None,
    ) -> Any:

        decision = self.can_read_sensitive(
            actor_id,
            category or "",
        )

        if decision.allowed:
            return data

        if isinstance(data, dict):
            return {
                "status": "restricted",
                "reason": decision.reason,
            }

        return "[INFORMATION_RESTRICTED]"

    # ---------------------------------------------------------
    # AUDIT
    # ---------------------------------------------------------

    def audit_decision(
        self,
        actor_id: Optional[str],
        action: str,
        decision: AccessDecision,
    ):

        if self.audit is None:
            return

        payload = {
            "actor_id": actor_id,
            "action": action,
            "allowed": decision.allowed,
            "requires_approval": decision.requires_approval,
            "reason": decision.reason,
        }

        try:
            if hasattr(self.audit, "record"):
                self.audit.record(
                    action="policy_decision",
                    metadata=payload,
                )
            elif hasattr(self.audit, "log"):
                self.audit.log(
                    "policy_decision",
                    payload,
                )
        except Exception:
            pass

    # ---------------------------------------------------------
    # STATUS
    # ---------------------------------------------------------

    def status(self):

        return {
            "status": "available",
            "founders": len(self.policy.founder_ids),
            "ceos": len(self.policy.ceo_ids),
            "privileged": len(self.policy.privileged_ids),
            "sensitive_categories": len(
                self.policy.sensitive_categories
            ),
            "approval_categories": len(
                self.policy.approval_categories
            ),
        }
