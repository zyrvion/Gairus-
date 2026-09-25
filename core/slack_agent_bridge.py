from __future__ import annotations

from typing import Any, Dict, Optional


class SlackAgentBridge:

    def __init__(
        self,
        agent=None,
        integration=None,
    ):
        self.agent = agent
        self.integration = integration

    def attach(
        self,
        agent=None,
        integration=None,
    ):
        if agent is not None:
            self.agent = agent

        if integration is not None:
            self.integration = integration

        return self

    def identity(
        self,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:

        user_id = (
            event.get("user_id")
            or event.get("user")
            or event.get("user_id_slack")
        )

        team_id = event.get("team_id")
        channel_id = event.get("channel_id")

        return {
            "provider": "slack",
            "user_id": user_id,
            "team_id": team_id,
            "channel_id": channel_id,
        }

    def ask(
        self,
        text: str,
        event: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        event = event or {}

        actor = self.identity(event)

        if self.agent is None:
            return {
                "ok": False,
                "error": "agent_unavailable",
            }

        try:
            if hasattr(
                self.agent,
                "ask",
            ):
                result = self.agent.ask(
                    text,
                    actor_id=actor["user_id"],
                )
            elif hasattr(
                self.agent,
                "think",
            ):
                result = self.agent.think(
                    text,
                )
            else:
                return {
                    "ok": False,
                    "error": "agent_interface_unavailable",
                }

            return {
                "ok": True,
                "actor": actor,
                "result": result,
            }

        except TypeError:
            try:
                result = self.agent.ask(text)

                return {
                    "ok": True,
                    "actor": actor,
                    "result": result,
                }

            except Exception as exc:
                return {
                    "ok": False,
                    "actor": actor,
                    "error": str(exc),
                }

        except Exception as exc:
            return {
                "ok": False,
                "actor": actor,
                "error": str(exc),
            }

    def format_response(
        self,
        result: Dict[str, Any],
    ) -> str:

        if not result.get("ok"):
            return (
                "Gaïrus : "
                + str(
                    result.get(
                        "error",
                        "erreur inconnue",
                    )
                )
            )

        value = result.get("result")

        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            for key in (
                "response",
                "message",
                "answer",
                "text",
                "content",
            ):
                if key in value:
                    return str(
                        value[key]
                    )

        return str(value)

    def handle_event(
        self,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:

        text = (
            event.get("text")
            or event.get("command")
            or event.get("query")
            or ""
        ).strip()

        if not text:
            return {
                "ok": False,
                "error": "empty_message",
            }

        return self.ask(
            text,
            event,
        )

    def send(
        self,
        channel_id: str,
        text: str,
    ) -> Dict[str, Any]:

        if self.integration is None:
            return {
                "ok": False,
                "error": "slack_integration_unavailable",
            }

        try:
            if hasattr(
                self.integration,
                "send",
            ):
                return self.integration.send(
                    channel_id,
                    text,
                )

            if hasattr(
                self.integration,
                "post",
            ):
                return self.integration.post(
                    channel_id,
                    text,
                )

            return {
                "ok": False,
                "error": "slack_send_unavailable",
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
            }

    def handle_and_send(
        self,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:

        result = self.handle_event(
            event
        )

        text = self.format_response(
            result
        )

        channel_id = (
            event.get("channel_id")
            or event.get("channel")
        )

        if channel_id:
            send_result = self.send(
                channel_id,
                text,
            )
        else:
            send_result = {
                "ok": False,
                "error": "channel_missing",
            }

        return {
            "result": result,
            "send": send_result,
        }

    def status(self):

        return {
            "status": "available",
            "agent": self.agent is not None,
            "integration": (
                self.integration is not None
            ),
        }
