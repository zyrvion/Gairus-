from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import Any, Dict, List, Optional

from core.gairus_capability_matrix import GairusCapabilityMatrix
from core.gairus_capabilities_201_500 import get_capabilities_201_500


class UnifiedGairusCapabilities:
    def __init__(self, runtime: Any = None):
        self.runtime = runtime
        self.capabilities_1_200 = GairusCapabilityMatrix(runtime)
        self.capabilities_201_500 = get_capabilities_201_500(runtime)

    def get(self, capability_id: int):
        capability_id = int(capability_id)
        if 1 <= capability_id <= 200:
            return self.capabilities_1_200.get(capability_id)
        if 201 <= capability_id <= 500:
            return self.capabilities_201_500.get(capability_id)
        return None

    def all(self) -> List[Any]:
        return sorted(
            self.capabilities_1_200.all() +
            self.capabilities_201_500.all(),
            key=lambda x: int(x.id)
        )

    def search(self, query: str) -> List[Any]:
        query = str(query or "").strip()
        if not query:
            return self.all()
        return sorted(
            self.capabilities_1_200.search(query) +
            self.capabilities_201_500.search(query),
            key=lambda x: int(x.id)
        )

    def by_domain(self, domain: str) -> List[Any]:
        return [
            x for x in self.all()
            if str(x.domain).lower() == str(domain).lower()
        ]

    def execute(
        self,
        capability_id: int,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        capability_id = int(capability_id)

        if 1 <= capability_id <= 200:
            result = self.capabilities_1_200.execute(
                capability_id, payload, **kwargs
            )
        elif 201 <= capability_id <= 500:
            result = self.capabilities_201_500.execute(
                capability_id, payload, **kwargs
            )
        else:
            return {
                "status": "error",
                "error": "capability_out_of_range",
                "capability_id": capability_id,
            }

        if isinstance(result, dict):
            result.setdefault("capability_id", capability_id)
            return result

        return {
            "status": "ok",
            "capability_id": capability_id,
            "result": result,
        }

    def run(self, capability_id: int, payload=None, **kwargs):
        return self.execute(capability_id, payload, **kwargs)

    def enable(self, capability_id: int) -> bool:
        engine = (
            self.capabilities_1_200
            if int(capability_id) <= 200
            else self.capabilities_201_500
        )
        return bool(engine.enable(capability_id))

    def disable(self, capability_id: int) -> bool:
        engine = (
            self.capabilities_1_200
            if int(capability_id) <= 200
            else self.capabilities_201_500
        )
        return bool(engine.disable(capability_id))

    def integrate_runtime(self, runtime: Any):
        runtime.unified_capabilities = self
        runtime.capabilities_unified = self
        runtime.capabilities = self
        return self

    def status(self):
        capabilities = self.all()
        domains = {}

        for capability in capabilities:
            domain = str(capability.domain)
            domains[domain] = domains.get(domain, 0) + 1

        return {
            "status": "ok",
            "type": "unified_gairus_capabilities",
            "total": len(capabilities),
            "expected": 500,
            "complete": len(capabilities) == 500,
            "range_1_200": len(self.capabilities_1_200.all()) == 200,
            "range_201_500": len(self.capabilities_201_500.all()) == 300,
            "domains": domains,
        }


_instance = None


def integrate_unified_capabilities(runtime):
    global _instance
    _instance = UnifiedGairusCapabilities(runtime)
    return _instance.integrate_runtime(runtime)


def get_unified_capabilities(runtime=None):
    global _instance
    if _instance is None:
        _instance = UnifiedGairusCapabilities(runtime)
    return _instance


def reset_unified_capabilities():
    global _instance
    _instance = None


if __name__ == "__main__":
    unified = UnifiedGairusCapabilities()
    status = unified.status()

    print("GAIRUS UNIFIED CAPABILITIES")
    print("=" * 40)
    print(f"Total: {status['total']}")
    print(f"Expected: {status['expected']}")
    print(f"Complete: {status['complete']}")
    print(f"1-200: {status['range_1_200']}")
    print(f"201-500: {status['range_201_500']}")
    print()
    print("Domains:")

    for domain, count in sorted(status["domains"].items()):
        print(f"  {domain}: {count}")
