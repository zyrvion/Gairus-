from core.company_controller import CompanyController
from core.governance_gate import GovernanceBlocked


def get_gairus(controller):
    for employee in controller.enterprise.employees.values():
        if "gaïrus" in employee.name.lower() or "gairus" in employee.name.lower():
            return employee
    raise AssertionError("Gaïrus introuvable")


def test_normal_action_allowed():
    c = CompanyController()
    actor = get_gairus(c)

    result = c.governance(
        actor.id,
        "create_content",
    )

    assert result["status"] == "allowed"
    assert result["approval_required"] is False


def test_sensitive_action_requires_approval():
    c = CompanyController()
    actor = get_gairus(c)

    result = c.governance(
        actor.id,
        "legal_signature",
    )

    assert result["status"] == "approval_required"
    assert result["approval_required"] is True


def test_unapproved_sensitive_action_is_blocked():
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
        "Une signature juridique non approuvée a traversé la gouvernance"
    )


def test_approved_sensitive_action_can_pass():
    c = CompanyController()
    actor = get_gairus(c)
    # A test fixture is not a production human account or an automatic approval.
    human = c.enterprise.add_employee(
        name="Test human approver", role="Owner", department="direction",
        level="human_admin",
    )

    approval = c.enterprise.request_approval(
        actor_id=actor.id,
        action="legal_signature",
    )

    assert approval["status"] == "approval_required"
    assert approval["approval"]["status"] == "pending"

    approver = c.enterprise.employees[human["id"]]

    resolved = c.enterprise.resolve_approval(
        approval_id=approval["approval"]["id"],
        approver_id=approver.id,
        decision="approved",
        note="Approbation humaine de test",
    )

    assert resolved["status"] == "resolved"
    assert resolved["approval"]["status"] == "approved"

    result = c.require_governance(
        actor.id,
        "legal_signature",
    )

    assert result["status"] == "allowed"


def test_sensitive_approval_requires_a_real_human():
    c = CompanyController()
    actor = get_gairus(c)
    approval = c.enterprise.request_approval(actor.id, "legal_signature")
    assert approval["status"] == "error"
    assert approval["required_level"] == 5


def test_inactive_human_cannot_approve():
    c = CompanyController()
    actor = get_gairus(c)
    human = c.enterprise.add_employee(
        name="Test human", role="Owner", department="direction", level="human_admin",
    )
    approval = c.enterprise.request_approval(actor.id, "legal_signature")
    c.enterprise.employees[human["id"]].active = False
    resolved = c.enterprise.resolve_approval(
        approval["approval"]["id"], human["id"], "approved",
    )
    assert resolved["status"] == "error"


if __name__ == "__main__":
    test_normal_action_allowed()
    test_sensitive_action_requires_approval()
    test_unapproved_sensitive_action_is_blocked()
    test_approved_sensitive_action_can_pass()
    print("GOVERNANCE GATE : OK")
