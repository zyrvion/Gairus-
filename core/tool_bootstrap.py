from __future__ import annotations

from typing import Any, Dict, Optional

from tools.registry import ToolRegistry
from core.tool_runtime import ToolRuntime


def bootstrap_tools(
    registry: Optional[ToolRegistry] = None,
    router: Any = None,
) -> ToolRuntime:
    """
    Construit le runtime des outils de Gaïrus.

    Les outils sont enregistrés uniquement lorsqu'ils disposent
    des dépendances nécessaires.
    """

    runtime = ToolRuntime(registry=registry)

    if router is not None:
        try:
            from tools.slack_hierarchy import register as register_slack

            register_slack(
                runtime.registry,
                router,
            )
        except ImportError:
            pass

    return runtime


def tool_summary(runtime: ToolRuntime) -> Dict[str, Any]:
    """
    Retourne un résumé exploitable par le runtime principal.
    """

    return {
        "count": runtime.registry.count(),
        "tools": runtime.registry.list(),
        "history": len(runtime.history),
    }
