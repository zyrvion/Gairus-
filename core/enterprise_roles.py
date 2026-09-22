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
