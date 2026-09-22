class ContentAgent:
    name = "content"

    def run(self, task):
        return {
            "agent": self.name,
            "task": task,
            "status": "completed",
            "capabilities": [
                "text",
                "reports",
                "emails",
                "marketing",
                "scripts",
                "business_documents",
            ],
        }
