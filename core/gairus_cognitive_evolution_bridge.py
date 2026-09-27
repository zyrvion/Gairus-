from __future__ import annotations

from typing import Any, Dict


class CognitiveEvolutionBridge:
    """
    Relie la cognition de Gaïrus à son moteur d'auto-évolution.

    Flux :
        perception
        -> raisonnement
        -> proposition
        -> évolution contrôlée
        -> tests
        -> validation
    """

    def __init__(self, runtime: Any):
        if runtime is None:
            raise ValueError("runtime is required")

        self.runtime = runtime
        self.cognitive = getattr(
            runtime,
            "cognitive",
            None,
        )
        self.evolution = getattr(
            runtime,
            "self_evolution",
            None,
        )

        if self.cognitive is None:
            raise RuntimeError(
                "cognitive runtime unavailable"
            )

        if self.evolution is None:
            raise RuntimeError(
                "self evolution runtime unavailable"
            )

    def perceive(
        self,
        event: str,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        context = context or {}

        result = self.cognitive.perceive(
            event,
            context,
        )

        return {
            "ok": True,
            "stage": "perception",
            "result": result,
        }

    def reason(
        self,
        observation: str,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        context = context or {}

        result = self.cognitive.reason(
            observation,
            context,
        )

        return {
            "ok": True,
            "stage": "reasoning",
            "result": result,
        }

    def propose(
        self,
        title: str,
        reason: str,
        files: list[str] | None = None,
    ) -> Dict[str, Any]:
        return self.evolution.propose(
            title=title,
            reason=reason,
            files=files or [],
        )

    def inspect(
        self,
        relative_path: str | None = None,
    ) -> Dict[str, Any]:
        if relative_path:
            return self.evolution.inspect_file(
                relative_path
            )

        return self.evolution.inspect()

    def validate(self) -> Dict[str, Any]:
        return self.evolution.validate()

    def evolve(
        self,
        title: str,
        reason: str,
        relative_path: str,
        content: str,
        branch: str | None = None,
        commit_message: str | None = None,
    ) -> Dict[str, Any]:
        """
        Lance une évolution contrôlée.

        Aucune évolution n'est considérée réussie
        tant que les tests ne sont pas passés.
        """

        return self.evolution.evolve(
            title=title,
            reason=reason,
            relative_path=relative_path,
            content=content,
            branch=branch,
            commit_message=commit_message,
        )

    def rollback(self) -> Dict[str, Any]:
        return self.evolution.rollback()

    def status(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "type": "cognitive_evolution_bridge",
            "cognitive": (
                self.cognitive.status()
                if self.cognitive
                else None
            ),
            "evolution": (
                self.evolution.status()
                if self.evolution
                else None
            ),
        }


_instance = None


def integrate_cognitive_evolution(
    runtime: Any,
):
    global _instance

    _instance = CognitiveEvolutionBridge(
        runtime
    )

    runtime.cognitive_evolution = _instance

    return _instance


def get_cognitive_evolution_bridge():
    return _instance
