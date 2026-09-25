from __future__ import annotations

from core.final_external_runtime import get_final_gairus
from core.gairus_operations import GairusOperations


_instance = None


def get_operations_gairus():
    global _instance

    if _instance is None:
        agent = get_final_gairus()

        operations = GairusOperations(agent.runtime)

        agent.operations = operations

        runtime = getattr(
            agent,
            "runtime",
            None,
        )

        if runtime is not None:
            runtime.operations = operations

            health = getattr(
                runtime,
                "health",
                None,
            )

            if health is not None:
                try:
                    if hasattr(
                        health,
                        "register",
                    ):
                        health.register(
                            "operations",
                            operations,
                        )
                except Exception:
                    pass

        _instance = agent

    return _instance


def reset_operations_gairus():
    global _instance
    _instance = None


def build_operations_gairus():
    return get_operations_gairus()
