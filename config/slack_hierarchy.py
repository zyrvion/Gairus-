from __future__ import annotations


SLACK_CHANNELS = {
    "direction": "#direction",
    "finance": "#finance",
    "commercial": "#commercial",
    "marketing": "#marketing",
    "technique": "#technique",
    "operations": "#operations",
    "rh": "#rh",
    "juridique": "#juridique",
    "recherche": "#recherche",
    "support": "#support",
    "projets": "#projets",
}


# Hiérarchie de communication de Gaïrus.
#
# employee
#     ↓
# manager
#     ↓
# director
#     ↓
# general_director
#     ↓
# human_admin
#
# Le niveau humain intervient lorsque l'action,
# la décision ou la responsabilité ne peut pas
# être portée uniquement par l'IA.

SLACK_HIERARCHY_RULES = {
    "employee_to_manager": True,
    "manager_to_director": True,
    "director_to_general_director": True,
    "general_director_to_human_admin": True,
}


ESCALATION_REASONS = {
    "blocker",
    "approval",
    "financial",
    "legal",
    "security",
    "strategic",
    "cross_department",
    "ownership",
    "human_required",
    "technical",
    "operational",
    "deadline",
}


# Actions qui doivent pouvoir remonter vers un humain.
HUMAN_ESCALATION_ACTIONS = {
    "legal_signature",
    "bank_transfer",
    "shareholder_decision",
    "capital_operation",
    "high_value_contract",
    "official_filing",
    "employment_contract",
    "termination",
}


def get_channel(department_id: str) -> str:
    """
    Retourne le canal Slack associé au département.
    """
    return SLACK_CHANNELS.get(
        department_id,
        SLACK_CHANNELS["direction"],
    )


def is_valid_reason(reason: str | None) -> bool:
    """
    Vérifie qu'une raison d'escalade est connue.
    Une raison inconnue reste acceptable comme
    contexte libre, mais n'est pas classée.
    """
    if reason is None:
        return False

    return reason in ESCALATION_REASONS


def requires_human_escalation(action: str | None) -> bool:
    """
    Indique si une action appartient aux opérations
    nécessitant une intervention humaine.
    """
    if not action:
        return False

    return action in HUMAN_ESCALATION_ACTIONS
