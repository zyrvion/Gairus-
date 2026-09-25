from __future__ import annotations

from typing import Any, Dict, Optional

from config.gairus import CONFIG, GairusConfig


class LLMRuntime:
    """
    Couche unifiée d'accès au moteur LLM de Gaïrus.

    Le moteur concret reste interchangeable :
    Ollama, llama.cpp, LM Studio ou API compatible OpenAI.
    """

    def __init__(
        self,
        config: Optional[GairusConfig] = None,
        client: Any = None,
    ):
        self.config = config or CONFIG
        self.client = client

    @property
    def enabled(self) -> bool:
        return bool(self.config.llm_enabled)

    @property
    def provider(self) -> str:
        return self.config.llm_provider

    @property
    def model(self) -> str:
        return self.config.llm_model

    def generate(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "status": "disabled",
                "text": "",
            }

        if self.client is None:
            return {
                "status": "unconfigured",
                "provider": self.provider,
                "model": self.model,
                "prompt": prompt,
                "context": context or {},
            }

        try:
            if hasattr(self.client, "generate"):
                result = self.client.generate(
                    prompt=prompt,
                    context=context or {},
                    **kwargs,
                )

            elif callable(self.client):
                result = self.client(
                    prompt=prompt,
                    context=context or {},
                    **kwargs,
                )

            else:
                raise TypeError(
                    "LLM client does not expose generate()"
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
            "enabled": self.enabled,
            "provider": self.provider,
            "model": self.model,
            "configured": self.client is not None,
        }
