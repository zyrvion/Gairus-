from core.llm_client import LLMClient


class ResearchAgent:
    name = "research"

    def __init__(self):
        self.llm = LLMClient()

    def run(self, task, context=None):
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu es l'agent de recherche de Gaïrus. "
                    "Structure les hypothèses, les faits, "
                    "les sources nécessaires et les incertitudes. "
                    "Ne présente jamais une information non vérifiée "
                    "comme un fait."
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
