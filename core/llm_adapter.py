from __future__ import annotations

from typing import Any, Dict, Optional


class LLMAdapter:
    """
    Adaptateur entre le runtime Gaïrus et le client LLM existant.

    Il permet à Gaïrus d'utiliser le client présent dans
    core.llm_client.py sans imposer un fournisseur particulier.
    """

    def __init__(
        self,
        client: Any = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.client = client
        self.provider = provider
        self.model = model

    def _call_client(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        context = context or {}

        if self.client is None:
            raise RuntimeError("LLM client is not configured")

        if hasattr(self.client, "generate"):
            return self.client.generate(
                prompt=prompt,
                context=context,
                **kwargs,
            )

        if hasattr(self.client, "complete"):
            return self.client.complete(
                prompt=prompt,
                **kwargs,
            )

        if hasattr(self.client, "chat"):
            return self.client.chat(
                prompt=prompt,
                context=context,
                **kwargs,
            )

        if callable(self.client):
            return self.client(
                prompt=prompt,
                context=context,
                **kwargs,
            )

        raise TypeError(
            "Unsupported LLM client interface"
        )

    def generate(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        try:
            result = self._call_client(
                prompt=prompt,
                context=context,
                **kwargs,
            )

            return {
                "status": "ok",
                "provider": self.provider,
                "model": self.model,
                "result": result,
            }

        except Exception as exc:
            return {
                "status": "error",
                "provider": self.provider,
                "model": self.model,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            }

    def chat(
        self,
        messages: list,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if self.client is None:
            return {
                "status": "error",
                "error": "LLM client is not configured",
            }

        try:
            if hasattr(self.client, "chat"):
                result = self.client.chat(
                    messages=messages,
                    **kwargs,
                )

            elif hasattr(self.client, "generate"):
                prompt = "\n".join(
                    str(message.get("content", ""))
                    for message in messages
                    if isinstance(message, dict)
                )

                result = self.client.generate(
                    prompt=prompt,
                    **kwargs,
                )

            elif callable(self.client):
                result = self.client(
                    messages=messages,
                    **kwargs,
                )

            else:
                raise TypeError(
                    "Unsupported LLM client interface"
                )

            return {
                "status": "ok",
                "provider": self.provider,
                "model": self.model,
                "result": result,
            }

        except Exception as exc:
            return {
                "status": "error",
                "provider": self.provider,
                "model": self.model,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            }

    def status(self) -> Dict[str, Any]:
        return {
            "configured": self.client is not None,
            "provider": self.provider,
            "model": self.model,
        }
