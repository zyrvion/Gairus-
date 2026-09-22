import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.enterprise import EnterpriseEngine
from core.enterprise_roles import has_permission
from core.company_controller import CompanyController


def test_bootstrap():
    engine = EnterpriseEngine()

    assert engine.company["legal_form"] == "SARL"
    assert len(engine.departments) >= 10
    assert len(engine.employees) >= 1


def test_general_director():
    assert has_permission(
        "general_director",
        "manage_company",
    )

    assert has_permission(
        "general_director",
        "strategic_planning",
    )


def test_mission():
    engine = EnterpriseEngine()

    mission = engine.create_mission(
        title="Lancer une nouvelle activité",
        objective="Étudier et préparer le lancement",
    )

    assert mission["status"] == "pending"
    assert len(mission["steps"]) == 7


def test_controller():
    controller = CompanyController()

    gairus_id = next(
        employee_id
        for employee_id, employee in controller.enterprise.employees.items()
        if employee.name == "Gaïrus"
    )

    dashboard = controller.execute(
        gairus_id,
        "dashboard",
    )

    assert dashboard["company"]["name"] == "Entreprise Gaïrus"
    assert dashboard["employees"] >= 1


if __name__ == "__main__":
    test_bootstrap()
    test_general_director()
    test_mission()
    test_controller()

    print("=" * 60)
    print("GAÏRUS ENTERPRISE TESTS: OK")
    print("=" * 60)
