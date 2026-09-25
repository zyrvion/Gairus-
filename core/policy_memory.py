from __future__ import annotations

from typing import Any, Dict


class PolicyMemory:

    def __init__(self, memory=None):

        self.memory = memory
        self.local = {}

    def remember(
        self,
        key: str,
        value: Any,
    ):

        self.local[key] = value

        if self.memory is not None:
            try:
                if hasattr(self.memory, "remember"):
                    self.memory.remember(
                        key,
                        value,
                    )
            except Exception:
                pass

    def get(
        self,
        key: str,
        default=None,
    ):

        if key in self.local:
            return self.local[key]

        return default

    def snapshot(self):

        return dict(self.local)

    def status(self):

        return {
            "status": "available",
            "rules": len(self.local),
        }
