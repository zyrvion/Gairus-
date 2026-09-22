from core.orchestrator import GairusOrchestrator
from agents.registry import AgentRegistry


class GairusEngine:
    def __init__(self):
        self.orchestrator = GairusOrchestrator()
        self.registry = AgentRegistry()

    def ask(self, request, complexity="auto"):
        result = self.orchestrator.run(
            request,
            complexity
        )

        agent_name = result["route"]
        agent_result = self.registry.run(
            agent_name,
            request
        )

        result["agent_result"] = agent_result

        return result
