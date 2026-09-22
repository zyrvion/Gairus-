from core.company_controller import CompanyController
from agents.company import CompanyAgent
from agents.content import ContentAgent
from core.orchestrator import GairusOrchestrator
from core.model_router import ModelRouter
from core.llm_client import LLMClient
from agents.registry import AgentRegistry


class GairusEngine:
    # Enterprise control plane

    def __init__(self):
        self.company_controller = CompanyController()
        self.orchestrator = GairusOrchestrator()
        self.registry = AgentRegistry()
        self.model_router = ModelRouter()
        self.llm = LLMClient()

    def ask(self, request, complexity="auto", context=None):
        mission = self.orchestrator.run(
            request,
            complexity
        )

        agent_name = mission["route"]

        choice = self.model_router.choose(
            request,
            complexity
        )

        selected_model = choice.model

        installed_models = self.llm.models()

        if installed_models:
            if selected_model not in installed_models:
                selected_model = (
                    self.llm.model
                    if self.llm.model in installed_models
                    else installed_models[0]
                )

        agent_result = self.registry.run(
            agent_name,
            request,
            context,
            selected_model
        )

        mission["model"] = {
            "provider": choice.provider,
            "requested": choice.model,
            "selected": selected_model,
            "mode": choice.mode,
            "reason": choice.reason,
        }

        mission["agent_result"] = agent_result

        return mission

    def status(self):
        installed_models = self.llm.models()

        return {
            "llm_url": self.llm.base_url,
            "llm_available": bool(installed_models),
            "models": installed_models,
            "agents": self.registry.names(),
        }
