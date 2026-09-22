class VoiceAgent:
    name = "voice"

    def run(self, task):
        return {"agent": self.name, "task": task, "status": "completed"}
