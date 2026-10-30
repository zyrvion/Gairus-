"""Keep OAuth credentials in server RAM, not in Gradio's signed client cookie."""

import copy
from http.cookies import CookieError, SimpleCookie
import secrets
import threading
import time

from itsdangerous import BadSignature, TimestampSigner

_sessions = {}
_lock = threading.Lock()


class PrivateSessionMiddleware:
    def __init__(self, app, secret_key, max_age=8 * 3600, **kwargs):
        self.app = app
        self.signer = TimestampSigner(str(secret_key))
        self.max_age = min(max_age or 8 * 3600, 8 * 3600)
        self.cookie = "session"

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        jar = SimpleCookie()
        try:
            for name, value in scope.get("headers", []):
                if name.lower() == b"cookie":
                    jar.load(value.decode("latin-1"))
        except CookieError:
            jar = SimpleCookie()
        sid = None
        if self.cookie in jar and len(jar[self.cookie].value) < 256:
            try:
                sid = self.signer.unsign(
                    jar[self.cookie].value, max_age=self.max_age
                ).decode()
            except (BadSignature, UnicodeError):
                pass
        with _lock:
            for old in list(_sessions):
                if _sessions[old][0] <= time.time():
                    _sessions.pop(old, None)
            entry = _sessions.get(sid)
            original = copy.deepcopy(entry[1]) if entry else {}
        scope["session"] = copy.deepcopy(original)

        async def wrapped_send(message):
            nonlocal sid
            if message["type"] == "http.response.start":
                current = scope["session"]
                headers = list(message.get("headers", []))
                if current != original:
                    with _lock:
                        # Rotate after OAuth login; never reuse a pre-login ID.
                        if "oauth_info" in current and "oauth_info" not in original:
                            _sessions.pop(sid, None)
                            sid = None
                        if current:
                            sid = sid or secrets.token_urlsafe(32)
                            while len(_sessions) >= 2048:
                                _sessions.pop(next(iter(_sessions)))
                            _sessions[sid] = (
                                time.time() + self.max_age, copy.deepcopy(current)
                            )
                            value = self.signer.sign(sid.encode()).decode()
                            cookie = (
                                f"{self.cookie}={value}; Path=/; Max-Age={self.max_age}; "
                                "HttpOnly; Secure; SameSite=Lax"
                            )
                        else:
                            _sessions.pop(sid, None)
                            cookie = (
                                f"{self.cookie}=; Path=/; Max-Age=0; "
                                "HttpOnly; Secure; SameSite=Lax"
                            )
                    headers.append((b"set-cookie", cookie.encode("latin-1")))
                if not scope.get("path", "").startswith(("/assets/", "/static/")):
                    headers = [(k, v) for k, v in headers if k.lower() != b"cache-control"]
                    headers.append((b"cache-control", b"no-store"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, wrapped_send)


def install():
    """Replace only Gradio's OAuth session middleware, failing closed on drift."""
    import gradio.routes
    from starlette.middleware import Middleware
    from starlette.middleware.sessions import SessionMiddleware

    original = gradio.routes.attach_oauth
    if getattr(original, "_gairus_private_sessions", False):
        return

    def attach(app):
        original(app)
        found = 0
        for index, middleware in enumerate(app.user_middleware):
            if middleware.cls is SessionMiddleware:
                app.user_middleware[index] = Middleware(
                    PrivateSessionMiddleware, **middleware.kwargs
                )
                found += 1
        if found != 1:
            raise RuntimeError("OAuth session protection could not be installed.")

    attach._gairus_private_sessions = True
    gradio.routes.attach_oauth = attach
