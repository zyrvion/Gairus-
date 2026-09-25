from __future__ import annotations

from typing import Any, Dict


class GairusRuntime:
    """
    Façade centrale du système.
    Toutes les capacités haut niveau passent ici avant
    de toucher les moteurs spécialisés.
    """

    def __init__(
        self,
        enterprise=None,
        controller=None,
        executor=None,
        llm=None,
        missions=None,
        autonomy=None,
    ):
        self.enterprise = enterprise
        self.controller = controller
        self.executor = executor
        self.llm = llm
        self.missions = missions
        self.autonomy = autonomy

    def status(self):
        return {
            "agent": "Gaïrus",
            "enterprise": self.enterprise is not None,
            "controller": self.controller is not None,
            "executor": self.executor is not None,
            "llm": self.llm is not None,
            "missions": self.missions is not None,
            "autonomy": self.autonomy is not None,
        }

    def think(self, prompt: str, context: Dict[str, Any] | None = None):
        context = context or {}

        if self.llm:
            generate = getattr(self.llm, "generate", None)
            if callable(generate):
                try:
                    return generate(prompt, context=context)
                except TypeError:
                    return generate(prompt)

        if self.autonomy:
            return self.autonomy.plan(prompt, context)

        return {
            "status": "no_llm",
            "prompt": prompt,
            "context": context,
        }

    def run(
        self,
        actor_id: str,
        action: str,
        handler=None,
        **kwargs,
    ):
        if not self.executor:
            raise RuntimeError("Executor unavailable")

        return self.executor.execute(
            action=action,
            handler=handler,
            actor_id=actor_id,
            **kwargs,
        )
