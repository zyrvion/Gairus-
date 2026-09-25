from __future__ import annotations

from typing import Any, Dict, Optional


class GairusCommandCenter:
    """
    Centre de commande unifié de Gaïrus.

    Il orchestre les composants existants sans remplacer
    les implémentations déjà présentes dans le projet.
    """

    def __init__(
        self,
        system: Any = None,
        enterprise: Any = None,
        controller: Any = None,
        executor: Any = None,
        hierarchy: Any = None,
        missions: Any = None,
        autonomy: Any = None,
        tools: Any = None,
        llm: Any = None,
        slack: Any = None,
        memory: Any = None,
        health: Any = None,
    ):
        self.system = system
        self.enterprise = enterprise
        self.controller = controller
        self.executor = executor
        self.hierarchy = hierarchy
        self.missions = missions
        self.autonomy = autonomy
        self.tools = tools
        self.llm = llm
        self.slack = slack
        self.memory = memory
        self.health = health

    def think(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if self.llm is not None:
            if hasattr(self.llm, "think"):
                return self.llm.think(
                    prompt,
                    context=context or {},
                )

            if hasattr(self.llm, "generate"):
                return self.llm.generate(
                    prompt,
                    context=context or {},
                )

        if self.system is not None and hasattr(self.system, "think"):
            return self.system.think(
                prompt,
                context=context or {},
            )

        return {
            "status": "unconfigured",
            "prompt": prompt,
            "context": context or {},
        }

    def run(
        self,
        actor_id: str,
        action: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if self.executor is not None:
            return self.executor.execute(
                action,
                actor_id=actor_id,
                **kwargs,
            )

        if self.system is not None and hasattr(self.system, "run"):
            return self.system.run(
                actor_id=actor_id,
                action=action,
                **kwargs,
            )

        return {
            "status": "error",
            "error": "Executor Gaïrus indisponible",
        }

    def create_mission(
        self,
        actor_id: str,
        title: str,
        objective: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if self.missions is None:
            raise RuntimeError("MissionOrchestrator indisponible")

        return self.missions.create(
            title=title,
            objective=objective,
            actor_id=actor_id,
            **kwargs,
        )

    def delegate(
        self,
        mission_id: str,
        employee_id: str,
        delegator_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.missions is not None and hasattr(
            self.missions,
            "delegate",
        ):
            return self.missions.delegate(
                mission_id=mission_id,
                employee_id=employee_id,
                delegator_id=delegator_id,
            )

        if self.enterprise is not None:
            return self.enterprise.delegate(
                mission_id=mission_id,
                employee_id=employee_id,
                delegator_id=delegator_id,
            )

        raise RuntimeError("Gestionnaire de missions indisponible")

    def escalate(
        self,
        actor_id: str,
        reason: str,
        action: Optional[str] = None,
        mission_id: Optional[str] = None,
        target_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = None

        if self.enterprise is not None:
            result = self.enterprise.escalate(
                actor_id=actor_id,
                reason=reason,
                action=action,
                mission_id=mission_id,
                target_level=target_level,
            )

        if self.slack is not None:
            try:
                slack_result = self.slack.send_escalation(
                    actor_id=actor_id,
                    reason=reason,
                    mission_id=mission_id,
                    action=action,
                )
            except Exception as exc:
                slack_result = {
                    "status": "error",
                    "error": str(exc),
                }
        else:
            slack_result = {
                "status": "not_configured",
            }

        return {
            "status": "ok",
            "escalation": result,
            "slack": slack_result,
        }

    def send_slack(
        self,
        channel: str,
        text: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if self.slack is None:
            raise RuntimeError("SlackIntegration indisponible")

        return self.slack.send(
            channel=channel,
            text=text,
            **kwargs,
        )

    def remember(
        self,
        key: str,
        value: Any,
    ) -> Dict[str, Any]:
        if self.memory is None:
            return {
                "status": "unavailable",
                "key": key,
            }

        if hasattr(self.memory, "remember"):
            self.memory.remember(key, value)

        return {
            "status": "ok",
            "key": key,
            "value": value,
        }

    def dashboard(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "agent": "Gaïrus",
        }

        components = {
            "enterprise": self.enterprise,
            "controller": self.controller,
            "executor": self.executor,
            "hierarchy": self.hierarchy,
            "missions": self.missions,
            "autonomy": self.autonomy,
            "tools": self.tools,
            "llm": self.llm,
            "slack": self.slack,
            "memory": self.memory,
            "health": self.health,
        }

        for name, component in components.items():
            if component is None:
                result[name] = {
                    "status": "not_configured",
                }
                continue

            try:
                if hasattr(component, "status"):
                    result[name] = component.status()
                elif hasattr(component, "dashboard"):
                    result[name] = component.dashboard()
                else:
                    result[name] = {
                        "status": "available",
                        "class": component.__class__.__name__,
                    }
            except Exception as exc:
                result[name] = {
                    "status": "error",
                    "error": str(exc),
                }

        return result

    def status(self) -> Dict[str, Any]:
        return {
            "agent": "Gaïrus",
            "components": {
                "enterprise": self.enterprise is not None,
                "controller": self.controller is not None,
                "executor": self.executor is not None,
                "hierarchy": self.hierarchy is not None,
                "missions": self.missions is not None,
                "autonomy": self.autonomy is not None,
                "tools": self.tools is not None,
                "llm": self.llm is not None,
                "slack": self.slack is not None,
                "memory": self.memory is not None,
                "health": self.health is not None,
            },
        }
