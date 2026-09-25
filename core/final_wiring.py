from __future__ import annotations

from typing import Any


def wire_runtime(runtime: Any) -> Any:
    """
    Dernière couche de câblage de Gaïrus.

    Elle relie les composants déjà construits sans remplacer
    leurs fichiers d'origine.
    """

    # Autonomie -> hiérarchie
    if getattr(runtime, "autonomy", None) is not None:
        try:
            runtime.autonomy.hierarchy = runtime.hierarchy
        except Exception:
            pass

        try:
            runtime.autonomy.llm = runtime.llm
        except Exception:
            pass

    # Health -> composants réels
    health = getattr(runtime, "health", None)

    if health is not None:
        components = {
            "runtime": runtime,
            "enterprise": getattr(runtime, "enterprise", None),
            "controller": getattr(runtime, "controller", None),
            "gateway": getattr(runtime, "gateway", None),
            "executor": getattr(runtime, "executor", None),
            "hierarchy": getattr(runtime, "hierarchy", None),
            "missions": getattr(runtime, "missions", None),
            "autonomy": getattr(runtime, "autonomy", None),
            "llm": getattr(runtime, "llm", None),
            "memory": getattr(runtime, "memory", None),
        }

        for name, component in components.items():
            if component is None:
                continue

            try:
                if hasattr(health, "register"):
                    health.register(name, component)
                elif hasattr(health, "add"):
                    health.add(name, component)
            except Exception:
                pass

    return runtime


def finalize_runtime(runtime: Any) -> Any:
    return wire_runtime(runtime)
