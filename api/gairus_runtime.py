from __future__ import annotations

from typing import Optional

from config.gairus import CONFIG, GairusConfig
from core.system import (
    GairusSystem,
    build_system,
    get_system,
    reset_system,
)


def create_runtime(
    config: Optional[GairusConfig] = None,
) -> GairusSystem:
    """
    Crée une instance complète du système Gaïrus.
    """
    return build_system(
        config=config or CONFIG,
    )


def runtime(
    config: Optional[GairusConfig] = None,
) -> GairusSystem:
    """
    Retourne l'instance singleton du système Gaïrus.
    """
    return get_system(
        config=config or CONFIG,
    )


def reset_runtime():
    """
    Réinitialise l'instance singleton.
    """
    reset_system()


__all__ = [
    "GairusSystem",
    "create_runtime",
    "runtime",
    "build_system",
    "get_system",
    "reset_system",
]
