from __future__ import annotations

from typing import Any, Dict, Optional


class GairusCognitiveContext:
    """
    Couche de contexte cognitif de Gaïrus.

    Centralise :
      - identité
      - personnes
      - hiérarchie
      - mémoire
      - missions
      - cognition
      - évolution

    Cette couche ne remplace aucun moteur existant.
    Elle compose les informations déjà disponibles.
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

        self.autonomous = getattr(
            runtime,
            "autonomous_integration",
            None,
        )

        self.missions = getattr(
            runtime,
            "missions",
            None,
        )

        self.evolution = getattr(
            runtime,
            "self_evolution",
            None,
        )

    # ---------------------------------------------------------
    # IDENTITE
    # ---------------------------------------------------------

    def identity(self) -> Dict[str, Any]:
        if self.cognitive is None:
            return {}

        try:
            return self.cognitive.identity()
        except Exception:
            return {}

    # ---------------------------------------------------------
    # PERSONNES
    # ---------------------------------------------------------

    def person(
        self,
        person_id: str,
    ) -> Optional[Dict[str, Any]]:
        if self.cognitive is None:
            return None

        try:
            return self.cognitive.get_person(
                person_id
            )
        except Exception:
            return None

    def organization(self) -> Dict[str, Any]:
        if self.cognitive is None:
            return {}

        try:
            return self.cognitive.organization()
        except Exception:
            return {}

    def hierarchy(
        self,
        person_id: str,
    ):
        if self.cognitive is None:
            return []

        try:
            return self.cognitive.hierarchy_chain(
                person_id
            )
        except Exception:
            return []

    def can_act(
        self,
        actor_id: str,
        action: str,
    ) -> bool:
        if self.cognitive is None:
            return False

        try:
            return bool(
                self.cognitive.can_act(
                    actor_id,
                    action,
                )
            )
        except Exception:
            return False

    # ---------------------------------------------------------
    # MEMOIRE
    # ---------------------------------------------------------

    def remember(
        self,
        key: str,
        value: Any,
        category: str = "general",
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
    ):
        if self.autonomous is None:
            return None

        return self.autonomous.remember(
            key=key,
            value=value,
            category=category,
            actor_id=actor_id,
            mission_id=mission_id,
        )

    def recall(
        self,
        key: str,
        default: Any = None,
    ):
        if self.autonomous is None:
            return default

        return self.autonomous.recall(
            key,
            default,
        )

    def search_memory(
        self,
        query: str,
        limit: int = 20,
    ):
        if self.autonomous is None:
            return []

        try:
            return self.autonomous.search_memory(
                query,
                limit=limit,
            )
        except Exception:
            return []

    # ---------------------------------------------------------
    # CONTEXTE DE MISSION
    # ---------------------------------------------------------

    def mission_context(
        self,
        mission_id: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        context = {
            "identity": self.identity(),
            "actor": None,
            "hierarchy": [],
            "organization": self.organization(),
            "mission": None,
            "memory": [],
        }

        if actor_id:
            context["actor"] = self.person(
                actor_id
            )

            context["hierarchy"] = self.hierarchy(
                actor_id
            )

        if mission_id and self.missions is not None:
            try:
                getter = getattr(
                    self.missions,
                    "get",
                    None,
                )

                if callable(getter):
                    context["mission"] = getter(
                        mission_id
                    )
            except Exception:
                pass

        if actor_id:
            try:
                context["memory"] = (
                    self.search_memory(
                        actor_id,
                        limit=20,
                    )
                )
            except Exception:
                pass

        return context

    # ---------------------------------------------------------
    # PERCEPTION
    # ---------------------------------------------------------

    def perceive(
        self,
        event: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if self.cognitive is None:
            return {
                "ok": False,
                "error": "cognitive_unavailable",
            }

        context = context or {}

        try:
            result = self.cognitive.perceive(
                event,
                context,
            )

            return {
                "ok": True,
                "event": event,
                "context": context,
                "result": result,
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
            }

    # ---------------------------------------------------------
    # RAISONNEMENT
    # ---------------------------------------------------------

    def reason(
        self,
        observation: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if self.cognitive is None:
            return {
                "ok": False,
                "error": "cognitive_unavailable",
            }

        context = context or {}

        try:
            result = self.cognitive.reason(
                observation,
                context,
            )

            return {
                "ok": True,
                "observation": observation,
                "context": context,
                "result": result,
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
            }

    # ---------------------------------------------------------
    # EVOLUTION
    # ---------------------------------------------------------

    def evolution_status(self):
        if self.evolution is None:
            return {
                "status": "unavailable"
            }

        try:
            return self.evolution.status()
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
            }

    # ---------------------------------------------------------
    # CONTEXTE COMPLET
    # ---------------------------------------------------------

    def build(
        self,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        event: Optional[str] = None,
    ) -> Dict[str, Any]:

        context = self.mission_context(
            mission_id=mission_id,
            actor_id=actor_id,
        )

        context["evolution"] = (
            self.evolution_status()
        )

        if event:
            context["perception"] = self.perceive(
                event,
                context,
            )

        return context

    # ---------------------------------------------------------
    # STATUT
    # ---------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "type": "gairus_cognitive_context",
            "identity": bool(
                self.cognitive
            ),
            "memory": bool(
                self.autonomous
            ),
            "missions": bool(
                self.missions
            ),
            "evolution": bool(
                self.evolution
            ),
            "organization": (
                bool(
                    self.organization()
                )
                if self.cognitive
                else False
            ),
        }


_instance = None


def integrate_cognitive_context(
    runtime: Any,
):
    global _instance

    _instance = GairusCognitiveContext(
        runtime
    )

    runtime.cognitive_context = _instance

    return _instance


def get_cognitive_context():
    return _instance
