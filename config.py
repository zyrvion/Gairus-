"""
GAÏRUS — Configuration centrale
Section 0 (FREE-FIRST) + Section 17 (Permissions) + Section 18 (Autonomie)
"""
import os

# --- Section 0 : philosophie FREE-FIRST -------------------------------
# Si True : aucune requête vers un fournisseur payant n'est jamais envoyée.
NO_PAID_PROVIDERS = os.environ.get("NO_PAID_PROVIDERS", "true").lower() == "true"

# --- Section 18 : niveau d'autonomie -----------------------------------
# ASSISTED    : Gaïrus propose seulement.
# SUPERVISED  : Gaïrus exécute le SAFE, demande confirmation pour CONFIRM.
# AUTONOMOUS  : Gaïrus exécute SAFE + CONFIRM sans redemander.
AUTONOMY_LEVEL = os.environ.get("GAIRUS_AUTONOMY", "SUPERVISED")

# --- Fournisseurs de modèles (Section 11 / 38 / 39) --------------------
# Clés lues depuis l'environnement — jamais codées en dur (Section 44).
# Aucune ici n'est obligatoire : si aucune clé n'est présente, Gaïrus
# tombe automatiquement sur le mode local "raisonnement minimal".
PROVIDERS = [
    {
        "id": "groq",
        "name": "Groq (gratuit, très rapide)",
        "paid": False,
        "api_key": os.environ.get("GROQ_API_KEY", ""),
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "openai/gpt-oss-120b",
    },
    {
        "id": "openrouter_free",
        "name": "OpenRouter (modèles gratuits)",
        "paid": False,
        "api_key": os.environ.get("OPENROUTER_API_KEY", ""),
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "meta-llama/llama-3.1-8b-instruct:free",
    },
]

# --- Mémoire (Section 13) ----------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "gairus_memory.db")

# --- Sandbox fichiers (Section 6 / 42 : jamais d'accès libre au disque) -
SANDBOX_DIR = os.path.join(os.path.dirname(__file__), "sandbox")
os.makedirs(SANDBOX_DIR, exist_ok=True)

# --- Permissions par outil (Section 17) ---------------------------------
# SAFE = auto  |  CONFIRM = on demande  |  RESTRICTED = jamais
TOOL_PERMISSIONS = {
    "web_search": "SAFE",
    "read_file": "SAFE",
    "write_file": "CONFIRM",
    "delete_file": "RESTRICTED",
}
