from .enterprise import EnterpriseEngine
from .enterprise_roles import has_permission
from .content_engine import ContentEngine


class CompanyController:
    def __init__(self):
        self.enterprise = EnterpriseEngine()
        self.content = ContentEngine()

    def _role_from_level(self, level):
        mapping = {
            1: "employee",
            2: "manager",
            3: "director",
            4: "general_director",
            5: "human_admin",
        }
        return mapping.get(level, "employee")

    def execute(self, actor_id, action, **kwargs):
        employee = self.enterprise.employees.get(actor_id)

        if not employee:
            return {
                "status": "error",
                "message": "Acteur inconnu",
            }

        role = self._role_from_level(employee.level)

        required = {
            "create_mission": "delegate",
            "delegate": "delegate",
            "create_content": "create_content",
            "update_kpi": "manage_kpis",
            "dashboard": "read",
            "org_chart": "read",
        }.get(action, "read")

        if not has_permission(role, required):
            return {
                "status": "permission_denied",
                "action": action,
                "required_permission": required,
                "role": role,
            }

        if action == "create_mission":
            return self.enterprise.create_mission(**kwargs)

        if action == "delegate":
            return self.enterprise.delegate(**kwargs)

        if action == "create_content":
            return self.content.create(**kwargs)

        if action == "update_kpi":
            return self.enterprise.update_kpi(**kwargs)

        if action == "dashboard":
            return self.enterprise.dashboard()

        if action == "org_chart":
            return self.enterprise.get_org_chart()

        return {
            "status": "completed",
            "action": action,
        }
