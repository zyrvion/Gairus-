from provider_catalog import PROVIDERS as PROVIDER_CATALOG
from dotenv import load_dotenv
load_dotenv()

import os
import requests

TIMEOUT = int(os.getenv("GAIRUS_PROVIDER_TIMEOUT", "90"))

AI_PROVIDERS = {
    "gemini": {
        "env": "GEMINI_API_KEY",
        "base": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    },
    "groq": {
        "env": "GROQ_API_KEY",
        "base": "https://api.groq.com/openai/v1",
        "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
    },
    "mistral": {
        "env": "MISTRAL_API_KEY",
        "base": "https://api.mistral.ai/v1",
        "model": os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
    },
    "openrouter": {
        "env": "OPENROUTER_API_KEY",
        "base": "https://openrouter.ai/api/v1",
        "model": os.getenv("OPENROUTER_MODEL", "openrouter/free"),
    },
    "cerebras": {
        "env": "CEREBRAS_API_KEY",
        "base": "https://api.cerebras.ai/v1",
        "model": os.getenv("CEREBRAS_MODEL", "gpt-oss-120b"),
    },
    "nvidia": {
        "env": "NVIDIA_API_KEY",
        "base": "https://integrate.api.nvidia.com/v1",
        "model": os.getenv(
            "NVIDIA_MODEL",
            "meta/llama-3.3-70b-instruct"
        ),
    },
    "zai": {
        "env": "ZAI_API_KEY",
        "base": "https://api.z.ai/api/paas/v4",
        "model": os.getenv("ZAI_MODEL", "GLM-4.7-Flash"),
    },
}

FREE_PRICING = {"free_tier", "free_models"}


def free_provider_names():
    return [
        provider["id"]
        for provider in sorted(
            PROVIDER_CATALOG,
            key=lambda item: item.get("priority", 100),
        )
        if provider.get("pricing") in FREE_PRICING
        and provider.get("id") in AI_PROVIDERS
    ]


def provider_model(provider):
    cfg = next(
        (item for item in PROVIDER_CATALOG if item.get("id") == provider),
        None,
    )
    if not cfg:
        return None
    model_env = cfg.get("model_env", f"{provider.upper()}_MODEL")
    return os.getenv(model_env) or cfg.get("default_model") or cfg.get("model")


def call_openai_provider(name, prompt, system=None):
    # Recherche le fournisseur dans le catalogue réel.
    cfg = next(
        (
            item for item in PROVIDER_CATALOG
            if item.get("id") == name
        ),
        None,
    )

    if not cfg:
        raise RuntimeError(f"{name}: fournisseur introuvable")

    key_name = cfg.get("env")
    key = os.getenv(key_name, "").strip() if key_name else ""

    if not key:
        raise RuntimeError(f"{name}: clé absente")

    base = cfg.get("base_url") or cfg.get("base") or ""

    if not base:
        base_urls = {
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "groq": "https://api.groq.com/openai/v1",
            "mistral": "https://api.mistral.ai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "cerebras": "https://api.cerebras.ai/v1",
            "nvidia": "https://integrate.api.nvidia.com/v1",
            "zai": "https://api.z.ai/api/paas/v4",
        }
        base = base_urls.get(name, "")

    if not base:
        raise RuntimeError(f"{name}: URL API inconnue")

    model = provider_model(name)

    if not model:
        raise RuntimeError(f"{name}: modèle inconnu")

    messages = []

    if system:
        messages.append({
            "role": "system",
            "content": system,
        })

    messages.append({
        "role": "user",
        "content": prompt,
    })

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    if name == "openrouter":
        headers["HTTP-Referer"] = "https://gairus.onrender.com"
        headers["X-Title"] = "Gairus"

    response = requests.post(
        base.rstrip("/") + "/chat/completions",
        headers=headers,
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        },
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"]

def ask_provider(name, prompt, system=None):
    return call_openai_provider(
        name,
        prompt,
        system
    )


def ask_with_fallback(prompt, system=None):
    """Try configured providers catalogued as free-tier/free-models only."""
    order = free_provider_names()

    errors = []

    for provider in order:
        try:
            cfg = AI_PROVIDERS.get(provider)
            if not cfg:
                continue
            key_name = cfg.get("env")

            if not os.getenv(key_name):
                continue

            reply = ask_provider(
                provider,
                prompt,
                system
            )

            if reply:
                return {
                    "provider": provider,
                    "model": provider_model(provider),
                    "reply": reply,
                    "errors": errors,
                }

        except Exception as exc:
            errors.append({
                "provider": provider,
                "error": str(exc),
            })

    return {
        "provider": None,
        "model": None,
        "reply": (
            "Aucun fournisseur IA disponible n'a répondu."
        ),
        "errors": errors,
    }
# ============================================================
# GAÏRUS — BRANCHEMENT DU ROUTEUR RÉSILIENT
# ============================================================

try:
    from resilience import register_provider, resilient_call

    def _resilient_existing_provider(name, prompt, system=None):
        """
        Adaptateur entre le routeur résilient et le système
        de fournisseurs historique de Gaïrus.
        """
        return ask_provider(
            name,
            prompt,
            system=system,
        )

    # Fournisseurs réellement définis dans PROVIDERS.
    _RESILIENT_PROVIDER_NAMES = free_provider_names()
    _RESILIENT_PRIORITIES = {
        item["id"]: item.get("priority", 100)
        for item in PROVIDER_CATALOG
    }

    for _provider_name in _RESILIENT_PROVIDER_NAMES:
        if not any(item.get("id") == _provider_name for item in PROVIDER_CATALOG):
            continue

        try:
            register_provider(
                name=_provider_name,
                handler=lambda prompt, system=None, _name=_provider_name:
                    _resilient_existing_provider(
                        _name,
                        prompt,
                        system,
                    ),
                capabilities={"text", "reasoning"},
                priority=_RESILIENT_PRIORITIES.get(
                    _provider_name,
                    100,
                ),
                timeout=float(
                    os.getenv(
                        "GAIRUS_PROVIDER_TIMEOUT",
                        "60",
                    )
                ),
                max_retries=int(
                    os.getenv(
                        "GAIRUS_PROVIDER_RETRIES",
                        "1",
                    )
                ),
                cooldown=float(
                    os.getenv(
                        "GAIRUS_PROVIDER_COOLDOWN",
                        "20",
                    )
                ),
            )
        except Exception:
            pass

