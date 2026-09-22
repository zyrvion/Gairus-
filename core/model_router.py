from dataclasses import dataclass
import os


@dataclass
class ModelChoice:
    provider: str
    model: str
    mode: str
    reason: str


class ModelRouter:
    def __init__(self):
        self.default_model = os.getenv(
            "GAIRUS_DEFAULT_MODEL",
            "deepseek"
        )

        self.models = {
            "general": os.getenv(
                "GAIRUS_GENERAL_MODEL",
                self.default_model
            ),
            "coding": os.getenv(
                "GAIRUS_CODING_MODEL",
                "deepseek-coder"
            ),
            "research": os.getenv(
                "GAIRUS_RESEARCH_MODEL",
                self.default_model
            ),
            "reasoning": os.getenv(
                "GAIRUS_REASONING_MODEL",
                self.default_model
            ),
            "multimodal": os.getenv(
                "GAIRUS_VISION_MODEL",
                self.default_model
            ),
            "fast": os.getenv(
                "GAIRUS_FAST_MODEL",
                self.default_model
            ),
        }

    def choose(self, task, complexity="auto"):
        text = task.lower()

        if any(x in text for x in (
            "code", "coder", "python", "javascript",
            "bug", "git", "programmer", "développe",
            "développement", "application", "script"
        )):
            return ModelChoice(
                "local",
                self.models["coding"],
                "deep",
                "Programmation"
            )

        if any(x in text for x in (
            "image", "photo", "vidéo", "video",
            "audio", "vision", "capture",
            "document visuel"
        )):
            return ModelChoice(
                "local",
                self.models["multimodal"],
                "normal",
                "Multimodal"
            )

        if any(x in text for x in (
            "cherche", "recherche", "source",
            "actualité", "internet", "web",
            "compare", "étude", "enquête"
        )):
            return ModelChoice(
                "local",
                self.models["research"],
                "deep",
                "Recherche"
            )

        if any(x in text for x in (
            "raisonne", "réfléchis", "preuve",
            "math", "scientifique", "architecture",
            "algorithme", "démontrer"
        )):
            return ModelChoice(
                "local",
                self.models["reasoning"],
                "deep",
                "Raisonnement"
            )

        if complexity == "deep":
            return ModelChoice(
                "local",
                self.models["reasoning"],
                "deep",
                "Complexité élevée"
            )

        if complexity == "fast":
            return ModelChoice(
                "local",
                self.models["fast"],
                "fast",
                "Réponse rapide"
            )

        return ModelChoice(
            "local",
            self.models["general"],
            "normal",
            "Tâche générale"
        )

    def route(self, task):
        text = task.lower()

        if any(x in text for x in (
            "code", "python", "javascript",
            "bug", "git", "programmer",
            "développe", "développement",
            "application", "script"
        )):
            return "coding"

        if any(x in text for x in (
            "cherche", "recherche", "source",
            "actualité", "internet", "web",
            "compare", "étude", "analyse"
        )):
            return "research"

        if any(x in text for x in (
            "pdf", "document", "connaissance",
            "fichier", "base de connaissances"
        )):
            return "knowledge"

        if any(x in text for x in (
            "réunion", "meeting", "transcription"
        )):
            return "meeting"

        if any(x in text for x in (
            "appel", "voix", "audio",
            "téléphone", "parle"
        )):
            return "voice"

        return "general"
