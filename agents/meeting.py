class MeetingAgent:
    name = "meeting"

    def run(self, task):
        return {"agent": self.name, "task": task, "status": "completed"}
