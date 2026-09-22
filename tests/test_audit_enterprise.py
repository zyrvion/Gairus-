from pathlib import Path
import tempfile

from security.audit import AuditLogger
from core.company_controller import CompanyController
from core.action_gateway import ActionGateway
from core.governance_gate import GovernanceBlocked


def get_gairus(c):
    for employee in c.enterprise.employees.values():
        if "gaïrus" in employee.name.lower() or "gairus" in employee.name.lower():
            return employee
    raise AssertionError("Gaïrus introuvable")


def test_audit_logger():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "audit.jsonl"
        logger = AuditLogger(path)

        record = logger.log(
            event="test",
            actor_id="actor-1",
            actor_name="Gaïrus",
            actor_level=4,
            department_id="direction",
            department_name="Direction Générale",
            action="create_content",
            tool="content",
            status="allowed",
            authorization={"status": "allowed"},
            result={"ok": True},
        )

        assert record["event"] == "test"
        assert record["actor"]["id"] == "actor-1"
        assert record["action"] == "create_content"
        assert path.exists()

        records = logger.read()
        assert len(records) == 1
        assert records[0]["actor"]["name"] == "Gaïrus"


def test_gateway_audits_allowed_action():
    c = CompanyController()
    actor = get_gairus(c)

    gateway = ActionGateway(
        enterprise=c.enterprise,
        controller=c,
    )

    result = gateway.authorize(
        actor_id=actor.id,
        action="create_content",
    )

    assert result["status"] == "allowed"

    records = gateway.audit_gateway.audit.search(
        actor_id=actor.id,
        action="create_content",
    )

    assert records
    assert records[-1]["status"] == "allowed"


def test_gateway_audits_blocked_action():
    c = CompanyController()
    actor = get_gairus(c)

    gateway = ActionGateway(
        enterprise=c.enterprise,
        controller=c,
    )

    try:
        gateway.authorize(
            actor_id=actor.id,
            action="legal_signature",
        )
    except GovernanceBlocked:
        pass
    else:
        raise AssertionError("Action sensible non bloquée")

    records = gateway.audit_gateway.audit.search(
        actor_id=actor.id,
        action="legal_signature",
        status="blocked",
    )

    assert records
    assert records[-1]["status"] == "blocked"


if __name__ == "__main__":
    test_audit_logger()
    test_gateway_audits_allowed_action()
    test_gateway_audits_blocked_action()
    print("AUDIT ENTERPRISE : OK")
