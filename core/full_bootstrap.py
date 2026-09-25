from __future__ import annotations

from typing import Any, Optional

from config.gairus import CONFIG, GairusConfig

from core.enterprise import EnterpriseEngine
from core.company_controller import CompanyController
from core.action_gateway import ActionGateway
from core.executor import Executor

from core.hierarchy import HierarchyEngine
from core.mission_orchestrator import MissionOrchestrator
from core.autonomy import AutonomyEngine

from core.tool_bootstrap import bootstrap_tools
from core.llm_bootstrap import bootstrap_llm

from core.slack_gateway import SlackGateway
from core.slack_hierarchy import SlackHierarchyRouter
from core.slack_integration import SlackIntegration

from memory.runtime_memory import RuntimeMemory
from core.health import HealthMonitor

from core.command_center import GairusCommandCenter


class FullGairusRuntime:
    """
    Runtime complet de Gaïrus.

    Cette classe assemble les composants existants.
    Aucun composant existant n'est remplacé.
    """

    def __init__(
        self,
        config: Optional[GairusConfig] = None,
        llm_client: Any = None,
        slack_token: Optional[str] = None,
    ):
        self.config = config or CONFIG

        self.enterprise = EnterpriseEngine()

        self.controller = CompanyController(
            enterprise=self.enterprise,
        )

        self.gateway = ActionGateway(
            enterprise=self.enterprise,
            controller=self.controller,
        )

        self.executor = Executor(
            enterprise=self.enterprise,
            controller=self.controller,
        )

        self.hierarchy = HierarchyEngine(
            enterprise=self.enterprise,
        )

        self.slack_gateway = SlackGateway(
            token=slack_token,
        )

        try:
            self.slack_router = SlackHierarchyRouter(
                hierarchy=self.hierarchy,
                slack_gateway=self.slack_gateway,
            )
        except TypeError:
            try:
                self.slack_router = SlackHierarchyRouter(
                    self.hierarchy,
                    self.slack_gateway,
                )
            except TypeError:
                self.slack_router = SlackHierarchyRouter()

        self.slack = SlackIntegration(
            gateway=self.slack_gateway,
            router=self.slack_router,
        )

        try:
            self.missions = MissionOrchestrator(
                enterprise=self.enterprise,
                executor=self.executor,
                controller=self.controller,
                hierarchy=self.hierarchy,
            )
        except TypeError:
            try:
                self.missions = MissionOrchestrator(
                    self.enterprise,
                    self.executor,
                    self.controller,
                )
            except TypeError:
                self.missions = MissionOrchestrator(
                    self.enterprise,
                    self.executor,
                )

        try:
            self.autonomy = AutonomyEngine(
                enterprise=self.enterprise,
                executor=self.executor,
                missions=self.missions,
                llm=None,
            )
        except TypeError:
            self.autonomy = AutonomyEngine(
                self.enterprise,
                self.executor,
                self.missions,
            )

        self.llm = bootstrap_llm(
            config=self.config,
            client=llm_client,
        )

        self.tools = bootstrap_tools(
            router=self.slack_router,
        )

        self.memory = RuntimeMemory()

        self.health = HealthMonitor()

        self.command = GairusCommandCenter(
            system=None,
            enterprise=self.enterprise,
            controller=self.controller,
            executor=self.executor,
            hierarchy=self.hierarchy,
            missions=self.missions,
            autonomy=self.autonomy,
            tools=self.tools,
            llm=self.llm,
            slack=self.slack,
            memory=self.memory,
            health=self.health,
        )

    def think(self, prompt: str, context=None):
        return self.command.think(
            prompt,
            context=context or {},
        )

    def run(self, actor_id: str, action: str, **kwargs):
        return self.command.run(
            actor_id=actor_id,
            action=action,
            **kwargs,
        )

    def create_mission(
        self,
        actor_id: str,
        title: str,
        objective: str,
        **kwargs,
    ):
        return self.command.create_mission(
            actor_id=actor_id,
            title=title,
            objective=objective,
            **kwargs,
        )

    def delegate(
        self,
        mission_id: str,
        employee_id: str,
        delegator_id=None,
    ):
        return self.command.delegate(
            mission_id=mission_id,
            employee_id=employee_id,
            delegator_id=delegator_id,
        )

    def escalate(
        self,
        actor_id: str,
        reason: str,
        action=None,
        mission_id=None,
        target_level=None,
    ):
        return self.command.escalate(
            actor_id=actor_id,
            reason=reason,
            action=action,
            mission_id=mission_id,
            target_level=target_level,
        )

    def send_slack(self, channel: str, text: str, **kwargs):
        return self.command.send_slack(
            channel=channel,
            text=text,
            **kwargs,
        )

    def dashboard(self):
        return self.command.dashboard()

    def status(self):
        return self.command.status()


_runtime = None


def get_full_runtime(
    config: Optional[GairusConfig] = None,
    llm_client: Any = None,
    slack_token: Optional[str] = None,
) -> FullGairusRuntime:
    global _runtime

    if _runtime is None:
        _runtime = FullGairusRuntime(
            config=config,
            llm_client=llm_client,
            slack_token=slack_token,
        )

    return _runtime


def reset_full_runtime():
    global _runtime
    _runtime = None


def build_full_runtime(
    config: Optional[GairusConfig] = None,
    llm_client: Any = None,
    slack_token: Optional[str] = None,
) -> FullGairusRuntime:
    return FullGairusRuntime(
        config=config,
        llm_client=llm_client,
        slack_token=slack_token,
    )
