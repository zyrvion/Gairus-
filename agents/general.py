from core.llm_client import LLMClient


class GeneralAgent:
    name = "general"

    def __init__(self):
        self.llm = LLMClient()

    def run(self, task, context=None):
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu es Gaïrus, un agent IA généraliste. "
                    "Réponds avec précision et indique "
                    "clairement les incertitudes."
                ),
            }
        ]

        if context:
            messages.append({
                "role": "system",
                "content": f"Contexte:\n{context}"
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
