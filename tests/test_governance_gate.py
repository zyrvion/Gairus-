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

    approval = c.enterprise.request_approval(
        actor_id=actor.id,
        action="legal_signature",
    )

    assert approval["status"] == "pending"

    approver = next(
        e for e in c.enterprise.employees.values()
        if e.level >= 5 and e.id != actor.id
    )

    resolved = c.enterprise.resolve_approval(
        approval_id=approval["approval_id"],
        approver_id=approver.id,
        decision="approved",
        note="Approbation humaine de test",
    )

    assert resolved["status"] == "approved"

    result = c.require_governance(
        actor.id,
        "legal_signature",
    )

    assert result["status"] == "allowed"


if __name__ == "__main__":
    test_normal_action_allowed()
    test_sensitive_action_requires_approval()
    test_unapproved_sensitive_action_is_blocked()
    test_approved_sensitive_action_can_pass()
    print("GOVERNANCE GATE : OK")
