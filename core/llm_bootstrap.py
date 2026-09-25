from __future__ import annotations

from typing import Any, Optional

from config.gairus import CONFIG, GairusConfig
from core.llm_manager import LLMManager


def bootstrap_llm(
    config: Optional[GairusConfig] = None,
    client: Any = None,
) -> LLMManager:
    """
    Construit le gestionnaire LLM central de Gaïrus.

    Le client concret peut être fourni plus tard, par exemple :
    - Ollama
    - llama.cpp
    - LM Studio
    - API compatible OpenAI
    """

    manager = LLMManager(
        config=config or CONFIG,
        client=client,
    )

    return manager


def llm_summary(
    manager: LLMManager,
):
    """
    Retourne un résumé compact de l'état du moteur LLM.
    """

    return manager.status()

