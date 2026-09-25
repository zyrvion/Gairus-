from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests


class APIGateway:

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(
        self,
        audit=None,
        allowed_domains=None,
        timeout: int = 30,
    ):
        self.audit = audit
        self.timeout = timeout
        self.allowed_domains = set(
            allowed_domains or []
        )
        self.history = []

    def allow_domain(self, domain: str):

        domain = self._normalize_domain(domain)

        if domain:
            self.allowed_domains.add(domain)

    def _normalize_domain(self, domain: str) -> str:

        domain = str(
            domain or ""
        ).strip().lower()

        if "://" in domain:

            parsed = urlparse(domain)

            domain = parsed.hostname or ""

        return domain.strip("/")

    def _domain_allowed(self, url: str) -> bool:

        parsed = urlparse(url)

        if parsed.scheme not in {
            "http",
            "https",
        }:
            return False

        hostname = (
            parsed.hostname or ""
        ).lower()

        if not self.allowed_domains:
            return True

        for domain in self.allowed_domains:

            if (
                hostname == domain
                or hostname.endswith(
                    "." + domain
                )
            ):
                return True

        return False

    def secret(
        self,
        env_name: str,
    ) -> Optional[str]:

        return os.getenv(env_name)

    def auth_headers(
        self,
        token_env: Optional[str] = None,
        scheme: str = "Bearer",
        header: str = "Authorization",
    ) -> Dict[str, str]:

        if not token_env:
            return {}

        token = self.secret(
            token_env
        )

        if not token:
            return {}

        return {
            header: f"{scheme} {token}"
        }

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[
            Dict[str, Any]
        ] = None,
        json_data: Any = None,
        data: Any = None,
        headers: Optional[
            Dict[str, str]
        ] = None,
        timeout: Optional[int] = None,
        allow_external: bool = False,
        actor_id: Optional[str] = None,
        mission_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        method = str(
            method or "GET"
        ).upper()

        if (
            not self._domain_allowed(url)
            and not allow_external
        ):
            raise PermissionError(
                f"Domaine API non autorisé: {url}"
            )

        if method not in (
            self.SAFE_METHODS
            | self.WRITE_METHODS
        ):
            raise ValueError(
                f"Méthode HTTP non supportée: {method}"
            )

        started = time.time()

        try:

            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                data=data,
                headers=headers or {},
                timeout=(
                    timeout
                    or self.timeout
                ),
            )

            duration = round(
                time.time() - started,
                4,
            )

            result = {
                "ok": response.ok,
                "status_code": response.status_code,
                "url": url,
                "method": method,
                "duration": duration,
                "headers": dict(
                    response.headers
                ),
            }

            try:
                result["data"] = (
                    response.json()
                )
            except Exception:
                result["data"] = (
                    response.text
                )

            self.history.append(
                {
                    "timestamp": time.time(),
                    "actor_id": actor_id,
                    "mission_id": mission_id,
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "ok": response.ok,
                    "duration": duration,
                }
            )

            self._audit(
                "api_request",
                {
                    "actor_id": actor_id,
                    "mission_id": mission_id,
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "ok": response.ok,
                    "duration": duration,
                },
            )

            return result

        except Exception as exc:

            duration = round(
                time.time() - started,
                4,
            )

            self._audit(
                "api_error",
                {
                    "actor_id": actor_id,
                    "mission_id": mission_id,
                    "method": method,
                    "url": url,
                    "error": str(exc),
                    "duration": duration,
                },
            )

            return {
                "ok": False,
                "status_code": None,
                "url": url,
                "method": method,
                "error": str(exc),
                "duration": duration,
            }

    def get(
        self,
        url,
        **kwargs,
    ):
        return self.request(
            "GET",
            url,
            **kwargs,
        )

    def post(
        self,
        url,
        **kwargs,
    ):
        return self.request(
            "POST",
            url,
            **kwargs,
        )

    def put(
        self,
        url,
        **kwargs,
    ):
        return self.request(
            "PUT",
            url,
            **kwargs,
        )

    def patch(
        self,
        url,
        **kwargs,
    ):
        return self.request(
            "PATCH",
            url,
            **kwargs,
        )

    def delete(
        self,
        url,
        **kwargs,
    ):
        return self.request(
            "DELETE",
            url,
            **kwargs,
        )

    def _audit(
        self,
        action: str,
        metadata: Dict[str, Any],
    ):

        if self.audit is None:
            return

        try:

            if hasattr(
                self.audit,
                "record",
            ):

                self.audit.record(
                    action=action,
                    metadata=metadata,
                )

            elif hasattr(
                self.audit,
                "log",
            ):

                self.audit.log(
                    action,
                    metadata,
                )

        except Exception:
            pass

    def status(self):

        return {
            "status": "available",
            "allowed_domains": sorted(
                self.allowed_domains
            ),
            "requests": len(
                self.history
            ),
            "timeout": self.timeout,
        }
