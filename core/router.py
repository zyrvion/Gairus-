class ModelRouter:
    def route(self, task):
        task = task.lower()

        if any(x in task for x in ("coder", "code", "python", "git", "bug")):
            return "coding"
        if any(x in task for x in ("cherche", "recherche", "web", "source")):
            return "research"
        if any(x in task for x in ("pdf", "document", "connaissance", "fichier")):
            return "knowledge"
        if any(x in task for x in ("réunion", "meeting", "transcription")):
            return "meeting"
        if any(x in task for x in ("appel", "voix", "audio", "téléphone")):
            return "voice"

        return "general"
