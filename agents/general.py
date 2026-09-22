class GeneralAgent:
    name = "general"

    def run(self, task):
        return {"agent": self.name, "task": task, "status": "completed"}
