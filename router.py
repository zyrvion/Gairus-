"""
GAÏRUS — ModelRouter (Section 11, 38, 39 : FREE-FIRST ROUTING)
Essaie les fournisseurs gratuits configurés dans config.PROVIDERS, dans
l'ordre. Si aucun n'est disponible (pas de clé, panne réseau...), bascule
sur un mode local minimal plutôt que de planter (Section 23 : RecoveryEngine).
"""
import sys
import requests
import config


class NoProviderAvailable(Exception):
    pass


def _call_openai_compatible(provider: dict, messages: list) -> str:
    headers = {
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": provider["model"],
        "messages": messages,
        "temperature": 0.4,
    }
    r = requests.post(provider["base_url"], headers=headers, json=payload, timeout=30)
    if not r.ok:
        print(f"[GAIRUS][{provider['id']}] Erreur HTTP {r.status_code} : {r.text[:500]}",
              file=sys.stderr)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def _local_fallback(messages: list, had_key: bool) -> str:
    last_user = ""
    for m in reversed(messages):
        if m["role"] == "user":
            last_user = m["content"]
            break
    if had_key:
        return (
            "[Mode local — la clé API est bien présente, mais l'appel au "
            "modèle a échoué]\n"
            "Regarde le terminal Termux : une ligne '[GAIRUS][groq] Erreur HTTP ...' "
            "devrait indiquer la vraie cause (modèle invalide, quota dépassé, etc.).\n"
            f"Ta dernière demande était : « {last_user} »."
        )
    return (
        "[Mode local — aucun fournisseur de modèle configuré]\n"
        "Je n'ai pas encore de clé API gratuite renseignée (GROQ_API_KEY ou "
        "OPENROUTER_API_KEY), donc je ne peux pas raisonner avec un vrai modèle "
        f"pour l'instant. Ta dernière demande était : « {last_user} ». "
        "Ajoute une clé gratuite dans les variables d'environnement pour activer "
        "le raisonnement complet."
    )


def call_model(messages: list) -> str:
    had_key = False
    for provider in config.PROVIDERS:
        if config.NO_PAID_PROVIDERS and provider["paid"]:
            continue
        if not provider["api_key"]:
            continue
        had_key = True
        try:
            return _call_openai_compatible(provider, messages)
        except Exception as e:
            print(f"[GAIRUS][{provider['id']}] Exception : {e}", file=sys.stderr)
            continue
    return _local_fallback(messages, had_key)
