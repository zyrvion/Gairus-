from __future__ import annotations

import secrets
import string
import time
from typing import Any, Dict, Optional


class AccountProvisioner:

    HUMAN_REQUIRED_STATES = {
        "captcha",
        "otp",
        "email_verification",
        "phone_verification",
        "identity_verification",
        "manual_approval",
        "terms_confirmation",
    }

    def __init__(
        self,
        api_gateway=None,
        memory=None,
        audit=None,
        enterprise=None,
    ):
        self.api = api_gateway
        self.memory = memory
        self.audit = audit
        self.enterprise = enterprise

        self.accounts = {}
        self.pending = {}

    def _generate_password(self, length: int = 32) -> str:
        alphabet = (
            string.ascii_letters
            + string.digits
            + "!@#$%^&*_-+="
        )

        return "".join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

    def generate_account(
        self,
        service: str,
        username: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        account_id = (
            f"acct_"
            f"{int(time.time())}_"
            f"{secrets.token_hex(4)}"
        )

        account = {
            "account_id": account_id,
            "service": service,
            "username": username,
            "status": "generated",
            "metadata": metadata or {},
            "created_at": time.time(),
        }

        self.accounts[account_id] = account

        self._remember(
            "account_generated",
            {
                "account_id": account_id,
                "service": service,
                "username": username,
            },
        )

        return self._public(account)

    def create(
        self,
        service: str,
        registration_url: Optional[str] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        account = self.generate_account(
            service=service,
            username=username,
            metadata=metadata,
        )

        account_id = account["account_id"]

        if not registration_url:
            return {
                "ok": True,
                "status": "prepared",
                "account": account,
            }

        if self.api is None:
            return {
                "ok": False,
                "status": "api_unavailable",
                "account": account,
            }

        payload = {
            "username": username,
            "email": email,
            "service": service,
        }

        response = self.api.post(
            registration_url,
            json_data=payload,
            actor_id=actor_id,
            mission_id=mission_id,
        )

        validation = self._detect_human_validation(
            response
        )

        if validation:
            self.pending[account_id] = {
                "account_id": account_id,
                "service": service,
                "state": validation,
                "created_at": time.time(),
                "response": self._safe_response(
                    response
                ),
            }

            self.accounts[account_id][
                "status"
            ] = "waiting_human_validation"

            return {
                "ok": True,
                "status": "waiting_human_validation",
                "account": self._public(
                    self.accounts[account_id]
                ),
                "validation": validation,
            }

        if response.get("ok"):
            self.accounts[account_id][
                "status"
            ] = "created"

            self.accounts[account_id][
                "service_response"
            ] = self._safe_response(
                response
            )

            self._remember(
                "account_created",
                {
                    "account_id": account_id,
                    "service": service,
                    "actor_id": actor_id,
                    "mission_id": mission_id,
                },
            )

            return {
                "ok": True,
                "status": "created",
                "account": self._public(
                    self.accounts[account_id]
                ),
                "response": self._safe_response(
                    response
                ),
            }

        self.accounts[account_id][
            "status"
        ] = "creation_failed"

        return {
            "ok": False,
            "status": "creation_failed",
            "account": self._public(
                self.accounts[account_id]
            ),
            "response": self._safe_response(
                response
            ),
        }

    def configure(
        self,
        account_id: str,
        configuration: Dict[str, Any],
        endpoint: Optional[str] = None,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        account = self.accounts.get(
            account_id
        )

        if account is None:
            return {
                "ok": False,
                "status": "account_not_found",
            }

        account["configuration"] = (
            configuration
        )

        if not endpoint:
            account["status"] = "configured"

            self._remember(
                "account_configured",
                {
                    "account_id": account_id,
                    "actor_id": actor_id,
                    "mission_id": mission_id,
                },
            )

            return {
                "ok": True,
                "status": "configured",
                "account": self._public(
                    account
                ),
            }

        if self.api is None:
            return {
                "ok": False,
                "status": "api_unavailable",
                "account": self._public(
                    account
                ),
            }

        response = self.api.post(
            endpoint,
            json_data=configuration,
            actor_id=actor_id,
            mission_id=mission_id,
        )

        validation = self._detect_human_validation(
            response
        )

        if validation:
            self.pending[account_id] = {
                "account_id": account_id,
                "service": account["service"],
                "state": validation,
                "created_at": time.time(),
                "response": self._safe_response(
                    response
                ),
            }

            account["status"] = (
                "waiting_human_validation"
            )

            return {
                "ok": True,
                "status": "waiting_human_validation",
                "validation": validation,
                "account": self._public(
                    account
                ),
            }

        if response.get("ok"):
            account["status"] = "configured"

            account[
                "configuration_response"
            ] = self._safe_response(
                response
            )

            self._remember(
                "account_configured",
                {
                    "account_id": account_id,
                    "actor_id": actor_id,
                    "mission_id": mission_id,
                },
            )

            return {
                "ok": True,
                "status": "configured",
                "account": self._public(
                    account
                ),
                "response": self._safe_response(
                    response
                ),
            }

        account["status"] = "configuration_failed"

        return {
            "ok": False,
            "status": "configuration_failed",
            "account": self._public(
                account
            ),
            "response": self._safe_response(
                response
            ),
        }

    def pending_approvals(self):
        return {
            key: {
                "account_id": value.get(
                    "account_id"
                ),
                "service": value.get(
                    "service"
                ),
                "state": value.get(
                    "state"
                ),
                "created_at": value.get(
                    "created_at"
                ),
            }
            for key, value in self.pending.items()
        }

    def resolve_human_step(
        self,
        account_id: str,
        approved: bool,
        actor_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        pending = self.pending.get(
            account_id
        )

        if pending is None:
            return {
                "ok": False,
                "status": "pending_validation_not_found",
            }

        account = self.accounts.get(
            account_id
        )

        if account is None:
            return {
                "ok": False,
                "status": "account_not_found",
            }

        if not approved:
            account["status"] = (
                "cancelled"
            )

            del self.pending[account_id]

            self._remember(
                "account_validation_rejected",
                {
                    "account_id": account_id,
                    "actor_id": actor_id,
                },
            )

            return {
                "ok": True,
                "status": "cancelled",
                "account": self._public(
                    account
                ),
            }

        account["status"] = (
            "human_validation_completed"
        )

        del self.pending[account_id]

        self._remember(
            "account_validation_completed",
            {
                "account_id": account_id,
                "actor_id": actor_id,
            },
        )

        return {
            "ok": True,
            "status": "human_validation_completed",
            "account": self._public(
                account
            ),
        }

    def _detect_human_validation(
        self,
        response: Dict[str, Any],
    ) -> Optional[str]:

        if not response:
            return None

        status_code = response.get(
            "status_code"
        )

        data = response.get(
            "data"
        )

        text = str(
            data or ""
        ).lower()

        if (
            "captcha" in text
            or "recaptcha" in text
            or "hcaptcha" in text
        ):
            return "captcha"

        if (
            "otp" in text
            or "one-time password" in text
            or "verification code" in text
        ):
            return "otp"

        if (
            "email verification" in text
            or "verify your email" in text
        ):
            return "email_verification"

        if (
            "phone verification" in text
            or "verify your phone" in text
        ):
            return "phone_verification"

        if (
            "identity verification" in text
            or "verify your identity" in text
        ):
            return "identity_verification"

        if status_code in {
            401,
            403,
        } and not response.get("ok"):
            return "manual_approval"

        return None

    def _safe_response(
        self,
        response: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:

        if not response:
            return {}

        safe = dict(response)

        headers = safe.get(
            "headers"
        )

        if headers:
            safe["headers"] = {
                key: value
                for key, value in headers.items()
                if key.lower()
                not in {
                    "authorization",
                    "cookie",
                    "set-cookie",
                    "x-api-key",
                }
            }

        return safe

    def _public(
        self,
        account: Dict[str, Any],
    ) -> Dict[str, Any]:

        result = dict(account)

        for key in (
            "password",
            "token",
            "api_key",
            "secret",
            "private_key",
            "credentials",
        ):
            result.pop(
                key,
                None,
            )

        return result

    def _remember(
        self,
        event: str,
        payload: Dict[str, Any],
    ):

        if self.memory is None:
            return

        try:
            if hasattr(
                self.memory,
                "add_event",
            ):
                self.memory.add_event(
                    event,
                    payload,
                )

            elif hasattr(
                self.memory,
                "remember",
            ):
                self.memory.remember(
                    event,
                    payload,
                )
        except Exception:
            pass

    def status(self):

        return {
            "status": "available",
            "accounts": len(
                self.accounts
            ),
            "pending_validations": len(
                self.pending
            ),
            "api_gateway": (
                self.api is not None
            ),
            "human_validation_states": sorted(
                self.HUMAN_REQUIRED_STATES
            ),
        }
