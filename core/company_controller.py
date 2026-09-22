from core.governance_gate import GovernanceGate\nfrom typing import Any, Dict

from core.enterprise import EnterpriseEngine
from core.enterprise_roles import has_permission


class CompanyController:
    """
    Contrôleur central de l'entreprise.

    Important:
    Le contrôleur possède UNE instance EnterpriseEngine.
    Les identifiants d'employés utilisés par execute()
    doivent donc provenir de cette même instance.
    """

    LEVEL_TO_ROLE = {
        1: "employee",
        2: "manager",
        3: "director",
        4: "general_director",
        5: "human_admin",
    }

    def __init__(self, enterprise=None):
        self.enterprise = enterprise or EnterpriseEngine()
        self.governance_gate = GovernanceGate(self.enterprise)

    def _get_employee(self, actor_id):
        """
        Recherche l'acteur dans l'instance EnterpriseEngine
        actuellement utilisée par le contrôleur.
        """
        return self.enterprise.employees.get(actor_id)

    def _permission(self, employee, permission):
        role = self.LEVEL_TO_ROLE.get(employee.level)

        if not role:
            return False

        return has_permission(role, permission)

    def governance(self, actor_id, requested_action, amount=None):
        return self.enterprise.governance_check(
            actor_id=actor_id,
            action=requested_action,
            amount=amount,
        )


    def require_governance(self, actor_id, action, amount=None):
        """
        Point d'entrée unique pour les modules Enterprise.
        Lève GovernanceBlocked si l'action n'est pas autorisée.
        """
        return self.governance_gate.check(
            actor_id=actor_id,
            action=action,
            amount=amount,
            require_approval=True,
        )

    def execute(self, actor_id: str, action: str, **kwargs) -> Dict[str, Any]:
        employee = self._get_employee(actor_id)

        if employee is None:
            return {
                "status": "error",
                "message": "Acteur inconnu",
                "actor_id": actor_id,
            }

        action_permissions = {
            "dashboard": "read",
            "org_chart": "read",
            "create_mission": "manage_projects",
            "delegate": "delegate",
            "create_content": "create_content",
            "update_kpi": "manage_kpis",
        }

        permission = action_permissions.get(action)

        if action == "governance":
            return self.governance(
                actor_id=employee.id,
                requested_action=kwargs.get("requested_action"),
                amount=kwargs.get("amount"),
            )

        if permission is None:
            return {
                "status": "error",
                "message": "Action inconnue",
                "action": action,
            }
        if action == "governance":
            return self.governance(
                actor_id=employee.id,
                requested_action=kwargs.get("requested_action"),
                amount=kwargs.get("amount"),
            )


        if not self._permission(employee, permission):
            return {
                "status": "denied",
                "message": "Permission insuffisante",
                "actor_id": actor_id,
                "action": action,
                "required_permission": permission,
            }

        if action == "dashboard":
            return {
                "status": "ok",
                "company": dict(self.enterprise.company),
                "employees": len(self.enterprise.employees),
                "departments": len(self.enterprise.departments),
                "missions": len(self.enterprise.missions),
                "kpis": dict(self.enterprise.kpis),
                "actor": {
                    "id": employee.id,
                    "name": employee.name,
                    "role": employee.role,
                    "level": employee.level,
                },
            }

        if action == "org_chart":
            return {
                "status": "ok",
                "org_chart": self.enterprise.get_org_chart(),
            }

        if action == "create_mission":
            mission = self.enterprise.create_mission(
                title=kwargs["title"],
                objective=kwargs["objective"],
                department_id=kwargs.get(
                    "department_id",
                    employee.department,
                ),
                priority=kwargs.get(
                    "priority",
                    "medium",
                ),
                owner_id=employee.id,
            )

            return {
                "status": "ok",
                "mission": mission,
            }

        if action == "delegate":
            delegation = self.enterprise.delegate(
                mission_id=kwargs["mission_id"],
                employee_id=kwargs["employee_id"],
            )

            if delegation.get("status") == "error":
                return delegation

            return {
                "status": "ok",
                "delegation": delegation,
            }

        if action == "create_content":
            from core.content_engine import ContentEngine

            content_engine = ContentEngine()

            content = content_engine.create(
                content_type=kwargs["content_type"],
                title=kwargs["title"],
                content=kwargs.get("content", ""),
            )

            return {
                "status": "ok",
                "content": content,
            }

        if action == "update_kpi":
            result = self.enterprise.update_kpi(
                department_id=kwargs["department_id"],
                name=kwargs["name"],
                value=kwargs["value"],
            )

            return {
                "status": "ok",
                "kpi": result,
            }

        return {
            "status": "error",
            "message": "Action non implémentée",
            "action": action,
        }
