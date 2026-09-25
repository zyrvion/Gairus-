"""
Sécurité et gouvernance de Gaïrus.

Centralise les politiques d'approbation humaine
et les contrôles liés aux actions sensibles.
"""

from .approval_policy import (
    HUMAN_APPROVAL_ACTIONS,
    ApprovalPolicy,
    DEFAULT_APPROVAL_POLICY,
    approval_reason,
    is_sensitive_action,
    normalize_action,
    policy,
    requires_human_approval,
)

__all__ = [
    "HUMAN_APPROVAL_ACTIONS",
    "ApprovalPolicy",
    "DEFAULT_APPROVAL_POLICY",
    "approval_reason",
    "is_sensitive_action",
    "normalize_action",
    "policy",
    "requires_human_approval",
]