except Exception:
    # Le système historique reste fonctionnel même si le
    # module de résilience n'est momentanément pas disponible.
    pass


def ask_resilient(prompt, system=None, preferred=None):
    """
    Point d'entrée résilient pour le cerveau de Gaïrus.

    Utilisation :

        ask_resilient(
            "Explique-moi...",
            system="...",
        )

    Retourne le texte du fournisseur ayant réussi.
    """

    try:
        result = resilient_call(
            "text",
            prompt,
            system=system,
            preferred=preferred,
        )

        if result.get("ok"):
            provider_name = result.get("provider")

            return {
                "provider": provider_name,
                "model": provider_model(provider_name),
                "reply": result.get("result"),
                "errors": [],
            }

        # Dernier filet de sécurité :
        # retour au système historique.
        return ask_with_fallback(
            prompt,
            system=system,
        )

    except Exception:
        return ask_with_fallback(
            prompt,
            system=system,
        )


# ============================================================
# GAÏRUS DYNAMIC PROVIDER DISCOVERY
# ============================================================

def discover_provider_catalog():
    """
    Découvre automatiquement les fournisseurs dont les identifiants
    sont présents dans l'environnement.
    """
    import os

    discovered = []

    for provider in PROVIDER_CATALOG:
        env_name = provider.get("env")

        if not env_name:
            continue

        configured = bool(os.getenv(env_name, "").strip())

        if provider.get("type") == "local":
            configured = bool(os.getenv(env_name, "").strip())

        if configured:
            discovered.append({
                "id": provider["id"],
                "name": provider["name"],
                "model": os.getenv(
                    provider.get("model_env", ""),
                    provider.get("default_model", "")
                ),
                "type": provider["type"],
                "protocol": provider["protocol"],
                "capabilities": provider["capabilities"],
                "priority": provider["priority"],
                "pricing": provider["pricing"],
            })

    return sorted(discovered, key=lambda x: x["priority"])


def provider_network_status():
    """
    Retourne l'état de tout le réseau de fournisseurs.
    Ne retourne JAMAIS les valeurs des clés.
    """
    import os

    result = []

    for provider in PROVIDER_CATALOG:
        env_name = provider.get("env")
        configured = bool(
            os.getenv(env_name, "").strip()
        ) if env_name else False

        result.append({
            "id": provider["id"],
            "name": provider["name"],
            "configured": configured,
            "type": provider["type"],
            "pricing": provider["pricing"],
            "priority": provider["priority"],
            "capabilities": provider["capabilities"],
        })

    return result


# === GAIRUS_DYNAMIC_NETWORK_ROUTER ===
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

try:
    from provider_catalog import PROVIDERS as PROVIDER_CATALOG
    from resilience import RESILIENT_ROUTER
except Exception:
    PROVIDER_CATALOG = []
    RESILIENT_ROUTER = None


def _catalog_provider_configured(provider):
    import os
    env_name = provider.get("env")
    if not env_name:
        return False
    return bool(os.getenv(env_name, "").strip())


def configured_provider_catalog():
    return [
        p for p in PROVIDER_CATALOG
        if _catalog_provider_configured(p)
    ]


def provider_network():
    result = []

    for p in PROVIDER_CATALOG:
        result.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("type"),
            "protocol": p.get("protocol"),
            "model": p.get("default_model"),
            "configured": _catalog_provider_configured(p),
            "priority": p.get("priority", 100),
            "capabilities": p.get("capabilities", []),
        })

    return sorted(
        result,
        key=lambda x: (
            not x["configured"],
            x["priority"],
            x["name"] or ""
        )
    )


def ask_network(prompt, system=None, preferred=None):
    """
    Point d'entrée principal de Gaïrus.
    Utilise d'abord le routeur résilient existant.
    Si aucun fournisseur configuré n'est disponible,
    retombe sur l'ancien système de fallback.
    """

    try:
        if RESILIENT_ROUTER is not None:
            result = ask_resilient(
                prompt,
                system=system,
                preferred=preferred
            )

            if result and result.get("reply"):
                return result

    except Exception as e:
        fallback_error = str(e)
    else:
        fallback_error = None

    try:
        reply = ask_with_fallback(prompt, system=system)

        return {
            "provider": "legacy-fallback",
            "model": None,
            "reply": reply,
            "errors": [fallback_error] if fallback_error else []
        }

    except Exception as e:
        return {
            "provider": None,
            "model": None,
            "reply": "Aucun fournisseur IA disponible.",
            "errors": [str(e)]
        }


def network_health():
    configured = configured_provider_catalog()

    return {
        "ok": True,
        "total": len(PROVIDER_CATALOG),
        "configured": len(configured),
        "providers": [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("type"),
                "protocol": p.get("protocol"),
                "model": p.get("default_model"),
            }
            for p in configured
        ]
    }

# === END GAIRUS_DYNAMIC_NETWORK_ROUTER ===
