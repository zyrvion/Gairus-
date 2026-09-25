from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


LEVELS = {
    "employee": 1,
    "manager": 2,
    "director": 3,
    "general_director": 4,
    "human_admin": 5,
}


DEPARTMENTS = {
    "direction": {
        "name": "Direction Générale",
        "channel": "#direction",
    },
    "finance": {
        "name": "Finance",
        "channel": "#finance",
    },
    "commercial": {
        "name": "Commercial",
        "channel": "#commercial",
    },
    "marketing": {
        "name": "Marketing",
        "channel": "#marketing",
    },
    "technique": {
        "name": "Technique",
        "channel": "#technique",
    },
    "operations": {
        "name": "Operations",
        "channel": "#operations",
    },
    "rh": {
        "name": "Ressources Humaines",
        "channel": "#rh",
    },
    "juridique": {
        "name": "Juridique",
        "channel": "#juridique",
    },
    "recherche": {
        "name": "Recherche & Innovation",
        "channel": "#recherche",
    },
    "support": {
        "name": "Support",
        "channel": "#support",
    },
    "projets": {
        "name": "Projets",
        "channel": "#projets",
    },
}


@dataclass
class HierarchyNode:
    actor_id: str
    name: str
    role: str
    level: int
    department_id: str
    manager_id: Optional[str] = None
    slack_user_id: Optional[str] = None
    active: bool = True
    permissions: List[str] = field(default_factory=list)

    @property
    def level_name(self) -> str:
        for name, value in LEVELS.items():
            if value == self.level:
                return name
        return "unknown"


