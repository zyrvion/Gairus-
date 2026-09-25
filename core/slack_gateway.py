from __future__ import annotations

import os
from typing import Any, Dict, Optional

from core.slack_adapter import SlackAdapter


class SlackGateway:
    """
    Gateway Slack utilisé par le noyau Gaïrus.

    Il utilise les identifiants Slack présents dans
    l'environnement et délègue la communication à l'API
    Slack via requests.
    """

    def __init__(
        self,
        token: Optional[str] = None,
    ):
        self.token = (
            token
            or os.getenv("SLACK_BOT_TOKEN", "")
        ).strip()

        self.adapter = SlackAdapter(
            gateway=self,
        )

    def configured(self) -> bool:
        return bool(self.token)

    def _headers(self):
        if not self.token:
            raise RuntimeError(
                "SLACK_BOT_TOKEN absent"
            )

        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": (
                "application/json; charset=utf-8"
            ),
        }

    def send_message(
        self,
        channel: str,
        text: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not channel:
            raise ValueError(
                "Slack channel is required"
            )

        if not text:
            raise ValueError(
                "Slack message cannot be empty"
            )

        import requests

        payload = {
            "channel": channel,
            "text": text,
        }

        payload.update(kwargs)

        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )

        data = response.json()

        if not data.get("ok"):
            raise RuntimeError(
                data.get(
                    "error",
                    "Slack API error",
                )
            )

        return data

    def send(
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
            "configured": self.configured(),
            "token": bool(self.token),
            "gateway": self.__class__.__name__,
        }
