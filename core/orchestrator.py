from .permissions import PermissionManager
from .planner import Planner
from .router import ModelRouter
from .executor import Executor
from .verifier import Verifier


class GairusOrchestrator:
    def __init__(self):
        self.permissions = PermissionManager()
        self.planner = Planner()
        self.router = ModelRouter()
        self.executor = Executor(self.permissions)
        self.verifier = Verifier()

    def run(self, objective):
        plan = self.planner.create_plan(objective)
        agent = self.router.route(objective)

        result = self.executor.execute(
            action=f"delegate:{agent}",
            risk="low",
        )

        verification = self.verifier.verify(result)

        return {
            "agent": "Gaïrus",
            "objective": objective,
            "route": agent,
            "plan": plan,
            "execution": result,
            "verification": verification,
        }
