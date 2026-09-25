from __future__ import annotations

import os
import platform
import time
from typing import Any, Dict, Optional


class HealthMonitor:
    """
    Moniteur de santé global de Gaïrus.

    Vérifie l'état des composants sans déclencher
    d'actions opérationnelles.
    """

    def __init__(
        self,
        runtime=None,
        enterprise=None,
        executor=None,
        controller=None,
        gateway=None,
        hierarchy=None,
        missions=None,
        autonomy=None,
        llm=None,
        memory=None,
    ):
        self.runtime = runtime
        self.enterprise = enterprise
        self.executor = executor
        self.controller = controller
        self.gateway = gateway
        self.hierarchy = hierarchy
        self.missions = missions
        self.autonomy = autonomy
        self.llm = llm
        self.memory = memory

        self.started_at = time.time()

    def _component(
        self,
        name: str,
        component: Any,
    ) -> Dict[str, Any]:
        if component is None:
            return {
                "name": name,
                "status": "unavailable",
                "available": False,
            }

        result = {
            "name": name,
            "status": "ok",
            "available": True,
            "class": component.__class__.__name__,
            "module": component.__class__.__module__,
        }

        status_method = getattr(
            component,
            "status",
            None,
        )

        if callable(status_method):
            try:
                component_status = status_method()

                if isinstance(component_status, dict):
                    result["details"] = component_status

            except Exception as exc:
                result["status"] = "degraded"
                result["status_error"] = str(exc)

        return result

    def components(self) -> Dict[str, Dict[str, Any]]:
        objects = {
            "runtime": self.runtime,
            "enterprise": self.enterprise,
            "controller": self.controller,
            "gateway": self.gateway,
            "executor": self.executor,
            "hierarchy": self.hierarchy,
            "missions": self.missions,
            "autonomy": self.autonomy,
            "llm": self.llm,
            "memory": self.memory,
        }

        return {
            name: self._component(
                name,
                component,
            )
            for name, component in objects.items()
        }

    def check_component(
        self,
        name: str,
    ) -> Dict[str, Any]:
        components = self.components()

        return components.get(
            name,
            {
                "name": name,
                "status": "unknown",
                "available": False,
            },
        )

    def check(self) -> Dict[str, Any]:
        components = self.components()

        unavailable = [
            name
            for name, result in components.items()
            if result.get("status") == "unavailable"
        ]

        degraded = [
            name
            for name, result in components.items()
            if result.get("status") == "degraded"
        ]

        if degraded:
            overall = "degraded"
        elif unavailable:
            overall = "partial"
        else:
            overall = "ok"

        return {
            "status": overall,
            "agent": "Gaïrus",
            "timestamp": time.time(),
            "uptime_seconds": round(
                time.time() - self.started_at,
                3,
            ),
            "components": components,
            "unavailable": unavailable,
            "degraded": degraded,
        }

    def readiness(self) -> Dict[str, Any]:
        """
        Vérifie si le noyau minimum de Gaïrus est disponible.
        """
        required = {
            "enterprise": self.enterprise,
            "controller": self.controller,
            "gateway": self.gateway,
            "executor": self.executor,
        }

        missing = [
            name
            for name, component in required.items()
            if component is None
        ]

        return {
            "ready": not missing,
            "missing": missing,
        }

    def liveness(self) -> Dict[str, Any]:
        return {
            "alive": True,
            "agent": "Gaïrus",
            "timestamp": time.time(),
        }

    def environment(self) -> Dict[str, Any]:
        return {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "system": platform.system(),
            "machine": platform.machine(),
            "pid": os.getpid(),
            "cwd": os.getcwd(),
        }

    def summary(self) -> Dict[str, Any]:
        health = self.check()
        readiness = self.readiness()

        return {
            "status": health["status"],
            "ready": readiness["ready"],
            "agent": "Gaïrus",
            "uptime_seconds": health["uptime_seconds"],
            "unavailable": health["unavailable"],
            "degraded": health["degraded"],
        }

    def status(self) -> Dict[str, Any]:
        return self.summary()
