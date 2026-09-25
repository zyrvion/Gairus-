from __future__ import annotations

from typing import Any, Dict, Optional


class SlackIntegration:
    """
    Couche d'intégration Slack de Gaïrus.

    Elle ne remplace aucun gateway existant.
    Elle sert de pont entre les différents composants Slack.
    """

    def __init__(
        self,
        gateway: Any = None,
        router: Any = None,
    ):
        self.gateway = gateway
        self.router = router

    def configure(
        self,
        gateway: Any = None,
        router: Any = None,
    ):
        if gateway is not None:
            self.gateway = gateway

        if router is not None:
            self.router = router

        return self

    def configured(self) -> bool:
        return self.gateway is not None

    def send(
        self,
        channel: str,
        text: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:

        if self.gateway is None:
            raise RuntimeError(
                "Slack gateway is not configured"
            )

        if hasattr(self.gateway, "send_message"):
            result = self.gateway.send_message(
                channel=channel,
                text=text,
                **kwargs,
            )

        elif hasattr(self.gateway, "send"):
            result = self.gateway.send(
                channel=channel,
                text=text,
                **kwargs,
            )

        else:
            raise TypeError(
                "Slack gateway does not expose "
                "send_message() or send()"
            )

        return {
            "status": "ok",
            "channel": channel,
            "result": result,
        }

    def route_and_send(
        self,
        actor_id: str,
        message: str,
        target_id: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:

        if self.router is None:
            raise RuntimeError(
                "Slack hierarchy router is not configured"
            )

        route = self.router.route(
            actor_id=actor_id,
            target_id=target_id,
            reason=reason,
        )

        payload = self.router.build_message(
            actor_id=actor_id,
            target_id=target_id,
            reason=reason,
            message=message,
            **kwargs,
        )

        sent = self.send(
            channel=payload["channel"],
            text=payload["text"],
        )

        return {
            "status": "ok",
            "route": route,
            "message": payload,
            "sent": sent,
        }

    def status(self) -> Dict[str, Any]:
        return {
            "configured": self.configured(),
            "gateway": (
                self.gateway.__class__.__name__
                if self.gateway is not None
                else None
            ),
            "router": (
                self.router.__class__.__name__
                if self.router is not None
                else None
            ),
        }
