from dataclasses import dataclass


@dataclass
class ModelChoice:
    model: str
    mode: str
    reason: str


class ModelRouter:
    def choose(self, task: str, complexity: str = "auto") -> ModelChoice:
        text = task.lower()

        if any(x in text for x in (
            "coder", "code", "python", "javascript", "bug",
            "git", "programmer", "développe", "développement"
        )):
            return ModelChoice(
                "coding",
                "deep",
                "Tâche de programmation"
            )

        if any(x in text for x in (
            "image", "photo", "vidéo", "video", "audio",
            "vision", "capture", "document visuel"
        )):
            return ModelChoice(
                "multimodal",
                "normal",
                "Tâche multimodale"
            )

        if any(x in text for x in (
            "cherche", "recherche", "source", "actualité",
            "internet", "web", "compare", "étude", "analyse"
        )):
            return ModelChoice(
                "research",
                "deep",
                "Tâche de recherche"
            )

        if any(x in text for x in (
            "réfléchis", "raisonne", "preuve", "math",
            "scientifique", "architecture", "algorithme"
        )):
            return ModelChoice(
                "reasoning",
                "deep",
                "Tâche nécessitant un raisonnement approfondi"
            )

        if complexity == "deep":
            return ModelChoice(
                "reasoning",
                "deep",
                "Complexité élevée"
            )

        if complexity == "fast":
            return ModelChoice(
                "fast",
                "fast",
                "Réponse rapide"
            )

        return ModelChoice(
            "general",
            "normal",
            "Tâche générale"
        )
