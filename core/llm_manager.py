from __future__ import annotations

from typing import Any, Dict, Optional

from config.gairus import CONFIG, GairusConfig
from core.llm_adapter import LLMAdapter


class LLMManager:
    """
    Gestionnaire central du moteur de raisonnement de Gaïrus.

    Le reste du système ne dépend pas directement d'Ollama,
    llama.cpp, LM Studio ou d'une API distante.
    """

    def __init__(
        self,
        config: Optional[GairusConfig] = None,
        client: Any = None,
    ):
        self.config = config or CONFIG
        self.adapter = LLMAdapter(
            client=client,
            provider=self.config.llm_provider,
            model=self.config.llm_model,
        )

    @property
    def provider(self) -> str:
        return self.config.llm_provider

    @property
    def model(self) -> str:
        return self.config.llm_model

    @property
    def enabled(self) -> bool:
        return bool(self.config.llm_enabled)

    def configure(
        self,
        client: Any,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.adapter = LLMAdapter(
            client=client,
            provider=provider or self.provider,
            model=model or self.model,
        )

        return self.adapter

    def generate(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "status": "disabled",
                "provider": self.provider,
                "model": self.model,
            }

        return self.adapter.generate(
            prompt=prompt,
            context=context,
            **kwargs,
        )

    def chat(
        self,
        messages: list,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "status": "disabled",
                "provider": self.provider,
                "model": self.model,
            }

        return self.adapter.chat(
            messages=messages,
            **kwargs,
        )

    def think(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Alias sémantique pour les appels de raisonnement.
        """

        return self.generate(
            prompt=prompt,
            context=context,
            **kwargs,
        )

    def status(self) -> Dict[str, Any]:
        adapter_status = self.adapter.status()

        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "model": self.model,
            "configured": adapter_status.get(
                "configured",
                False,
            ),
        }
