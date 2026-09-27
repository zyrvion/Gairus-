from __future__ import annotations
from core.gairus_self_evolution import get_self_evolution
from core.final_external_runtime import get_final_gairus
from core.gairus_operations import GairusOperations
from core.autonomous_integration import AutonomousIntegration
from core.autonomous_runtime_bridge import integrate_autonomous_runtime
from core.gairus_cognitive_evolution import get_cognitive_evolution
from core.gairus_cognitive_evolution_bridge import integrate_cognitive_evolution
_instance = None


def get_operations_gairus():
    global _instance

    if _instance is None:
        agent = get_final_gairus()

        runtime = getattr(agent, "runtime", None)

        if runtime is None:
            raise RuntimeError(
                "Gaïrus final runtime is unavailable"
            )

        # Couche opérations existante.
        operations = GairusOperations(runtime)

        agent.operations = operations
        runtime.operations = operations

        # Mémoire persistante + audit + événements.
        autonomous = AutonomousIntegration(runtime)

        agent.autonomous = autonomous
        runtime.autonomous_support = autonomous.support
        runtime.autonomous_integration = autonomous

        # Moteur autonome EXISTANT.
        bridge = integrate_autonomous_runtime(runtime)

        agent.autonomous_runtime = bridge
        runtime.autonomous_runtime_bridge = bridge
        cognitive = get_cognitive_evolution(runtime)
        agent.cognitive = cognitive
        runtime.cognitive = cognitive
        evolution = get_self_evolution(runtime)
        agent.self_evolution = evolution
        runtime.self_evolution = evolution
        cognitive_evolution = integrate_cognitive_evolution(runtime)
        agent.cognitive_evolution = cognitive_evolution
        runtime.cognitive_evolution = cognitive_evolution
        try:
            if hasattr(health, "register"):
                health.register(
                    "self_evolution",
                    evolution,
                )
        except Exception:
            pass
        try:
            cognitive.set_identity(
                "gairus.name",
                "Gaïrus",
                "identity",
            )
            cognitive.set_identity(
                "gairus.role",
                "Agent IA autonome généraliste",
                "identity",
            )
            cognitive.set_identity(
                "gairus.creator",
                "Arta Lyon Némésis",
                "creator and founder",
            )
        except Exception:
            pass
        # Santé.
        health = getattr(runtime, "health", None)

        if health is not None:
            try:
                if hasattr(health, "register"):
                    health.register(
                        "operations",
                        operations,
                    )
            except Exception:
                pass

            try:
                if hasattr(health, "register"):
                    health.register(
                        "autonomous",
                        autonomous,
                    )
            except Exception:
                pass

            try:
                if hasattr(health, "register"):
                    health.register(
                        "autonomous_runtime",
                        bridge,
                    )
            except Exception:
                pass

        # Démarrage du moteur 24/7 existant.
        try:
            bridge.start()
        except Exception:
            pass

        _instance = agent

    return _instance


def reset_operations_gairus():
    global _instance

    try:
        if _instance is not None:
            runtime = getattr(
                _instance,
                "runtime",
                None,
            )

            bridge = getattr(
                runtime,
                "autonomous_runtime_bridge",
                None,
            )

            if bridge is not None:
                bridge.stop()
    except Exception:
        pass

    _instance = None


def build_operations_gairus():
    return get_operations_gairus()
