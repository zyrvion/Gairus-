from __future__ import annotations

from core.policy_engine import PolicyEngine
from core.policy_memory import PolicyMemory
from core.browser_operator import BrowserOperator


class GairusOperations:

    def __init__(
        self,
        runtime,
        *,
        founder_ids=None,
        ceo_ids=None,
        privileged_ids=None,
    ):

        self.runtime = runtime

        self.policy = PolicyEngine(
            founder_ids=founder_ids,
            ceo_ids=ceo_ids,
            privileged_ids=privileged_ids,
            audit=getattr(runtime, "audit", None),
        )

        self.policy_memory = PolicyMemory(
            getattr(runtime, "memory", None)
        )

        self.browser = BrowserOperator(
            audit=getattr(runtime, "audit", None),
            policy=self.policy,
        )

        self._bootstrap_rules()

    def _bootstrap_rules(self):

        self.policy_memory.remember(
            "gairus.security.rule",
            "Sensitive information is restricted by identity.",
        )

        self.policy_memory.remember(
            "gairus.hierarchy.rule",
            "Internal hierarchy is never disclosed to unauthorized actors.",
        )

        self.policy_memory.remember(
            "gairus.secrets.rule",
            "Credentials, tokens and private keys are never exposed in normal output.",
        )

        self.policy_memory.remember(
            "gairus.autonomy.rule",
            "Gaïrus may autonomously execute authorized operational tasks.",
        )

    # ---------------------------------------------------------
    # POLICY
    # ---------------------------------------------------------

    def authorize(
        self,
        actor_id,
        action,
        category=None,
    ):

        decision = self.policy.check_action(
            actor_id,
            action,
            category=category,
        )

        self.policy.audit_decision(
            actor_id,
            action,
            decision,
        )

        return decision

    # ---------------------------------------------------------
    # SENSITIVE OUTPUT
    # ---------------------------------------------------------

    def protect(
        self,
        actor_id,
        data,
        category,
    ):

        return self.policy.sanitize_output(
            actor_id,
            data,
            category,
        )

    # ---------------------------------------------------------
    # STATUS
    # ---------------------------------------------------------

    def status(self):

        return {
            "status": "available",
            "policy": self.policy.status(),
            "policy_memory": self.policy_memory.status(),
            "browser": self.browser.status(),
        }
