class Planner:
    def create_plan(self, objective):
        return {
            "objective": objective,
            "steps": [
                {"id": 1, "action": "analyze", "status": "pending"},
                {"id": 2, "action": "execute", "status": "pending"},
                {"id": 3, "action": "verify", "status": "pending"},
                {"id": 4, "action": "remember", "status": "pending"},
            ],
        }
