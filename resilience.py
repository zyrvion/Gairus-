from dotenv import load_dotenv
load_dotenv()

"""
GAÏRUS — Resilient Provider Router
Fallback multi-fournisseurs, retries, timeouts, cooldowns et circuit breaker.
"""

import os
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ProviderState:
    name: str
    capabilities: set = field(default_factory=set)
    priority: int = 100
    timeout: float = 45.0
    max_retries: int = 2
    cooldown: float = 30.0

    failures: int = 0
    successes: int = 0
    last_error: Optional[str] = None
    last_failure: float = 0.0
    last_success: float = 0.0
    disabled: bool = False

    def available(self) -> bool:
        if self.disabled:
            return False

        if self.last_failure <= 0:
            return True

        return (time.time() - self.last_failure) >= self.cooldown


class ResilientProviderRouter:
    """
    Routeur central de Gaïrus.

    Principe :

        fournisseur A
             ↓
          retry
             ↓
        fournisseur B
             ↓
          retry
             ↓
        fournisseur C

    Un fournisseur qui échoue plusieurs fois est temporairement
    placé en cooldown afin d'éviter de ralentir toute la mission.
    """

    def __init__(self):
        self.providers: Dict[str, ProviderState] = {}
        self.handlers: Dict[str, Callable[..., Any]] = {}
        self.lock = threading.RLock()

    # ---------------------------------------------------------
    # ENREGISTREMENT
    # ---------------------------------------------------------

    def register(
        self,
        name: str,
        handler: Callable[..., Any],
        capabilities=None,
        priority: int = 100,
        timeout: float = 45.0,
        max_retries: int = 2,
        cooldown: float = 30.0,
    ):
        capabilities = set(capabilities or {"text"})

        with self.lock:
            self.providers[name] = ProviderState(
                name=name,
                capabilities=capabilities,
                priority=priority,
                timeout=timeout,
                max_retries=max_retries,
                cooldown=cooldown,
            )

            self.handlers[name] = handler

    # ---------------------------------------------------------
    # DISPONIBILITÉ
    # ---------------------------------------------------------

    def _candidates(self, capability: str) -> List[ProviderState]:
        with self.lock:
            providers = [
                p
                for p in self.providers.values()
                if capability in p.capabilities
                and p.available()
                and self._provider_configured(p.name)
            ]

        providers.sort(
            key=lambda p: (
                p.priority,
                p.failures,
                -p.successes,
            )
        )

        return providers

    # ---------------------------------------------------------
    # EXÉCUTION
    # ---------------------------------------------------------

    def call(
        self,
        capability: str,
        *args,
        preferred: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:

        candidates = self._candidates(capability)

        if preferred:
            preferred_provider = next(
                (
                    p
                    for p in candidates
                    if p.name == preferred
                ),
                None,
            )

            if preferred_provider:
                candidates = [
                    preferred_provider
                ] + [
                    p
                    for p in candidates
                    if p.name != preferred
                ]

        if not candidates:
            return {
                "ok": False,
                "error": (
                    f"Aucun fournisseur disponible "
                    f"pour la capacité '{capability}'"
                ),
                "capability": capability,
            }

        errors = []

        for provider in candidates:

            handler = self.handlers.get(provider.name)

            if not handler:
                continue

            for attempt in range(provider.max_retries + 1):

                started = time.time()

                try:
                    result = self._execute_with_timeout(
                        handler,
                        provider.timeout,
                        *args,
                        **kwargs,
                    )

                    elapsed = time.time() - started

                    with self.lock:
                        provider.successes += 1
                        provider.failures = 0
                        provider.last_success = time.time()
                        provider.last_error = None

                    return {
                        "ok": True,
                        "provider": provider.name,
                        "attempt": attempt + 1,
                        "latency": round(elapsed, 3),
                        "result": result,
                    }

                except Exception as exc:

                    error = str(exc)

                    with self.lock:
                        provider.failures += 1
                        provider.last_error = error
                        provider.last_failure = time.time()

                    errors.append(
                        {
                            "provider": provider.name,
                            "attempt": attempt + 1,
                            "error": error,
                        }
                    )

                    if attempt < provider.max_retries:

                        delay = min(
                            2 ** attempt,
                            8,
                        )

                        time.sleep(delay)

            # fournisseur suivant

        return {
            "ok": False,
            "error": "Tous les fournisseurs ont échoué",
            "capability": capability,
            "attempts": errors,
        }

    # ---------------------------------------------------------
    # TIMEOUT
    # ---------------------------------------------------------

    @staticmethod
    def _execute_with_timeout(
        handler,
        timeout,
        *args,
        **kwargs,
    ):
        """
        Exécution avec timeout.

        Pour les handlers simples et synchrones, on utilise
        un thread daemon afin que le runtime principal ne soit
        pas bloqué indéfiniment.
        """

        result = []
        error = []

        def worker():
            try:
                result.append(
                    handler(*args, **kwargs)
                )
            except Exception as exc:
                error.append(exc)

        thread = threading.Thread(
            target=worker,
            daemon=True,
        )

        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            raise TimeoutError(
                f"Timeout après {timeout}s"
            )

        if error:
            raise error[0]

        return result[0] if result else None

    # ---------------------------------------------------------
    # ÉTAT
    # ---------------------------------------------------------

    def status(self):
        with self.lock:
            return {
                name: {
                    "capabilities": sorted(
                        provider.capabilities
                    ),
                    "priority": provider.priority,
                    "timeout": provider.timeout,
                    "max_retries": provider.max_retries,
                    "cooldown": provider.cooldown,
                    "failures": provider.failures,
                    "successes": provider.successes,
                    "available": provider.available(),
                    "last_error": provider.last_error,
                    "last_failure": provider.last_failure,
                    "last_success": provider.last_success,
                }
                for name, provider
                in self.providers.items()
            }


# Instance globale de Gaïrus
RESILIENT_ROUTER = ResilientProviderRouter()


def register_provider(
    name,
    handler,
    capabilities=None,
    priority=100,
    timeout=45,
    max_retries=2,
    cooldown=30,
):
    RESILIENT_ROUTER.register(
        name=name,
        handler=handler,
        capabilities=capabilities,
        priority=priority,
        timeout=timeout,
        max_retries=max_retries,
        cooldown=cooldown,
    )


def resilient_call(
    capability,
    *args,
    preferred=None,
    **kwargs,
):
    return RESILIENT_ROUTER.call(
        capability,
        *args,
        preferred=preferred,
        **kwargs,
    )


def resilient_status():
    return RESILIENT_ROUTER.status()
