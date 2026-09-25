from __future__ import annotations

from typing import Any, Dict, Optional

from core.api_gateway import APIGateway
from core.account_provisioner import AccountProvisioner


class GairusExternal:

    def __init__(
        self,
        runtime,
    ):

        self.runtime = runtime

        self.api = APIGateway(
            audit=getattr(runtime, "audit", None),
        )

        self.accounts = AccountProvisioner(
            api_gateway=self.api,
            memory=getattr(runtime, "memory", None),
            audit=getattr(runtime, "audit", None),
            enterprise=getattr(runtime, "enterprise", None),
        )

    # ---------------------------------------------------------
    # API
    # ---------------------------------------------------------

    def api_request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_data: Any = None,
        headers: Optional[Dict[str, str]] = None,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        allow_external: bool = False,
    ):

        return self.api.request(
            method=method,
            url=url,
            params=params,
            json_data=json_data,
            headers=headers,
            actor_id=actor_id,
            mission_id=mission_id,
            allow_external=allow_external,
        )

    def get(self, url, **kwargs):
        return self.api.get(url, **kwargs)

    def post(self, url, **kwargs):
        return self.api.post(url, **kwargs)

    def put(self, url, **kwargs):
        return self.api.put(url, **kwargs)

    def patch(self, url, **kwargs):
        return self.api.patch(url, **kwargs)

    def delete(self, url, **kwargs):
        return self.api.delete(url, **kwargs)

    # ---------------------------------------------------------
    # COMPTES
    # ---------------------------------------------------------

    def create_account(
        self,
        service: str,
        *,
        signup_url: Optional[str] = None,
        email: Optional[str] = None,
        username: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
    ):

        return self.accounts.create(
            service=service,
            signup_url=signup_url,
            email=email,
            username=username,
            payload=payload,
            actor_id=actor_id,
            mission_id=mission_id,
        )

    def configure_account(
        self,
        account_id: str,
        endpoint: str,
        payload: Dict[str, Any],
        *,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
    ):

        return self.accounts.configure(
            account_id=account_id,
            endpoint=endpoint,
            payload=payload,
            actor_id=actor_id,
            mission_id=mission_id,
        )

    def pending_account_validations(self):
        return self.accounts.pending_approvals()

    def resolve_account_validation(
        self,
        account_id: str,
        state: str,
        approved: bool = False,
    ):

        return self.accounts.resolve_human_step(
            account_id,
            state,
            approved=approved,
        )

    # ---------------------------------------------------------
    # STATUS
    # ---------------------------------------------------------

    def status(self):

        return {
            "status": "available",
            "api": self.api.status(),
            "accounts": self.accounts.status(),
        }
