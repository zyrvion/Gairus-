"""
GAÏRUS — ToolRegistry (Section 16)
Outils réellement fonctionnels dans Termux, sans dépendance lourde.
"""
import os
import json
import requests
import config


def web_search(query: str) -> str:
    """Recherche web gratuite (DuckDuckGo Instant Answer, sans clé)."""
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1},
            timeout=10,
        )
        data = r.json()
        abstract = data.get("AbstractText") or ""
        related = [t.get("Text", "") for t in data.get("RelatedTopics", [])[:3] if isinstance(t, dict)]
        parts = [p for p in [abstract] + related if p]
        return "\n".join(parts) if parts else "Aucun résultat clair trouvé."
    except Exception as e:
        return f"Erreur recherche web : {e}"


def read_file(path: str) -> str:
    """Lecture limitée au dossier sandbox (Section 42 : jamais d'accès libre)."""
    full = os.path.join(config.SANDBOX_DIR, os.path.basename(path))
    if not os.path.exists(full):
        return f"Fichier introuvable dans le sandbox : {path}"
    with open(full, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()[:4000]


def write_file(path: str, content: str) -> str:
    full = os.path.join(config.SANDBOX_DIR, os.path.basename(path))
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Fichier écrit : {path} ({len(content)} caractères)"


def delete_file(path: str) -> str:
    return "Action refusée : suppression désactivée par défaut (RESTRICTED)."


REGISTRY = {
    "web_search": {
        "fn": web_search,
        "description": "Recherche une information sur le web.",
        "params": ["query"],
    },
    "read_file": {
        "fn": read_file,
        "description": "Lit un fichier du dossier sandbox de Gaïrus.",
        "params": ["path"],
    },
    "write_file": {
        "fn": write_file,
        "description": "Écrit/écrase un fichier dans le dossier sandbox.",
        "params": ["path", "content"],
    },
    "delete_file": {
        "fn": delete_file,
        "description": "Supprime un fichier (désactivé par défaut).",
        "params": ["path"],
    },
}


def list_tools_for_model() -> str:
    lines = []
    for name, spec in REGISTRY.items():
        lines.append(f"- {name}({', '.join(spec['params'])}) : {spec['description']}")
    return "\n".join(lines)


def run_tool(name: str, params: dict) -> str:
    if name not in REGISTRY:
        return f"Outil inconnu : {name}"
    fn = REGISTRY[name]["fn"]
    try:
        return fn(**params)
    except TypeError as e:
        return f"Paramètres invalides pour {name} : {e}"
