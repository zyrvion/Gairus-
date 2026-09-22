class ResearchAgent:
    name = "research"

    def run(self, task):
        return {"agent": self.name, "task": task, "status": "completed"}
