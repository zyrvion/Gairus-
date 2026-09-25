from __future__ import annotations

from typing import Any, Dict, Optional


class SlackAdapter:
    """
    Adaptateur entre Gaïrus et le gateway Slack existant.

    Le gateway Slack reste responsable de la communication
    avec l'API Slack. Cet adaptateur fournit une interface
    propre au reste du système Gaïrus.
    """

    def __init__(self, gateway: Any = None):
        self.gateway = gateway

    def configure(self, gateway: Any):
        self.gateway = gateway
        return self

    def _require_gateway(self):
        if self.gateway is None:
            raise RuntimeError(
                "Slack gateway is not configured"
            )

        return self.gateway

    def send_message(
        self,
        channel: str,
        text: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        gateway = self._require_gateway()

        if hasattr(gateway, "send_message"):
            result = gateway.send_message(
                channel=channel,
                text=text,
                **kwargs,
            )

        elif hasattr(gateway, "send"):
            result = gateway.send(
                channel=channel,
                text=text,
                **kwargs,
            )

        elif callable(gateway):
            result = gateway(
                channel=channel,
                text=text,
                **kwargs,
            )

        else:
            raise TypeError(
                "Unsupported Slack gateway interface"
            )

        return {
            "status": "ok",
            "channel": channel,
            "result": result,
        }

    def post(
        self,
        channel: str,
        text: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return self.send_message(
            channel=channel,
            text=text,
            **kwargs,
        )

    def mention(
        self,
        user_id: str,
    ) -> str:
        if not user_id:
            return ""

        return f"<@{user_id}>"

    def status(self) -> Dict[str, Any]:
        return {
            "configured": self.gateway is not None,
            "gateway": (
                self.gateway.__class__.__name__
                if self.gateway is not None
                else None
            ),
        }
