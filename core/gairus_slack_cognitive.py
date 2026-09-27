from __future__ import annotations

from typing import Any, Dict, Optional


class GairusSlackCognitive:
    """
    Pont entre Slack et le contexte cognitif de Gaïrus.

    Il transforme un événement Slack en contexte exploitable :
        utilisateur
        -> identité
        -> organisation
        -> mémoire
        -> perception
        -> mission
    """

    def __init__(self, runtime: Any):
        if runtime is None:
            raise ValueError("runtime is required")

        self.runtime = runtime

        self.context = getattr(
            runtime,
            "cognitive_context",
            None,
        )

        self.cognitive = getattr(
            runtime,
            "cognitive",
            None,
        )

    # ---------------------------------------------------------
    # UTILISATEUR SLACK
    # ---------------------------------------------------------

    def identify(
        self,
        slack_user_id: str,
        slack_user_name: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:

        if not slack_user_id:
            return {
                "ok": False,
                "error": "slack_user_id_required",
            }

        person = None

        if self.cognitive is not None:
            try:
                person = self.cognitive.get_person(
                    slack_user_id
                )
            except Exception:
                person = None

        if person:
            return {
                "ok": True,
                "known": True,
                "person": person,
            }

        return {
            "ok": True,
            "known": False,
            "person": {
                "person_id": slack_user_id,
                "name": (
                    display_name
                    or slack_user_name
                    or slack_user_id
                ),
                "slack_user_id": slack_user_id,
                "role": None,
                "manager_id": None,
                "permissions": [],
            },
        }

    # ---------------------------------------------------------
    # ENREGISTREMENT
    # ---------------------------------------------------------

    def register_person(
        self,
        slack_user_id: str,
        name: str,
        role: Optional[str] = None,
        manager_id: Optional[str] = None,
        permissions: Optional[list[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if self.cognitive is None:
            return {
                "ok": False,
                "error": "cognitive_unavailable",
            }

        try:
            person = self.cognitive.register_person(
                person_id=slack_user_id,
                name=name,
                role=role,
                manager_id=manager_id,
                permissions=permissions or [],
                metadata=metadata or {},
            )

            return {
                "ok": True,
                "person": person,
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
            }

    # ---------------------------------------------------------
    # CONTEXTE SLACK
    # ---------------------------------------------------------

    def build_context(
        self,
        slack_user_id: str,
        text: str,
        channel_id: Optional[str] = None,
        thread_ts: Optional[str] = None,
        message_ts: Optional[str] = None,
        user_name: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:

        identity = self.identify(
            slack_user_id=slack_user_id,
            slack_user_name=user_name,
            display_name=display_name,
        )

        context = {
            "source": "slack",
            "slack": {
                "user_id": slack_user_id,
                "channel_id": channel_id,
                "thread_ts": thread_ts,
                "message_ts": message_ts,
                "text": text,
            },
            "identity": (
                self.context.identity()
                if self.context
                else {}
            ),
            "actor": identity.get("person"),
            "known_actor": identity.get(
                "known",
                False,
            ),
        }

        if self.context is not None:
            try:
                actor_context = (
                    self.context.mission_context(
                        actor_id=slack_user_id,
                    )
                )

                context.update(
                    {
                        "organization":
                            actor_context.get(
                                "organization",
                                {},
                            ),
                        "hierarchy":
                            actor_context.get(
                                "hierarchy",
                                [],
                            ),
                        "memory":
                            actor_context.get(
                                "memory",
                                [],
                            ),
                    }
                )

            except Exception:
                pass

        if self.cognitive is not None:
            try:
                perception = self.cognitive.perceive(
                    text,
                    context,
                )

                context["perception"] = perception

            except Exception:
                pass

        return context

    # ---------------------------------------------------------
    # MEMOIRE
    # ---------------------------------------------------------

    def remember_interaction(
        self,
        slack_user_id: str,
        text: str,
        channel_id: Optional[str] = None,
        message_ts: Optional[str] = None,
    ):
        if self.context is None:
            return None

        key = (
            f"slack:"
            f"{slack_user_id}:"
            f"{message_ts or 'latest'}"
        )

        value = {
            "text": text,
            "channel_id": channel_id,
            "message_ts": message_ts,
            "source": "slack",
        }

        return self.context.remember(
            key=key,
            value=value,
            category="slack_interaction",
            actor_id=slack_user_id,
        )

    # ---------------------------------------------------------
    # RAISONNEMENT
    # ---------------------------------------------------------

    def reason(
        self,
        slack_user_id: str,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if self.context is None:
            return {
                "ok": False,
                "error": "cognitive_context_unavailable",
            }

        full_context = (
            context
            or self.build_context(
                slack_user_id,
                text,
            )
        )

        try:
            result = self.context.reason(
                text,
                full_context,
            )

            return result

        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
            }

    # ---------------------------------------------------------
    # MISSION
    # ---------------------------------------------------------

    def mission_context(
        self,
        slack_user_id: str,
        mission_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        if self.context is None:
            return {
                "ok": False,
                "error": "cognitive_context_unavailable",
            }

        return self.context.build(
            actor_id=slack_user_id,
            mission_id=mission_id,
        )

    # ---------------------------------------------------------
    # STATUT
    # ---------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "type": "gairus_slack_cognitive",
            "cognitive": bool(
                self.cognitive
            ),
            "context": bool(
                self.context
            ),
        }


_instance = None


def integrate_slack_cognitive(
    runtime: Any,
):
    global _instance

    _instance = GairusSlackCognitive(
        runtime
    )

    runtime.slack_cognitive = _instance

    return _instance


def get_slack_cognitive():
    return _instance
