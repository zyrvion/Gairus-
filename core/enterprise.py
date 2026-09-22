from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


def now():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Employee:
    id: str
    name: str
    role: str
    department: str
    level: int
    manager_id: Optional[str] = None
    permissions: list = field(default_factory=list)
    active: bool = True


@dataclass
class Department:
    id: str
    name: str
    director_role: str
    parent_id: Optional[str] = None
    employees: list = field(default_factory=list)


@dataclass
class Mission:
    id: str
    title: str
    objective: str
    owner_id: Optional[str] = None
    department_id: Optional[str] = None
    priority: str = "normal"
    status: str = "pending"
    created_at: str = field(default_factory=now)
    steps: list = field(default_factory=list)


class EnterpriseEngine:
    LEVELS = {
        "employee": 1,
        "manager": 2,
        "director": 3,
        "general_director": 4,
        "human_admin": 5,
    }

    def __init__(self):
        self.company = {
            "name": "Entreprise Gaïrus",
            "legal_form": "SARL",
            "status": "operational",
            "created_at": now(),
        }
        self.departments = {}
        self.employees = {}
        self.missions = {}
        self.kpis = {}
        self._bootstrap()

    def _id(self, prefix):
        return f"{prefix}_{uuid.uuid4().hex[:10]}"

    def _bootstrap(self):
        departments = [
            ("direction", "Direction Générale", "Directeur Général"),
            ("finance", "Administration & Finance", "Directeur Administratif et Financier"),
            ("commercial", "Direction Commerciale", "Directeur Commercial"),
            ("marketing", "Marketing & Communication", "Directeur Marketing"),
            ("technique", "Direction Technique", "Directeur Technique"),
            ("operations", "Opérations", "Directeur des Opérations"),
            ("rh", "Ressources Humaines", "Directeur des Ressources Humaines"),
            ("juridique", "Juridique & Conformité", "Responsable Juridique"),
            ("innovation", "Recherche & Innovation", "Directeur Innovation"),
            ("support", "Support & Relation Client", "Responsable Support"),
        ]

        for dep_id, name, director in departments:
            self.departments[dep_id] = Department(
                id=dep_id,
                name=name,
                director_role=director,
            )

        self.add_employee(
            name="Gaïrus",
            role="Directeur Général IA",
            department="direction",
            level="general_director",
            permissions=[
                "read",
                "plan",
                "delegate",
                "coordinate",
                "analyze",
                "create_content",
                "research",
                "code",
                "manage_projects",
                "manage_documents",
                "manage_kpis",
                "manage_workflows",
                "strategic_planning",
                "request_approval",
            ],
        )

    def add_employee(
        self,
        name,
        role,
        department,
        level="employee",
        manager_id=None,
        permissions=None,
    ):
        if department not in self.departments:
            raise ValueError(f"Département inconnu: {department}")

        employee_id = self._id("emp")

        employee = Employee(
            id=employee_id,
            name=name,
            role=role,
            department=department,
            level=self.LEVELS[level],
            manager_id=manager_id,
            permissions=permissions or [],
        )

        self.employees[employee_id] = employee
        self.departments[department].employees.append(employee_id)

        return employee.__dict__

    def create_mission(
        self,
        title,
        objective,
        owner_id=None,
        department_id=None,
        priority="normal",
    ):
        mission_id = self._id("mission")

        steps = [
            {"id": 1, "action": "analyze", "status": "pending"},
            {"id": 2, "action": "plan", "status": "pending"},
            {"id": 3, "action": "delegate", "status": "pending"},
            {"id": 4, "action": "execute", "status": "pending"},
            {"id": 5, "action": "verify", "status": "pending"},
            {"id": 6, "action": "report", "status": "pending"},
            {"id": 7, "action": "remember", "status": "pending"},
        ]

        mission = Mission(
            id=mission_id,
            title=title,
            objective=objective,
            owner_id=owner_id,
            department_id=department_id,
            priority=priority,
            steps=steps,
        )

        self.missions[mission_id] = mission
        return mission.__dict__

    def delegate(self, mission_id, employee_id, delegator_id=None):
        mission = self.missions.get(mission_id)
        if mission is None:
            return {
                "status": "error",
                "message": "Mission inconnue",
                "mission_id": mission_id,
            }

        employee = self.employees.get(employee_id)
        if employee is None:
            return {
                "status": "error",
                "message": "Employé inconnu",
                "employee_id": employee_id,
            }

        if delegator_id is not None:
            delegator = self.employees.get(delegator_id)

            if delegator is None:
                return {
                    "status": "error",
                    "message": "Délégateur inconnu",
                    "delegator_id": delegator_id,
                }

            if delegator.level < 2:
                return {
                    "status": "error",
                    "message": "Niveau hiérarchique insuffisant pour déléguer",
                    "delegator_id": delegator_id,
                    "delegator_level": delegator.level,
                }

            if employee.level >= delegator.level:
                return {
                    "status": "error",
                    "message": "Une délégation doit descendre dans la hiérarchie",
                    "delegator_id": delegator.id,
                    "delegator_level": delegator.level,
                    "employee_id": employee.id,
                    "employee_level": employee.level,
                }

        mission["assignee_id"] = employee_id
        mission["assigned_to"] = employee.name
        mission["status"] = "assigned"

        if delegator_id is not None:
            mission["delegated_by"] = delegator_id

        for step in mission.get("steps", []):
            if step["action"] == "delegate":
                step["status"] = "completed"

        return {
            "status": "delegated",
            "mission_id": mission_id,
            "owner_id": mission.get("owner_id"),
            "delegated_by": delegator_id,
            "employee_id": employee_id,
            "employee_name": employee.name,
        }

    def can_act(self, employee_id, permission):
        employee = self.employees.get(employee_id)

        if not employee or not employee.active:
            return False

        return permission in employee.permissions

    def update_kpi(self, name, value, target=None):
        self.kpis[name] = {
            "value": value,
            "target": target,
            "updated_at": now(),
        }

        return self.kpis[name]

    def get_org_chart(self):
        return {
            "company": self.company,
            "departments": {
                key: value.__dict__
                for key, value in self.departments.items()
            },
            "employees": {
                key: value.__dict__
                for key, value in self.employees.items()
            },
        }

    def dashboard(self):
        return {
            "company": self.company,
            "employees": len(self.employees),
            "departments": len(self.departments),
            "missions": len(self.missions),
            "kpis": self.kpis,
            "active_missions": [
                mission.__dict__
                for mission in self.missions.values()
                if mission.status not in {"completed", "cancelled"}
            ],
        }
