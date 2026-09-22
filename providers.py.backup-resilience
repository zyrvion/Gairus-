import os
import requests

TIMEOUT = int(os.getenv("GAIRUS_PROVIDER_TIMEOUT", "90"))

PROVIDERS = {
    "gemini": {
        "env": "GOOGLE_API_KEY",
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
}


def call_openai_provider(name, prompt, system=None):
    cfg = PROVIDERS[name]
    key = os.getenv(cfg["env"])

    if not key:
        raise RuntimeError(f"{name}: clé absente")

    messages = []

    if system:
        messages.append({
            "role": "system",
            "content": system
        })

    messages.append({
        "role": "user",
        "content": prompt
    })

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    if name == "openrouter":
        headers["HTTP-Referer"] = "https://gairus.onrender.com"
        headers["X-Title"] = "Gairus"

    response = requests.post(
        cfg["base"].rstrip("/") + "/chat/completions",
        headers=headers,
        json={
            "model": cfg["model"],
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
    """
    Fallback gratuit/prioritaire de Gaïrus.

    Ordre :
    Gemini -> Groq -> OpenRouter -> Mistral
    """

    order = [
        "gemini",
        "groq",
        "openrouter",
        "mistral",
    ]

    errors = []

    for provider in order:
        try:
            key_name = PROVIDERS[provider]["env"]

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
                    "model": PROVIDERS[provider]["model"],
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
