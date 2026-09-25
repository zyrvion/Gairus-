from __future__ import annotations

import time
from typing import Any, Dict, Optional


class BrowserOperator:
    """
    Opérateur navigateur de Gaïrus.

    Il fournit une abstraction permettant à un backend navigateur
    (Playwright ou autre) d'être branché sans modifier le moteur
    d'autonomie.

    Le moteur décide quoi faire.
    Le BrowserOperator exécute les opérations navigateur.
    """

    def __init__(
        self,
        browser=None,
        audit=None,
        policy=None,
    ):

        self.browser = browser
        self.audit = audit
        self.policy = policy

        self.sessions: Dict[str, Any] = {}
        self.history = []

    # ---------------------------------------------------------
    # SESSION
    # ---------------------------------------------------------

    def attach(
        self,
        session_id: str,
        page: Any,
    ):

        self.sessions[session_id] = page

        self._record(
            "browser_session_attached",
            {
                "session_id": session_id,
            },
        )

        return {
            "ok": True,
            "session_id": session_id,
        }

    def detach(
        self,
        session_id: str,
    ):

        self.sessions.pop(
            session_id,
            None,
        )

        return {
            "ok": True,
            "session_id": session_id,
        }

    # ---------------------------------------------------------
    # NAVIGATION
    # ---------------------------------------------------------

    def open(
        self,
        session_id: str,
        url: str,
    ):

        page = self._page(session_id)

        result = page.goto(url)

        self._record(
            "browser_open",
            {
                "session_id": session_id,
                "url": url,
            },
        )

        return {
            "ok": True,
            "url": url,
            "result": str(result),
        }

    # ---------------------------------------------------------
    # ACTIONS
    # ---------------------------------------------------------

    def click(
        self,
        session_id: str,
        selector: str,
    ):

        page = self._page(session_id)

        page.click(selector)

        return {
            "ok": True,
            "action": "click",
            "selector": selector,
        }

    def fill(
        self,
        session_id: str,
        selector: str,
        value: str,
    ):

        page = self._page(session_id)

        page.fill(
            selector,
            value,
        )

        return {
            "ok": True,
            "action": "fill",
            "selector": selector,
        }

    def press(
        self,
        session_id: str,
        selector: str,
        key: str,
    ):

        page = self._page(session_id)

        page.press(
            selector,
            key,
        )

        return {
            "ok": True,
            "action": "press",
            "selector": selector,
            "key": key,
        }

    # ---------------------------------------------------------
    # LECTURE
    # ---------------------------------------------------------

    def text(
        self,
        session_id: str,
        selector: Optional[str] = None,
    ):

        page = self._page(session_id)

        if selector:
            value = page.text_content(selector)
        else:
            value = page.locator("body").inner_text()

        return {
            "ok": True,
            "text": value,
        }

    def title(
        self,
        session_id: str,
    ):

        page = self._page(session_id)

        return {
            "ok": True,
            "title": page.title(),
        }

    # ---------------------------------------------------------
    # CAPTURE
    # ---------------------------------------------------------

    def screenshot(
        self,
        session_id: str,
        path: str,
    ):

        page = self._page(session_id)

        page.screenshot(
            path=path,
        )

        return {
            "ok": True,
            "path": path,
        }

    # ---------------------------------------------------------
    # INTERNAL
    # ---------------------------------------------------------

    def _page(
        self,
        session_id: str,
    ):

        page = self.sessions.get(
            session_id
        )

        if page is None:
            raise KeyError(
                f"Session navigateur inconnue: {session_id}"
            )

        return page

    def _record(
        self,
        action: str,
        metadata: Dict[str, Any],
    ):

        event = {
            "timestamp": time.time(),
            "action": action,
            "metadata": metadata,
        }

        self.history.append(event)

        if self.audit is None:
            return

        try:
            if hasattr(self.audit, "record"):
                self.audit.record(
                    action=action,
                    metadata=metadata,
                )
        except Exception:
            pass

    def status(self):

        return {
            "status": "available",
            "sessions": len(self.sessions),
            "history": len(self.history),
            "browser_backend": (
                type(self.browser).__name__
                if self.browser is not None
                else None
            ),
        }
