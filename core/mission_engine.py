from datetime import datetime, timezone
from .planner import Planner
from .router import ModelRouter


class MissionEngine:
    def __init__(self):
        self.planner = Planner()
        self.router = ModelRouter()
        self.missions = {}

    def create(self, objective, complexity="auto"):
        mission_id = (
            datetime.now(timezone.utc)
            .strftime("%Y%m%d%H%M%S%f")
        )

        plan = self.planner.create_plan(objective)
        route = self.router.route(objective)

        mission = {
            "id": mission_id,
            "objective": objective,
            "route": route,
            "complexity": complexity,
            "status": "planned",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "plan": plan,
        }

        self.missions[mission_id] = mission
        return mission

    def get(self, mission_id):
        return self.missions.get(mission_id)

    def all(self):
        return list(self.missions.values())
