from __future__ import annotations

from typing import Any, Dict

import autonomy


class AutonomousRuntimeBridge:
    """
    Pont final entre le runtime Gaïrus et le moteur d'autonomie existant.

    Ne crée pas de nouveau scheduler.
    Utilise exclusivement celui déjà présent dans autonomy.py.
    """

    def __init__(self, runtime: Any):
        if runtime is None:
            raise ValueError("runtime is required")

        self.runtime = runtime
        self.autonomy = getattr(runtime, "autonomy", None)

    def start(self):
        """
        Démarre le scheduler autonome existant.
        """
        scheduler = autonomy.start_autonomy_runtime()

        self.runtime.autonomy_scheduler = scheduler

        if scheduler is None:
            return {
                "ok": False,
                "started": False,
                "reason": "autonomy_disabled_or_start_failed",
            }

        return {
            "ok": True,
            "started": True,
            "scheduler": type(scheduler).__name__,
            "jobs": [
                {
                    "id": job.id,
                    "next_run": (
                        job.next_run_time.isoformat()
                        if job.next_run_time
                        else None
                    ),
                }
                for job in scheduler.get_jobs()
            ],
        }

    def stop(self):
        """
        Arrête le scheduler autonome existant.
        """
        stopped = autonomy.stop_autonomy_runtime()

        self.runtime.autonomy_scheduler = None

        return {
            "ok": True,
            "stopped": bool(stopped),
        }

    def cycle(self):
        """
        Exécute immédiatement un cycle autonome.
        """
        result = autonomy.autonomous_runtime_cycle()

        return {
            "ok": True,
            "result": result,
        }

    def status(self) -> Dict[str, Any]:
        """
        Retourne l'état réel du moteur d'autonomie.
        """
        try:
            status = autonomy.runtime_status()
        except Exception as exc:
            status = {
                "ok": False,
                "error": str(exc),
            }

        scheduler = getattr(
            self.runtime,
            "autonomy_scheduler",
            None,
        )

        return {
            "status": "ok",
            "type": "autonomous_runtime_bridge",
            "engine": (
                type(self.autonomy).__name__
                if self.autonomy is not None
                else None
            ),
            "scheduler": (
                type(scheduler).__name__
                if scheduler is not None
                else None
            ),
            "runtime_status": status,
        }


_bridge = None


def integrate_autonomous_runtime(runtime: Any):
    global _bridge

    _bridge = AutonomousRuntimeBridge(runtime)

    runtime.autonomous_runtime_bridge = _bridge

    return _bridge


def get_autonomous_runtime_bridge():
    return _bridge
