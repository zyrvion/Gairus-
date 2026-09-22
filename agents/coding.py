class CodingAgent:
    name = "coding"

    def run(self, task):
        return {"agent": self.name, "task": task, "status": "completed"}
