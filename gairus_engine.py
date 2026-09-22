from core.orchestrator import GairusOrchestrator


class GairusEngine:
    def __init__(self):
        self.orchestrator = GairusOrchestrator()

    def ask(self, request):
        return self.orchestrator.run(request)
