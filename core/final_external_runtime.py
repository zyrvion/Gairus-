from __future__ import annotations

from core.full_bootstrap import get_full_runtime
from core.final_wiring import wire_runtime
from core.gairus import Gairus
from core.gairus_external import GairusExternal


_instance = None


def get_final_gairus():
    global _instance

    if _instance is None:

        runtime = get_full_runtime()

        runtime = wire_runtime(
            runtime
        )

        external = GairusExternal(
            runtime
        )

        runtime.external = external

        agent = Gairus(
            runtime=runtime
        )

        agent.external = external

        _instance = agent

    return _instance


def reset_final_gairus():

    global _instance
    _instance = None


def build_final_gairus():

    return get_final_gairus()
