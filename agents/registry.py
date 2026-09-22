from .general import GeneralAgent
from .research import ResearchAgent
from .coding import CodingAgent
from .knowledge import KnowledgeAgent
from .meeting import MeetingAgent
from .voice import VoiceAgent


class AgentRegistry:
    def __init__(self):
        self.agents = {
            "general": GeneralAgent(),
            "research": ResearchAgent(),
            "coding": CodingAgent(),
            "knowledge": KnowledgeAgent(),
            "meeting": MeetingAgent(),
            "voice": VoiceAgent(),
        }

    def get(self, name):
        return self.agents.get(name)

    def names(self):
        return list(self.agents.keys())

    def run(self, name, task, context=None):
        agent = self.get(name)

        if agent is None:
            raise ValueError(
                f"Agent inconnu: {name}"
            )

        return agent.run(task, context)
