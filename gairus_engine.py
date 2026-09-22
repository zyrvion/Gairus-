from core.orchestrator import GairusOrchestrator
from core.model_router import ModelRouter
from core.llm_client import LLMClient
from agents.registry import AgentRegistry


class GairusEngine:
    def __init__(self):
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

        agent_result = self.registry.run(
            agent_name,
            request,
            context
        )

        mission["model"] = {
            "provider": choice.provider,
            "name": choice.model,
            "mode": choice.mode,
            "reason": choice.reason,
        }

        mission["agent_result"] = agent_result

        return mission

    def status(self):
        return {
            "llm_url": self.llm.base_url,
            "llm_available": self.llm.available(),
            "models": self.llm.models(),
            "agents": self.registry.names(),
        }