class HierarchyEngine:
    """
    Moteur hiérarchique de Gaïrus.

    Il détermine :
    - qui dépend de qui ;
    - qui peut déléguer à qui ;
    - vers qui une situation doit être escaladée ;
    - quel responsable doit être contacté ;
    - la structure complète de l'organisation.
    """

    def __init__(self, enterprise=None):
        self.enterprise = enterprise
        self.nodes: Dict[str, HierarchyNode] = {}

        self._load_enterprise()

    def _load_enterprise(self):
        if self.enterprise is None:
            return

        employees = getattr(
            self.enterprise,
            "employees",
            {},
        )

        if not isinstance(employees, dict):
            return

        for actor_id, employee in employees.items():
            self.register(
                actor_id=actor_id,
                name=getattr(employee, "name", actor_id),
                role=getattr(employee, "role", "employee"),
                level=getattr(employee, "level", 1),
                department_id=getattr(
                    employee,
                    "department_id",
                    "direction",
                ),
                manager_id=getattr(
                    employee,
                    "manager_id",
                    None,
                ),
                slack_user_id=getattr(
                    employee,
                    "slack_user_id",
                    None,
                ),
                permissions=getattr(
                    employee,
                    "permissions",
                    [],
                ),
            )

    def register(
        self,
        actor_id: str,
        name: str,
        role: str,
        level,
        department_id: str,
        manager_id: Optional[str] = None,
        slack_user_id: Optional[str] = None,
        permissions=None,
    ) -> HierarchyNode:

        if isinstance(level, str):
            level = LEVELS.get(
                level.lower(),
                LEVELS["employee"],
            )

        if department_id not in DEPARTMENTS:
            department_id = "direction"

        node = HierarchyNode(
            actor_id=actor_id,
            name=name,
            role=role,
            level=int(level),
            department_id=department_id,
            manager_id=manager_id,
            slack_user_id=slack_user_id,
            permissions=list(permissions or []),
        )

        self.nodes[actor_id] = node

        return node

    def remove(self, actor_id: str):
        return self.nodes.pop(actor_id, None)

    def get(self, actor_id: str):
        return self.nodes.get(actor_id)

    def exists(self, actor_id: str) -> bool:
        return actor_id in self.nodes

    def manager(self, actor_id: str):
        node = self.get(actor_id)

        if node is None:
            return None

        if not node.manager_id:
            return None

        return self.get(node.manager_id)

    def subordinates(self, actor_id: str):
        return [
            node
            for node in self.nodes.values()
            if node.active
            and node.manager_id == actor_id
        ]

    def same_department(self, actor_a: str, actor_b: str):
        a = self.get(actor_a)
        b = self.get(actor_b)

        if not a or not b:
            return False

        return a.department_id == b.department_id

    def can_manage(
        self,
        manager_id: str,
        employee_id: str,
    ) -> bool:

        manager = self.get(manager_id)
        employee = self.get(employee_id)

        if not manager or not employee:
            return False

        if not manager.active or not employee.active:
            return False

        if manager_id == employee_id:
            return False

        return manager.level > employee.level

    def can_delegate(
        self,
        delegator_id: str,
        employee_id: str,
    ) -> bool:

        return self.can_manage(
            delegator_id,
            employee_id,
        )

    def chain(self, actor_id: str):
        """
        Retourne l'acteur puis toute sa chaîne hiérarchique.
        """

        result = []
        current = self.get(actor_id)
        visited = set()

        while current is not None:
            if current.actor_id in visited:
                break

            visited.add(current.actor_id)
            result.append(current)

            if not current.manager_id:
                break

            current = self.get(
                current.manager_id
            )

        return result

    def ancestors(self, actor_id: str):
        chain = self.chain(actor_id)

        if len(chain) <= 1:
            return []

        return chain[1:]

    def descendants(self, actor_id: str):
        result = []
        queue = list(
            self.subordinates(actor_id)
        )
        visited = set()

        while queue:
            node = queue.pop(0)

            if node.actor_id in visited:
                continue

            visited.add(node.actor_id)
            result.append(node)

            queue.extend(
                self.subordinates(node.actor_id)
            )

        return result

    def escalation_target(
        self,
        actor_id: str,
        reason: Optional[str] = None,
    ):
        """
        Règle principale :

        employee
            → manager

        manager
            → director

        director
            → general_director

        general_director
            → human_admin si une intervention humaine
              est nécessaire.
        """

        node = self.get(actor_id)

        if node is None:
            return None

        manager = self.manager(actor_id)

        if manager and manager.active:
            return manager

        higher_same_department = [
            candidate
            for candidate in self.nodes.values()
            if candidate.active
            and candidate.department_id == node.department_id
            and candidate.level > node.level
        ]

        if higher_same_department:
            return sorted(
                higher_same_department,
                key=lambda item: item.level,
            )[0]

        higher_global = [
            candidate
            for candidate in self.nodes.values()
            if candidate.active
            and candidate.level > node.level
        ]

        if higher_global:
            return sorted(
                higher_global,
                key=lambda item: item.level,
            )[0]

        return None

    def route(
        self,
        actor_id: str,
        reason: Optional[str] = None,
    ):
        node = self.get(actor_id)

        if node is None:
            return {
                "status": "unknown_actor",
                "actor_id": actor_id,
                "target": None,
            }

        target = self.escalation_target(
            actor_id,
            reason,
        )

        return {
            "status": "ok",
            "actor_id": actor_id,
            "actor_name": node.name,
            "actor_level": node.level,
            "actor_level_name": node.level_name,
            "department_id": node.department_id,
            "department_name": DEPARTMENTS[
                node.department_id
            ]["name"],
            "channel": DEPARTMENTS[
                node.department_id
            ]["channel"],
            "reason": reason,
            "target_actor_id": (
                target.actor_id
                if target
                else None
            ),
            "target_name": (
                target.name
                if target
                else None
            ),
            "target_level": (
                target.level
                if target
                else None
            ),
            "target_slack_user_id": (
                target.slack_user_id
                if target
                else None
            ),
        }

    def org_chart(self):
        return [
            {
                "actor_id": node.actor_id,
                "name": node.name,
                "role": node.role,
                "level": node.level,
                "level_name": node.level_name,
                "department_id": node.department_id,
                "manager_id": node.manager_id,
                "slack_user_id": node.slack_user_id,
                "active": node.active,
                "permissions": list(
                    node.permissions
                ),
            }
            for node in self.nodes.values()
        ]

    def department_members(
        self,
        department_id: str,
    ):
        return [
            node
            for node in self.nodes.values()
            if node.active
            and node.department_id == department_id
        ]

    def directors(self):
        return [
            node
            for node in self.nodes.values()
            if node.active
            and node.level >= LEVELS["director"]
        ]

    def human_admins(self):
        return [
            node
            for node in self.nodes.values()
            if node.active
            and node.level >= LEVELS["human_admin"]
        ]

    def summary(self):
        return {
            "total_actors": len(self.nodes),
            "active_actors": sum(
                1
                for node in self.nodes.values()
                if node.active
            ),
            "departments": len(DEPARTMENTS),
            "directors": len(self.directors()),
            "human_admins": len(
                self.human_admins()
            ),
        }
