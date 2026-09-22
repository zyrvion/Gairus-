from core.company_controller import CompanyController
from core.action_gateway import ActionGateway
from core.governance_gate import GovernanceBlocked


def get_gairus(c):
    for employee in c.enterprise.employees.values():
        if "gaïrus" in employee.name.lower() or "gairus" in employee.name.lower():
            return employee
    raise AssertionError("Gaïrus introuvable")


def test_normal_action():
    c = CompanyController()
    actor = get_gairus(c)

    result = c.require_governance(
        actor.id,
        "create_content",
    )

    assert result["status"] == "allowed"


def test_sensitive_action_blocked():
    c = CompanyController()
    actor = get_gairus(c)

    try:
        c.require_governance(
            actor.id,
            "legal_signature",
        )
    except GovernanceBlocked:
        return

    raise AssertionError(
        "legal_signature non approuvée a traversé la barrière"
    )


def test_bank_transfer_blocked():
    c = CompanyController()
    actor = get_gairus(c)

    try:
        c.require_governance(
            actor.id,
            "bank_transfer",
            amount=100000,
        )
    except GovernanceBlocked:
        return

    raise AssertionError(
        "bank_transfer non approuvé a traversé la barrière"
    )


def test_tool_mapping():
    c = CompanyController()
    actor = get_gairus(c)

    gateway = ActionGateway(
        enterprise=c.enterprise,
        controller=c,
    )

    try:
        gateway.authorize_tool(
            actor_id=actor.id,
            tool="bank_transfer",
            amount=100000,
        )
    except GovernanceBlocked:
        return

    raise AssertionError(
        "tool bank_transfer a traversé la barrière"
    )


def test_normal_tool():
    c = CompanyController()
    actor = get_gairus(c)

    gateway = ActionGateway(
        enterprise=c.enterprise,
        controller=c,
    )

    result = gateway.authorize_tool(
        actor_id=actor.id,
        tool="create_content",
    )

    assert result["status"] == "allowed"


if __name__ == "__main__":
    test_normal_action()
    test_sensitive_action_blocked()
    test_bank_transfer_blocked()
    test_tool_mapping()
    test_normal_tool()
    print("EXECUTION GOVERNANCE : OK")
