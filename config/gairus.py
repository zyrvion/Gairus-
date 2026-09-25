from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "oui",
    }


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class GairusConfig:
    """
    Configuration centrale de Gaïrus.

    Les valeurs sensibles restent dans les variables
    d'environnement et ne sont jamais codées en dur.
    """

    agent_name: str = "Gaïrus"
    environment: str = field(
        default_factory=lambda: os.getenv(
            "GAIRUS_ENV",
            "production",
        )
    )

    autonomy_enabled: bool = field(
        default_factory=lambda: _env_bool(
            "GAIRUS_AUTONOMY",
            True,
        )
    )

    approvals_enabled: bool = field(
        default_factory=lambda: _env_bool(
            "GAIRUS_APPROVALS",
            True,
        )
    )

    audit_enabled: bool = field(
        default_factory=lambda: _env_bool(
            "GAIRUS_AUDIT",
            True,
        )
    )

    slack_enabled: bool = field(
        default_factory=lambda: _env_bool(
            "GAIRUS_SLACK",
            True,
        )
    )

    llm_enabled: bool = field(
        default_factory=lambda: _env_bool(
            "GAIRUS_LLM_ENABLED",
            True,
        )
    )

    llm_provider: str = field(
        default_factory=lambda: os.getenv(
            "GAIRUS_LLM_PROVIDER",
            "ollama",
        )
    )

    llm_url: str = field(
        default_factory=lambda: os.getenv(
            "GAIRUS_LLM_URL",
            "http://127.0.0.1:11434",
        )
    )

    llm_model: str = field(
        default_factory=lambda: os.getenv(
            "GAIRUS_LLM_MODEL",
            "deepseek",
        )
    )

    max_plan_steps: int = field(
        default_factory=lambda: _env_int(
            "GAIRUS_MAX_PLAN_STEPS",
            100,
        )
    )

    request_timeout: int = field(
        default_factory=lambda: _env_int(
            "GAIRUS_REQUEST_TIMEOUT",
            60,
        )
    )

    data_dir: str = field(
        default_factory=lambda: os.getenv(
            "GAIRUS_DATA_DIR",
            "data",
        )
    )

    audit_file: str = field(
        default_factory=lambda: os.getenv(
            "GAIRUS_AUDIT_FILE",
            "data/audit_enterprise.jsonl",
        )
    )

    company_name: str = field(
        default_factory=lambda: os.getenv(
            "GAIRUS_COMPANY_NAME",
            "Entreprise Gaïrus",
        )
    )

    company_type: str = field(
        default_factory=lambda: os.getenv(
            "GAIRUS_COMPANY_TYPE",
            "SARL",
        )
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict,
    )

    def __post_init__(self):
        self.metadata.setdefault(
            "agent",
            self.agent_name,
        )

        self.metadata.setdefault(
            "environment",
            self.environment,
        )

    @classmethod
    def from_env(cls) -> "GairusConfig":
        return cls()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "environment": self.environment,
            "autonomy_enabled": self.autonomy_enabled,
            "approvals_enabled": self.approvals_enabled,
            "audit_enabled": self.audit_enabled,
            "slack_enabled": self.slack_enabled,
            "llm_enabled": self.llm_enabled,
            "llm_provider": self.llm_provider,
            "llm_url": self.llm_url,
            "llm_model": self.llm_model,
            "max_plan_steps": self.max_plan_steps,
            "request_timeout": self.request_timeout,
            "data_dir": self.data_dir,
            "audit_file": self.audit_file,
            "company_name": self.company_name,
            "company_type": self.company_type,
            "metadata": dict(self.metadata),
        }

    def safe_dict(self) -> Dict[str, Any]:
        """
        Version destinée aux logs et dashboards.

        Aucun secret ou token n'est exposé.
        """
        result = self.to_dict()

        if "llm_url" in result:
            result["llm_url"] = str(result["llm_url"])

        result.pop("metadata", None)

        return result

    def update(
        self,
        **values,
    ) -> "GairusConfig":
        allowed = {
            "agent_name",
            "environment",
            "autonomy_enabled",
            "approvals_enabled",
            "audit_enabled",
            "slack_enabled",
            "llm_enabled",
            "llm_provider",
            "llm_url",
            "llm_model",
            "max_plan_steps",
            "request_timeout",
            "data_dir",
            "audit_file",
            "company_name",
            "company_type",
        }

        for key, value in values.items():
            if key in allowed:
                setattr(self, key, value)

        return self


CONFIG = GairusConfig.from_env()
