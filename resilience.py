from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

"""
GAÏRUS — Resilient Provider Router

Routeur multi-fournisseurs :
- ordre de priorité
- retry par fournisseur
- timeout
- cooldown
- circuit breaker léger
- bascule automatique vers le fournisseur suivant
- fournisseur préféré optionnel
- aucun nombre maximum de fournisseurs imposé

Le routeur ne connaît pas les clés API.
Les fournisseurs sont enregistrés par providers.py.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ProviderState:
    name: str

    capabilities: set = field(default_factory=set)

    priority: int = 100

    timeout: float = 45.0

    max_retries: int = 1

    cooldown: float = 20.0

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

        elapsed = time.time() - self.last_failure

        return elapsed >= self.cooldown


class ResilientProviderRouter:
    """
    Routeur central de Gaïrus.

    Exemple :

        Gemini
           ↓ échec
        Groq
           ↓ échec
        Mistral
           ↓ échec
        DeepSeek
           ↓
        succès

    Le routeur continue automatiquement avec le fournisseur
    suivant lorsqu'un fournisseur échoue.

    Il n'existe volontairement aucun nombre maximal global
    de fournisseurs.
    """

    def __init__(self):
        self.providers: Dict[str, ProviderState] = {}

        self.handlers: Dict[str, Callable[..., Any]] = {}

        self.lock = threading.RLock()

    # ========================================================
    # ENREGISTREMENT
    # ========================================================

    def register(
        self,
        name: str,
        handler: Callable[..., Any],
        capabilities=None,
        priority: int = 100,
        timeout: float = 45.0,
        max_retries: int = 1,
        cooldown: float = 20.0,
    ):
        if not name:
            raise ValueError("Nom de fournisseur obligatoire.")

        if not callable(handler):
            raise ValueError(
                f"{name}: handler fournisseur invalide."
            )

        capabilities = set(
            capabilities or {"text"}
        )

        with self.lock:
            existing = self.providers.get(name)

            if existing:
                failures = existing.failures
                successes = existing.successes
                last_error = existing.last_error
                last_failure = existing.last_failure
                last_success = existing.last_success
                disabled = existing.disabled
            else:
                failures = 0
                successes = 0
                last_error = None
                last_failure = 0.0
                last_success = 0.0
                disabled = False

            self.providers[name] = ProviderState(
                name=name,
                capabilities=capabilities,
                priority=int(priority),
                timeout=float(timeout),
                max_retries=max(0, int(max_retries)),
                cooldown=max(0.0, float(cooldown)),
                failures=failures,
                successes=successes,
                last_error=last_error,
                last_failure=last_failure,
                last_success=last_success,
                disabled=disabled,
            )

            self.handlers[name] = handler

    # ========================================================
    # CONTRÔLE
    # ========================================================

    def enable(self, name: str):
        with self.lock:
            provider = self.providers.get(name)

            if not provider:
                raise KeyError(
                    f"Fournisseur inconnu : {name}"
                )

            provider.disabled = False

    def disable(self, name: str):
        with self.lock:
            provider = self.providers.get(name)

            if not provider:
                raise KeyError(
                    f"Fournisseur inconnu : {name}"
                )

            provider.disabled = True

    def reset_provider(self, name: str):
        with self.lock:
            provider = self.providers.get(name)

            if not provider:
                raise KeyError(
                    f"Fournisseur inconnu : {name}"
                )

            provider.failures = 0
            provider.last_error = None
            provider.last_failure = 0.0
            provider.disabled = False

    # ========================================================
    # CANDIDATS
    # ========================================================

    @staticmethod
    def _provider_configured(name: str) -> bool:
        try:
            import os
            from provider_catalog import PROVIDERS

            cfg = next(
                (
                    item
                    for item in PROVIDERS
                    if item.get("id") == name
                ),
                None,
            )

            if not cfg:
                return False

            env_name = cfg.get("env")

            if not env_name:
                return False

            configured = bool(os.getenv(env_name, "").strip())
            if name == "gemini":
                configured = configured or bool(
                    os.getenv("GOOGLE_API_KEY", "").strip()
                )
            if name == "cloudflare":
                configured = configured and bool(
                    os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
                )
            return configured

        except Exception:
            return False

    def _candidates(
        self,
        capability: str,
    ) -> List[ProviderState]:

        with self.lock:
            providers = [
                provider
                for provider in self.providers.values()
                if capability in provider.capabilities
                and provider.available()
                and provider.name in self.handlers
            ]

        providers.sort(
            key=lambda provider: (
                provider.priority,
                provider.failures,
                -provider.successes,
            )
        )

        return providers

    # ========================================================
    # APPEL
    # ========================================================

    def call(
        self,
        capability: str,
        *args,
        preferred: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:

        candidates = self._candidates(
            capability
        )

        if preferred:
            preferred_provider = next(
                (
                    provider
                    for provider in candidates
                    if provider.name == preferred
                ),
                None,
            )

            if preferred_provider:
                candidates = [
                    preferred_provider
                ] + [
                    provider
                    for provider in candidates
                    if provider.name != preferred
                ]

        if not candidates:
            return {
                "ok": False,
                "error": (
                    "Aucun fournisseur configuré "
                    f"pour la capacité '{capability}'."
                ),
                "capability": capability,
                "attempts": [],
            }

        errors = []

        for provider in candidates:

            handler = self.handlers.get(
                provider.name
            )

            if not handler:
                continue

            total_attempts = (
                provider.max_retries + 1
            )

            for attempt in range(
                total_attempts
            ):

                started = time.time()

                try:

                    result = (
                        self._execute_with_timeout(
                            handler,
                            provider.timeout,
                            *args,
                            **kwargs,
                        )
                    )

                    elapsed = (
                        time.time() - started
                    )

                    if result is None:
                        raise RuntimeError(
                            "Le fournisseur a retourné "
                            "une réponse vide."
                        )

                    if (
                        isinstance(result, str)
                        and not result.strip()
                    ):
                        raise RuntimeError(
                            "Le fournisseur a retourné "
                            "une réponse vide."
                        )

                    with self.lock:

                        provider.successes += 1

                        provider.failures = 0

                        provider.last_success = (
                            time.time()
                        )

                        provider.last_error = None

                        provider.last_failure = 0.0

                    return {
                        "ok": True,
                        "provider": provider.name,
                        "attempt": attempt + 1,
                        "latency": round(
                            elapsed,
                            3,
                        ),
                        "result": result,
                        "attempts": errors,
                    }

                except Exception as exc:

                    error = (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )

                    with self.lock:

                        provider.failures += 1

                        provider.last_error = error

                        provider.last_failure = (
                            time.time()
                        )

                    errors.append(
                        {
                            "provider": (
                                provider.name
                            ),
                            "attempt": (
                                attempt + 1
                            ),
                            "error": error,
                        }
                    )

                    if attempt < total_attempts - 1:

                        delay = min(
                            2 ** attempt,
                            8,
                        )

                        time.sleep(delay)

            # ------------------------------------------------
            # IMPORTANT :
            # Le fournisseur courant a échoué.
            # On passe automatiquement au suivant.
            # ------------------------------------------------

        return {
            "ok": False,
            "error": (
                "Tous les fournisseurs configurés "
                "pour cette capacité ont échoué."
            ),
            "capability": capability,
            "attempts": errors,
        }

    # ========================================================
    # TIMEOUT
    # ========================================================

    @staticmethod
    def _execute_with_timeout(
        handler,
        timeout,
        *args,
        **kwargs,
    ):
        result = []

        error = []

        def worker():
            try:
                result.append(
                    handler(
                        *args,
                        **kwargs,
                    )
                )

            except Exception as exc:
                error.append(exc)

        thread = threading.Thread(
            target=worker,
            daemon=True,
        )

        thread.start()

        thread.join(
            max(
                0.1,
                float(timeout),
            )
        )

        if thread.is_alive():
            raise TimeoutError(
                f"Timeout après {timeout}s."
            )

        if error:
            raise error[0]

        if not result:
            return None

        return result[0]

    # ========================================================
    # ÉTAT
    # ========================================================

    def status(self):

        with self.lock:

            return {
                name: {
                    "capabilities": sorted(
                        provider.capabilities
                    ),
                    "priority": (
                        provider.priority
                    ),
                    "timeout": (
                        provider.timeout
                    ),
                    "max_retries": (
                        provider.max_retries
                    ),
                    "cooldown": (
                        provider.cooldown
                    ),
                    "failures": (
                        provider.failures
                    ),
                    "successes": (
                        provider.successes
                    ),
                    "available": (
                        provider.available()
                    ),
                    "disabled": (
                        provider.disabled
                    ),
                    "last_error": (
                        provider.last_error
                    ),
                    "last_failure": (
                        provider.last_failure
                    ),
                    "last_success": (
                        provider.last_success
                    ),
                }

                for name, provider
                in self.providers.items()
            }


# ============================================================
# INSTANCE GLOBALE
# ============================================================

RESILIENT_ROUTER = (
    ResilientProviderRouter()
)


# ============================================================
# API PUBLIQUE
# ============================================================

def register_provider(
    name,
    handler,
    capabilities=None,
    priority=100,
    timeout=45,
    max_retries=1,
    cooldown=20,
):
    return RESILIENT_ROUTER.register(
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
