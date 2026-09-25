from __future__ import annotations

from typing import Any, Dict, Optional

from config.gairus import GairusConfig
from core.bootstrap import bootstrap_runtime
from core.health import HealthMonitor
from memory.runtime_memory import RuntimeMemory


class GairusSystem:
    """
    Système central de Gaïrus.

    Cette classe compose les différents moteurs :
        Enterprise
        Hierarchy
        Controller
        ActionGateway
        Executor
        Missions
        Autonomy
        Runtime
        Memory
        Health

    Elle constitue une façade stable pour les interfaces
    Flask, Slack, CLI, workers et autres intégrations.
    """

    def __init__(
        self,
        config: Optional[GairusConfig] = None,
        llm=None,
    ):
        self.config = config or GairusConfig.from_env()

        self.memory = RuntimeMemory()

        self.runtime = bootstrap_runtime(
            llm=llm,
            enabled_autonomy=self.config.autonomy_enabled,
        )

        self.health = HealthMonitor(
            runtime=self.runtime,
            enterprise=getattr(
                self.runtime,
                "enterprise",
                None,
            ),
            executor=getattr(
                self.runtime,
                "executor",
                None,
            ),
            controller=getattr(
                self.runtime,
                "controller",
                None,
            ),
            gateway=getattr(
                self.runtime,
                "gateway",
                None,
            ),
            hierarchy=getattr(
                self.runtime,
                "hierarchy",
                None,
            ),
            missions=getattr(
                self.runtime,
                "missions",
                None,
            ),
            autonomy=getattr(
                self.runtime,
                "autonomy",
                None,
            ),
            llm=llm,
            memory=self.memory,
        )

    @property
    def enterprise(self):
        return self.runtime.enterprise

    @property
    def controller(self):
        return self.runtime.controller

    @property
    def gateway(self):
        return getattr(
            self.runtime,
            "gateway",
            None,
        )

    @property
    def executor(self):
        return self.runtime.executor

    @property
    def hierarchy(self):
        return getattr(
            self.runtime,
            "hierarchy",
            None,
        )

    @property
    def missions(self):
        return self.runtime.missions

    @property
    def autonomy(self):
        return self.runtime.autonomy

    @property
    def llm(self):
        return self.runtime.llm

    def status(self) -> Dict[str, Any]:
        return {
            "agent": self.config.agent_name,
            "environment": self.config.environment,
            "runtime": self.runtime.status(),
            "health": self.health.summary(),
            "memory": self.memory.status(),
        }

    def health_status(self) -> Dict[str, Any]:
        return self.health.check()

    def readiness(self) -> Dict[str, Any]:
        return self.health.readiness()

    def liveness(self) -> Dict[str, Any]:
        return self.health.liveness()

    def think(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        context = context or {}

        memory_context = self.memory.context()

        merged_context = {
            **memory_context,
            **context,
        }

        self.memory.add_message(
            role="user",
            content=prompt,
        )

        result = self.runtime.think(
            prompt=prompt,
            context=merged_context,
        )

        self.memory.add_result(
            result=result,
        )

        return result

    def run(
        self,
        actor_id: str,
        action: str,
        handler=None,
        **kwargs,
    ) -> Dict[str, Any]:
        self.memory.add_task(
            {
                "actor_id": actor_id,
                "action": action,
                "parameters": kwargs,
            },
            actor_id=actor_id,
        )

        result = self.runtime.run(
            actor_id=actor_id,
            action=action,
            handler=handler,
            **kwargs,
        )

        self.memory.add_result(
            result=result,
            actor_id=actor_id,
        )

        return result

    def create_mission(
        self,
        actor_id: str,
        title: str,
        objective: Optional[str] = None,
        department_id: Optional[str] = None,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = self.runtime.create_mission(
            actor_id=actor_id,
            title=title,
            objective=objective,
            department_id=department_id,
            priority=priority,
            metadata=metadata,
        )

        self.memory.add_task(
            {
                "type": "mission_created",
                "mission": result,
            },
            actor_id=actor_id,
        )

        return result

    def delegate(
        self,
        mission_id: str,
        employee_id: str,
        delegator_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = self.runtime.delegate(
            mission_id=mission_id,
            employee_id=employee_id,
            delegator_id=delegator_id,
        )

        self.memory.add_result(
            {
                "type": "delegation",
                "mission_id": mission_id,
                "employee_id": employee_id,
                "result": result,
            },
            actor_id=delegator_id,
        )

        return result

    def escalate(
        self,
        actor_id: str,
        reason: str,
        action: Optional[str] = None,
        mission_id: Optional[str] = None,
        target_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = self.runtime.escalate(
            actor_id=actor_id,
            reason=reason,
            action=action,
            mission_id=mission_id,
            target_level=target_level,
        )

        self.memory.add_result(
            {
                "type": "escalation",
                "result": result,
            },
            actor_id=actor_id,
        )

        return result

    def dashboard(self) -> Dict[str, Any]:
        result = {
            "agent": self.config.agent_name,
            "environment": self.config.environment,
            "health": self.health.summary(),
        }

        if self.enterprise is not None:
            try:
                result["enterprise"] = (
                    self.enterprise.dashboard()
                )
            except Exception as exc:
                result["enterprise_error"] = str(exc)

        if self.hierarchy is not None:
            try:
                result["hierarchy"] = (
                    self.hierarchy.summary()
                )
            except Exception as exc:
                result["hierarchy_error"] = str(exc)

        if self.missions is not None:
            try:
                result["missions"] = (
                    self.missions.dashboard()
                )
            except Exception as exc:
                result["missions_error"] = str(exc)

        if self.autonomy is not None:
            try:
                result["autonomy"] = (
                    self.autonomy.status()
                )
            except Exception as exc:
                result["autonomy_error"] = str(exc)

        result["memory"] = self.memory.status()

        return result


_SYSTEM: Optional[GairusSystem] = None


def get_system(
    config: Optional[GairusConfig] = None,
    llm=None,
    reset: bool = False,
) -> GairusSystem:
    global _SYSTEM

    if reset or _SYSTEM is None:
        _SYSTEM = GairusSystem(
            config=config,
            llm=llm,
        )

    return _SYSTEM


def build_system(
    config: Optional[GairusConfig] = None,
    llm=None,
) -> GairusSystem:
    return GairusSystem(
        config=config,
        llm=llm,
    )


def reset_system():
    global _SYSTEM
    _SYSTEM = None
