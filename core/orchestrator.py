from .permissions import PermissionManager
from .planner import Planner
from .router import ModelRouter
from .executor import Executor
from .verifier import Verifier
from .mission_engine import MissionEngine
from .task_graph import TaskGraph
from security.audit import AuditLog


class GairusOrchestrator:
    def __init__(self):
        self.permissions = PermissionManager()
        self.planner = Planner()
        self.router = ModelRouter()
        self.executor = Executor(self.permissions)
        self.verifier = Verifier()
        self.missions = MissionEngine()
        self.audit = AuditLog()

    def run(self, objective, complexity="auto"):
        mission = self.missions.create(
            objective,
            complexity
        )

        self.audit.record(
            "mission_created",
            mission
        )

        graph = TaskGraph()

        graph.add(
            "analysis",
            "analyze objective"
        )

        graph.add(
            "routing",
            "select agent and model",
            ["analysis"]
        )

        graph.add(
            "execution",
            "execute mission",
            ["routing"]
        )

        graph.add(
            "verification",
            "verify result",
            ["execution"]
        )

        route = self.router.route(objective)

        result = self.executor.execute(
            action=f"delegate:{route}",
            risk="low",
        )

        verification = self.verifier.verify(result)

        if verification.get("verified"):
            mission["status"] = "completed"
        else:
            mission["status"] = "verification_failed"

        mission["execution"] = result
        mission["verification"] = verification
        mission["task_graph"] = graph.nodes

        self.audit.record(
            "mission_finished",
            {
                "mission_id": mission["id"],
                "status": mission["status"],
            }
        )

        return mission
