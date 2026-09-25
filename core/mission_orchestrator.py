from __future__ import annotations

from typing import Any, Dict, List, Optional


class MissionOrchestrator:
    """
    Orchestrateur central des missions de Gaïrus.

    Responsabilités :
    - créer une mission ;
    - suivre son état ;
    - déléguer les étapes ;
    - escalader les blocages ;
    - conserver la gouvernance Enterprise comme autorité finale.

    L'orchestrateur ne contourne jamais Executor, ActionGateway
    ou GovernanceGate pour exécuter une action sensible.
    """

    VALID_STATUSES = {
        "planned",
        "queued",
        "running",
        "blocked",
        "waiting_approval",
        "completed",
        "failed",
        "cancelled",
    }

    def __init__(self, enterprise=None, executor=None, controller=None, hierarchy=None):
        self.enterprise = enterprise
        self.executor = executor
        self.controller = controller
        self.hierarchy = hierarchy

        self._missions: Dict[str, Dict[str, Any]] = {}

        self._load_existing_missions()

    def _load_existing_missions(self):
        """
        Charge les missions déjà présentes dans EnterpriseEngine
        lorsque celui-ci expose un registre de missions.
        """
        if self.enterprise is None:
            return

        missions = getattr(self.enterprise, "missions", None)

        if isinstance(missions, dict):
            for mission_id, mission in missions.items():
                if isinstance(mission, dict):
                    self._missions[mission_id] = mission
                else:
                    self._missions[mission_id] = self._serialize(mission)

    def _serialize(self, value):
        if value is None:
            return None

        if isinstance(value, dict):
            return dict(value)

        if hasattr(value, "__dict__"):
            return dict(value.__dict__)

        return value

    def _mission(self, mission_id: str) -> Optional[Dict[str, Any]]:
        return self._missions.get(mission_id)

    def get(self, mission_id: str) -> Optional[Dict[str, Any]]:
        mission = self._mission(mission_id)

        if mission is None:
            return None

        return dict(mission)

    def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        missions = list(self._missions.values())

        if status is not None:
            missions = [
                mission
                for mission in missions
                if mission.get("status") == status
            ]

        return [dict(mission) for mission in missions]

    def create(
        self,
        actor_id: str,
        title: str,
        objective: Optional[str] = None,
        department_id: Optional[str] = None,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not actor_id:
            raise ValueError("actor_id is required")

        if not title:
            raise ValueError("Mission title is required")

        if self.enterprise is None:
            raise RuntimeError("EnterpriseEngine is not configured")

        metadata = metadata or {}

        mission = None

        try:
            mission = self.enterprise.create_mission(
                actor_id=actor_id,
                title=title,
                objective=objective,
                department_id=department_id,
                priority=priority,
            )
        except TypeError:
            try:
                mission = self.enterprise.create_mission(
                    actor_id=actor_id,
                    title=title,
                    objective=objective,
                    department_id=department_id,
                )
            except TypeError:
                mission = self.enterprise.create_mission(
                    actor_id=actor_id,
                    title=title,
                    objective=objective,
                )

        mission_data = self._serialize(mission)

        if not isinstance(mission_data, dict):
            mission_data = {
                "mission_id": getattr(mission, "id", None),
                "title": title,
                "objective": objective,
                "department_id": department_id,
                "priority": priority,
                "actor_id": actor_id,
            }

        mission_id = (
            mission_data.get("mission_id")
            or mission_data.get("id")
        )

        if not mission_id:
            mission_id = f"mission-{len(self._missions) + 1}"

        mission_data["mission_id"] = mission_id
        mission_data.setdefault("title", title)
        mission_data.setdefault("objective", objective)
        mission_data.setdefault("department_id", department_id)
        mission_data.setdefault("priority", priority)
        mission_data.setdefault("actor_id", actor_id)
        mission_data.setdefault("status", "planned")
        mission_data.setdefault("metadata", metadata)

        self._missions[mission_id] = mission_data

        return dict(mission_data)

    def update_status(
        self,
        mission_id: str,
        status: str,
        note: Optional[str] = None,
        result: Any = None,
    ) -> Dict[str, Any]:
        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid mission status: {status}"
            )

        mission = self._mission(mission_id)

        if mission is None:
            raise KeyError(f"Unknown mission: {mission_id}")

        mission["status"] = status

        if note is not None:
            mission["status_note"] = note

        if result is not None:
            mission["result"] = result

        return dict(mission)

    def start(self, mission_id: str) -> Dict[str, Any]:
        return self.update_status(
            mission_id,
            "running",
        )

    def block(
        self,
        mission_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        return self.update_status(
            mission_id,
            "blocked",
            note=reason,
        )

    def wait_for_approval(
        self,
        mission_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.update_status(
            mission_id,
            "waiting_approval",
            note=reason,
        )

    def complete(
        self,
        mission_id: str,
        result: Any = None,
    ) -> Dict[str, Any]:
        return self.update_status(
            mission_id,
            "completed",
            result=result,
        )

    def fail(
        self,
        mission_id: str,
        error: str,
    ) -> Dict[str, Any]:
        return self.update_status(
            mission_id,
            "failed",
            note=error,
        )

    def cancel(
        self,
        mission_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.update_status(
            mission_id,
            "cancelled",
            note=reason,
        )

    def delegate(
        self,
        mission_id: str,
        employee_id: str,
        delegator_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.enterprise is None:
            raise RuntimeError("EnterpriseEngine is not configured")

        mission = self._mission(mission_id)

        if mission is None:
            raise KeyError(f"Unknown mission: {mission_id}")

        result = self.enterprise.delegate(
            mission_id=mission_id,
            employee_id=employee_id,
            delegator_id=delegator_id,
        )

        mission["delegated_to"] = employee_id

        if delegator_id:
            mission["delegated_by"] = delegator_id

        mission["delegation_result"] = self._serialize(result)

        return dict(mission)

    def escalate(
        self,
        mission_id: str,
        actor_id: str,
        reason: str,
        target_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.enterprise is None:
            raise RuntimeError("EnterpriseEngine is not configured")

        mission = self._mission(mission_id)

        if mission is None:
            raise KeyError(f"Unknown mission: {mission_id}")

        result = self.enterprise.escalate(
            actor_id=actor_id,
            reason=reason,
            mission_id=mission_id,
            target_level=target_level,
        )

        mission["status"] = "blocked"
        mission["escalation_reason"] = reason
        mission["escalation"] = self._serialize(result)

        return dict(mission)

    def execute_step(
        self,
        mission_id: str,
        actor_id: str,
        action: str,
        handler=None,
        tool: Optional[str] = None,
        amount: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Exécute une étape d'une mission via Executor.

        Toute gouvernance, autorisation, approbation et audit
        restent dans la chaîne Executor -> ActionGateway ->
        GovernanceGate.
        """
        mission = self._mission(mission_id)

        if mission is None:
            raise KeyError(f"Unknown mission: {mission_id}")

        if self.executor is None:
            raise RuntimeError("Executor is not configured")

        self.start(mission_id)

        try:
            result = self.executor.execute(
                action=action,
                handler=handler,
                actor_id=actor_id,
                tool=tool,
                amount=amount,
                mission_id=mission_id,
                metadata=metadata,
                **kwargs,
            )

            if isinstance(result, dict):
                status = result.get("status")

                if status in {
                    "approval_required",
                    "waiting_approval",
                }:
                    self.wait_for_approval(
                        mission_id,
                        result.get("message"),
                    )

                elif status in {
                    "blocked",
                    "denied",
                    "forbidden",
                }:
                    self.block(
                        mission_id,
                        result.get("error")
                        or result.get("message")
                        or "Mission blocked",
                    )

            mission["last_step"] = {
                "action": action,
                "actor_id": actor_id,
                "result": self._serialize(result),
            }

            return {
                "status": "ok",
                "mission_id": mission_id,
                "result": result,
            }

        except PermissionError as exc:
            self.block(
                mission_id,
                str(exc),
            )

            return {
                "status": "blocked",
                "mission_id": mission_id,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            }

        except Exception as exc:
            self.fail(
                mission_id,
                str(exc),
            )

            return {
                "status": "error",
                "mission_id": mission_id,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            }

    def dashboard(self) -> Dict[str, Any]:
        missions = list(self._missions.values())

        counts = {
            status: 0
            for status in self.VALID_STATUSES
        }

        for mission in missions:
            status = mission.get("status", "planned")

            if status not in counts:
                counts[status] = 0

            counts[status] += 1

        return {
            "total": len(missions),
            "by_status": counts,
            "active": sum(
                counts.get(status, 0)
                for status in {
                    "planned",
                    "queued",
                    "running",
                    "blocked",
                    "waiting_approval",
                }
            ),
            "completed": counts.get("completed", 0),
            "failed": counts.get("failed", 0),
            "cancelled": counts.get("cancelled", 0),
        }

    def active_missions(self) -> List[Dict[str, Any]]:
        active_statuses = {
            "planned",
            "queued",
            "running",
            "blocked",
            "waiting_approval",
        }

        return [
            dict(mission)
            for mission in self._missions.values()
            if mission.get("status") in active_statuses
        ]
