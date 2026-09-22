from core.llm_client import LLMClient


class CodingAgent:
    name = "coding"

    def __init__(self):
        self.llm = LLMClient()

    def run(self, task, context=None):
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu es l'agent de programmation de Gaïrus. "
                    "Analyse le problème, propose une solution "
                    "robuste et retourne du code exploitable."
                ),
            }
        ]

        if context:
            messages.append({
                "role": "system",
                "content": f"Contexte du projet:\n{context}"
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
