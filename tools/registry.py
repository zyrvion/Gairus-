from __future__ import annotations

from typing import Any, Dict, Optional


class ToolRegistry:
    """
    Registre central des outils de Gaïrus.

    Chaque outil est enregistré sous un nom unique.

    Le registre permet à Gaïrus de :
    - découvrir ses outils ;
    - récupérer un outil ;
    - vérifier son existence ;
    - exécuter un outil ;
    - exposer les capacités disponibles au moteur IA.
    """

    def __init__(self):
        self._tools: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # ENREGISTREMENT
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        tool: Any,
        overwrite: bool = False,
    ):

        if not name:
            raise ValueError(
                "Tool name cannot be empty"
            )

        if tool is None:
            raise ValueError(
                f"Tool '{name}' cannot be None"
            )

        if (
            name in self._tools
            and not overwrite
        ):
            raise ValueError(
                f"Tool '{name}' already registered"
            )

        self._tools[name] = tool

        return tool

    def unregister(self, name: str):
        return self._tools.pop(
            name,
            None,
        )

    # ------------------------------------------------------------------
    # RECHERCHE
    # ------------------------------------------------------------------

    def get(
        self,
        name: str,
        default=None,
    ):

        return self._tools.get(
            name,
            default,
        )

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self):
        return sorted(
            self._tools.keys()
        )

    def count(self) -> int:
        return len(
            self._tools
        )

    # ------------------------------------------------------------------
    # DESCRIPTION
    # ------------------------------------------------------------------

    def describe(
        self,
        name: str,
    ) -> Optional[Dict[str, Any]]:

        tool = self.get(name)

        if tool is None:
            return None

        return {
            "name": name,
            "description": getattr(
                tool,
                "description",
                "",
            ),
            "class": tool.__class__.__name__,
            "module": tool.__class__.__module__,
            "callable": callable(
                getattr(
                    tool,
                    "execute",
                    None,
                )
            ),
        }

    def catalog(self):
        return [
            self.describe(name)
            for name in self.list()
        ]

    # ------------------------------------------------------------------
    # EXÉCUTION
    # ------------------------------------------------------------------

    def execute(
        self,
        name: str,
        **kwargs,
    ):

        tool = self.get(name)

        if tool is None:
            raise KeyError(
                f"Unknown Gaïrus tool: {name}"
            )

        execute = getattr(
            tool,
            "execute",
            None,
        )

        if not callable(execute):
            raise TypeError(
                f"Tool '{name}' does not expose execute()"
            )

        return execute(
            **kwargs
        )

    # ------------------------------------------------------------------
    # APPEL SÉCURISÉ
    # ------------------------------------------------------------------

    def safe_execute(
        self,
        name: str,
        **kwargs,
    ):

        try:
            result = self.execute(
                name,
                **kwargs,
            )

            return {
                "status": "ok",
                "tool": name,
                "result": result,
            }

        except Exception as exc:

            return {
                "status": "error",
                "tool": name,
                "error": str(exc),
                "error_type": (
                    exc.__class__.__name__
                ),
            }

    # ------------------------------------------------------------------
    # EXPORT POUR LE MOTEUR IA
    # ------------------------------------------------------------------

    def ai_catalog(self):
        """
        Format compact destiné au moteur de raisonnement.
        """

        result = []

        for name in self.list():

            tool = self.get(name)

            result.append(
                {
                    "name": name,
                    "description": getattr(
                        tool,
                        "description",
                        "",
                    ),
                }
            )

        return result

    # ------------------------------------------------------------------
    # NETTOYAGE
    # ------------------------------------------------------------------

    def clear(self):
        self._tools.clear()

    def __contains__(self, name):
        return self.has(name)

    def __len__(self):
        return self.count()
