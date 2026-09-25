from __future__ import annotations


def external_capabilities():

    return {
        "api_calls": {
            "enabled": True,
            "description": (
                "Appeler des API HTTP externes, "
                "lire leurs réponses et orchestrer des workflows."
            ),
            "methods": [
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
            ],
        },

        "account_creation": {
            "enabled": True,
            "description": (
                "Créer et configurer des comptes via les "
                "API et parcours d'inscription autorisés."
            ),
            "human_validation": True,
        },

        "account_configuration": {
            "enabled": True,
            "description": (
                "Configurer automatiquement les services "
                "après création d'un compte."
            ),
        },

        "credential_management": {
            "enabled": True,
            "description": (
                "Utiliser des secrets fournis par "
                "l'environnement sans les exposer dans les logs."
            ),
        },

        "external_workflows": {
            "enabled": True,
            "description": (
                "Enchaîner plusieurs API et services "
                "dans une même mission."
            ),
        },
    }
