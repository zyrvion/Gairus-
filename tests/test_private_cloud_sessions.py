import asyncio
import importlib.util
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "deploy" / "huggingface"
spec = importlib.util.spec_from_file_location("gairus_private_sessions", SOURCE / "private_sessions.py")
sessions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sessions)


def run_request(middleware, path, cookie=""):
    messages = []
    scope = {
        "type": "http", "path": path,
        "headers": [(b"cookie", cookie.encode())] if cookie else [],
    }

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        messages.append(message)

    asyncio.run(middleware(scope, receive, send))
    return scope, messages


async def app(scope, receive, send):
    if scope["path"] == "/login":
        scope["session"]["oauth_info"] = {"access_token": "synthetic-private-token"}
    if scope["path"] == "/logout":
        scope["session"].clear()
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def test_cookie_contains_no_token_and_session_survives_request():
    sessions._sessions.clear()
    middleware = sessions.PrivateSessionMiddleware(app, secret_key="synthetic-secret")
    _, messages = run_request(middleware, "/login")
    headers = dict(messages[0]["headers"])
    cookie = headers[b"set-cookie"].decode()
    assert "synthetic-private-token" not in cookie
    assert "access_token" not in cookie
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=Lax" in cookie
    scope, _ = run_request(middleware, "/private", cookie.split(";")[0])
    assert scope["session"]["oauth_info"]["access_token"] == "synthetic-private-token"
    assert headers[b"cache-control"] == b"no-store"


def test_logout_invalidates_server_session_and_old_cookie():
    sessions._sessions.clear()
    middleware = sessions.PrivateSessionMiddleware(app, secret_key="synthetic-secret")
    _, messages = run_request(middleware, "/login")
    cookie = dict(messages[0]["headers"])[b"set-cookie"].decode().split(";")[0]
    run_request(middleware, "/logout", cookie)
    scope, _ = run_request(middleware, "/private", cookie)
    assert scope["session"] == {}


def test_tampered_or_unknown_cookie_does_not_authenticate():
    middleware = sessions.PrivateSessionMiddleware(app, secret_key="synthetic-secret")
    scope, _ = run_request(middleware, "/private", "session=not-a-signed-session")
    assert scope["session"] == {}
    valid_but_unknown = middleware.signer.sign(b"unknown").decode()
    scope, _ = run_request(middleware, "/private", "session=" + valid_but_unknown)
    assert scope["session"] == {}


def test_worker_restart_requires_login_not_durable_token():
    sessions._sessions.clear()
    middleware = sessions.PrivateSessionMiddleware(app, secret_key="synthetic-secret")
    _, messages = run_request(middleware, "/login")
    cookie = dict(messages[0]["headers"])[b"set-cookie"].decode().split(";")[0]
    sessions._sessions.clear()
    scope, _ = run_request(middleware, "/private", cookie)
    assert scope["session"] == {}
