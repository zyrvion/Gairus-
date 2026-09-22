from core.llm_client import LLMClient


class KnowledgeAgent:
    name = "knowledge"

    def __init__(self):
        self.llm = LLMClient()

    def run(self, task, context=None):
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu es l'agent de connaissance de Gaïrus. "
                    "Réponds uniquement à partir du contexte fourni "
                    "lorsqu'il est disponible."
                ),
            }
        ]

        if context:
            messages.append({
                "role": "system",
                "content": f"Sources:\n{context}"
            })

        messages.append({
            "role": "user",
            "content": task
        })

        if not self.llm.available():
            return {
                "agent": self.name,
                "task": task,
                "status": "llm_unavailable",
                "answer": None
            }

        return {
            "agent": self.name,
            "task": task,
            "status": "completed",
            "answer": self.llm.chat(messages)
        }
