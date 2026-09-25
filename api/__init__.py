"""
API publique de Gaïrus.

Ce package expose les composants nécessaires pour intégrer
le runtime de Gaïrus à une application Flask, HTTP ou autre
interface externe.
"""

from .gairus_runtime import (
    GairusSystem,
    build_system,
    get_system,
    reset_system,
)

__all__ = [
    "GairusSystem",
    "build_system",
    "get_system",
    "reset_system",
]
