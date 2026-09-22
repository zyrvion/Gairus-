from core.enterprise import EnterpriseEngine
from core.enterprise_roles import has_permission


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


def test_mission():
    engine = EnterpriseEngine()

    mission = engine.create_mission(
        title="Lancer une nouvelle activité",
        objective="Étudier et préparer le lancement",
    )

    assert mission["status"] == "pending"
    assert len(mission["steps"]) == 7


if __name__ == "__main__":
    test_bootstrap()
    test_general_director()
    test_mission()
    print("ENTERPRISE TESTS: OK")
