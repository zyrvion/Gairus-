ROLE_PERMISSIONS = {
    "employee": {
        "read",
        "create_content",
        "research",
        "report",
    },
    "manager": {
        "read",
        "create_content",
        "research",
        "report",
        "delegate",
        "coordinate",
        "manage_tasks",
    },
    "director": {
        "read",
        "create_content",
        "research",
        "report",
        "delegate",
        "coordinate",
        "manage_tasks",
        "manage_projects",
        "manage_kpis",
        "manage_department",
    },
    "general_director": {
        "read",
        "create_content",
        "research",
        "report",
        "delegate",
        "coordinate",
        "manage_tasks",
        "manage_projects",
        "manage_kpis",
        "manage_department",
        "manage_company",
        "strategic_planning",
        "request_approval",
    },
    "human_admin": {
        "*",
    },
}


def permissions_for(role):
    return sorted(ROLE_PERMISSIONS.get(role, set()))


def has_permission(role, permission):
    permissions = ROLE_PERMISSIONS.get(role, set())
    return "*" in permissions or permission in permissions


# Niveau hiérarchique minimal requis pour les actions Enterprise.
ACTION_MIN_LEVELS = {
    "read": 1,
    "plan": 1,
    "analyze": 1,
    "create_content": 1,
    "research": 1,
    "code": 1,
    "manage_documents": 2,
    "manage_projects": 2,
    "manage_workflows": 2,
    "delegate": 2,
    "manage_kpis": 2,
    "strategic_planning": 3,
    "manage_department": 3,
    "manage_budget": 3,
    "approve": 4,
    "company_management": 4,
    "legal_signature": 5,
    "bank_transfer": 5,
    "shareholder_decision": 5,
    "capital_operation": 5,
    "official_filing": 5,
    "employment_contract": 5,
    "termination": 5,
}


def minimum_level(action):
    return ACTION_MIN_LEVELS.get(action, 5)


def level_can_execute(level, action):
    return int(level) >= minimum_level(action)
