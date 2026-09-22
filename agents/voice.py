from core.llm_client import LLMClient


class VoiceAgent:
    name = "voice"

    def __init__(self):
        self.llm = LLMClient()

    def run(self, task, context=None, model=None):
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu es l'agent vocal de Gaïrus. "
                    "Prépare des réponses naturelles, courtes "
                    "et adaptées à une conversation orale."
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
            "answer": self.llm.chat(
                messages,
                model=model
            )
        }
