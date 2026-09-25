from __future__ import annotations

from typing import Any, Dict, Optional


# Actions qui exigent explicitement une validation humaine.
HUMAN_APPROVAL_ACTIONS = {
    "legal_signature",
    "bank_transfer",
    "shareholder_decision",
    "capital_operation",
    "high_value_contract",
    "official_filing",
    "employment_contract",
    "termination",
}


# Actions particulièrement sensibles pouvant être utilisées
# par les différents moteurs de Gaïrus.
SENSITIVE_ACTIONS = set(HUMAN_APPROVAL_ACTIONS)


def normalize_action(action: Optional[str]) -> str:
    if action is None:
        return ""

    return str(action).strip().lower()


def requires_human_approval(
    action: Optional[str],
    amount: Optional[float] = None,
) -> bool:
    """
    Détermine si une action doit obligatoirement passer
    par une approbation humaine.
    """
    normalized = normalize_action(action)

    if normalized in HUMAN_APPROVAL_ACTIONS:
        return True

    if amount is not None:
        try:
            if float(amount) > 0:
                return True
        except (TypeError, ValueError):
            pass

    return False


def is_sensitive_action(
    action: Optional[str],
) -> bool:
    return normalize_action(action) in SENSITIVE_ACTIONS


def approval_reason(
    action: Optional[str],
    amount: Optional[float] = None,
) -> str:
    normalized = normalize_action(action)

    if normalized in HUMAN_APPROVAL_ACTIONS:
        return (
            f"L'action '{normalized}' appartient aux opérations "
            "nécessitant une validation humaine."
        )

    if amount is not None:
        try:
            if float(amount) > 0:
                return (
                    "Une opération financière avec montant positif "
                    "nécessite une validation humaine."
                )
        except (TypeError, ValueError):
            pass

    return "Aucune approbation humaine explicite requise."


def policy(
    action: Optional[str],
    amount: Optional[float] = None,
) -> Dict[str, Any]:
    normalized = normalize_action(action)
    required = requires_human_approval(
        normalized,
        amount=amount,
    )

    return {
        "action": normalized,
        "sensitive": is_sensitive_action(
            normalized,
        ),
        "human_approval_required": required,
        "reason": approval_reason(
            normalized,
            amount=amount,
        ),
    }


class ApprovalPolicy:
    """
    Interface objet pour les composants de Gaïrus.

    Cette classe ne valide pas elle-même une approbation.
    Elle détermine uniquement quand une validation est requise.
    """

    def __init__(
        self,
        enabled: bool = True,
    ):
        self.enabled = bool(enabled)

    def configure(
        self,
        enabled: bool,
    ):
        self.enabled = bool(enabled)
        return self.status()

    def requires(
        self,
        action: Optional[str],
        amount: Optional[float] = None,
    ) -> bool:
        if not self.enabled:
            return False

        return requires_human_approval(
            action,
            amount=amount,
        )

    def is_sensitive(
        self,
        action: Optional[str],
    ) -> bool:
        return is_sensitive_action(
            action,
        )

    def evaluate(
        self,
        action: Optional[str],
        amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        result = policy(
            action,
            amount=amount,
        )

        result["policy_enabled"] = self.enabled

        if not self.enabled:
            result["human_approval_required"] = False
            result["reason"] = (
                "La politique d'approbation est désactivée."
            )

        return result

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "sensitive_actions": sorted(
                SENSITIVE_ACTIONS,
            ),
            "human_approval_actions": sorted(
                HUMAN_APPROVAL_ACTIONS,
            ),
        }


DEFAULT_APPROVAL_POLICY = ApprovalPolicy(
    enabled=True,
)
