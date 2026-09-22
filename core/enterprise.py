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
    SENSITIVE_ACTIONS = {
        "legal_signature",
        "bank_transfer",
        "shareholder_decision",
        "capital_operation",
        "high_value_contract",
        "official_filing",
        "employment_contract",
        "termination",
    }


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

    def requires_human_approval(self, action, amount=None):
        if action in self.SENSITIVE_ACTIONS:
            return True

        if amount is not None:
            try:
                return float(amount) > 0
            except (TypeError, ValueError):
                return False

        return False

    def governance_check(self, actor_id, action, amount=None):
        actor = self.employees.get(actor_id)

        if actor is None:
            return {
                "status": "error",
                "message": "Acteur inconnu",
                "actor_id": actor_id,
            }

        if not self.requires_human_approval(action, amount):
            return {
                "status": "allowed",
                "actor_id": actor.id,
                "action": action,
                "approval_required": False,
            }

        existing = [
            approval
            for approval in getattr(self, "approvals", {}).values()
            if approval.get("actor_id") == actor.id
            and approval.get("action") == action
            and approval.get("status") == "approved"
        ]

        if existing:
            return {
                "status": "allowed",
                "actor_id": actor.id,
                "action": action,
                "approval_required": True,
                "approval": existing[-1],
            }

        return {
            "status": "approval_required",
            "actor_id": actor.id,
            "action": action,
            "approval_required": True,
        }

    def request_approval(
        self,
        actor_id,
        action,
        reason,
        mission_id=None,
        amount=None,
        target_level=None,
    ):
        actor = self.employees.get(actor_id)

        if actor is None:
            return {
                "status": "error",
                "message": "Acteur inconnu",
                "actor_id": actor_id,
            }

        if not hasattr(self, "approvals"):
            self.approvals = {}

        approval_id = f"APR-{len(self.approvals) + 1:06d}"

        # Les actions sensibles remontent automatiquement
        # vers le niveau humain lorsqu'elles concernent
        # une signature, un transfert ou une décision légale.
        human_actions = {
            "legal_signature",
            "bank_transfer",
            "shareholder_decision",
            "capital_operation",
            "high_value_contract",
            "official_filing",
            "employment_contract",
            "termination",
        }

        if action in human_actions:
            required_level = 5
        elif target_level is not None:
            required_level = target_level
        else:
            required_level = min(actor.level + 1, 5)

        candidates = [
            employee
            for employee in self.employees.values()
            if employee.level >= required_level
            and employee.id != actor.id
        ]

        candidates.sort(key=lambda employee: employee.level)

        if not candidates:
            return {
                "status": "error",
                "message": "Aucun approbateur disponible",
                "required_level": required_level,
            }

        approver = candidates[0]

        approval = {
            "id": approval_id,
            "actor_id": actor.id,
            "actor_name": actor.name,
            "actor_level": actor.level,
            "approver_id": approver.id,
            "approver_name": approver.name,
            "approver_level": approver.level,
            "action": action,
            "reason": reason,
            "mission_id": mission_id,
            "amount": amount,
            "status": "pending",
        }

        self.approvals[approval_id] = approval

        return {
            "status": "approval_required",
            "approval": approval,
        }

    def resolve_approval(
        self,
        approval_id,
        approver_id,
        decision,
        note=None,
    ):
        if not hasattr(self, "approvals"):
            self.approvals = {}

        approval = self.approvals.get(approval_id)

        if approval is None:
            return {
                "status": "error",
                "message": "Approbation inconnue",
                "approval_id": approval_id,
            }

        approver = self.employees.get(approver_id)

        if approver is None:
            return {
                "status": "error",
                "message": "Approbateur inconnu",
                "approver_id": approver_id,
            }

        if approver.id != approval["approver_id"] and approver.level < approval["approver_level"]:
            return {
                "status": "error",
                "message": "Approbateur non autorisé",
                "approver_id": approver.id,
            }

        if decision not in {"approved", "rejected"}:
            return {
                "status": "error",
                "message": "Décision invalide",
                "decision": decision,
            }

        approval["status"] = decision
        approval["resolved_by"] = approver.id
        approval["resolved_by_name"] = approver.name
        approval["note"] = note

        return {
            "status": "resolved",
            "approval": approval,
        }

    def escalate(self, actor_id, reason, action=None, mission_id=None, target_level=None):
        actor = self.employees.get(actor_id)

        if actor is None:
            return {
                "status": "error",
                "message": "Acteur inconnu",
                "actor_id": actor_id,
            }

        # Escalade suivant la chaîne manager_id réelle.
        chain = []
        current = actor

        while current.manager_id:
            manager = self.employees.get(current.manager_id)

            if manager is None:
                break

            chain.append(manager)
            current = manager

        if target_level is not None:
            candidates = [
                manager
                for manager in chain
                if manager.level >= target_level
            ]
        else:
            candidates = chain

        if not candidates:
            # Cas particulier : Gaïrus peut remonter vers l'administration
            # humaine lorsqu'aucun supérieur IA n'existe.
            candidates = [
                employee
                for employee in self.employees.values()
                if employee.level >= 5
                and employee.id != actor.id
            ]

        if not candidates:
            return {
                "status": "error",
                "message": "Aucun supérieur disponible pour l'escalade",
                "actor_id": actor.id,
                "actor_level": actor.level,
            }

        target = candidates[0]

        if target.level <= actor.level:
            return {
                "status": "error",
                "message": "La cible d'escalade doit être hiérarchiquement supérieure",
                "actor_id": actor.id,
                "actor_level": actor.level,
                "target_id": target.id,
                "target_level": target.level,
            }

        if not hasattr(self, "escalations"):
            self.escalations = {}

        escalation_id = f"ESC-{len(self.escalations) + 1:06d}"

        escalation = {
            "id": escalation_id,
            "actor_id": actor.id,
            "actor_name": actor.name,
            "actor_level": actor.level,
            "target_id": target.id,
            "target_name": target.name,
            "target_level": target.level,
            "reason": reason,
            "action": action,
            "mission_id": mission_id,
            "status": "pending",
            "chain": [
                {
                    "id": employee.id,
                    "name": employee.name,
                    "level": employee.level,
                }
                for employee in chain
            ],
        }

        self.escalations[escalation_id] = escalation

        return {
            "status": "escalated",
            "escalation": escalation,
        }

    def resolve_escalation(self, escalation_id, resolver_id, decision, note=None):
        if not hasattr(self, "escalations"):
            self.escalations = {}

        escalation = self.escalations.get(escalation_id)

        if escalation is None:
            return {
                "status": "error",
                "message": "Escalade inconnue",
                "escalation_id": escalation_id,
            }

        resolver = self.employees.get(resolver_id)

        if resolver is None:
            return {
                "status": "error",
                "message": "Décideur inconnu",
                "resolver_id": resolver_id,
            }

        if resolver.level < escalation["target_level"]:
            return {
                "status": "error",
                "message": "Niveau insuffisant pour résoudre cette escalade",
                "resolver_id": resolver.id,
                "resolver_level": resolver.level,
                "required_level": escalation["target_level"],
            }

        escalation["status"] = "resolved"
        escalation["resolved_by"] = resolver.id
        escalation["resolved_by_name"] = resolver.name
        escalation["decision"] = decision
        escalation["note"] = note

        return {
            "status": "resolved",
            "escalation": escalation,
        }

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
