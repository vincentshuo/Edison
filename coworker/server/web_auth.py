"""Single-owner browser login for the self-hosted Edison instance.

Caddy asks ``/v1/web-auth/check`` before serving a page or proxying an API call.
The desktop sidecar does not enable this module.
"""

from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict, deque
from html import escape
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

_COOKIE = "edison_session"
_SESSION_SECONDS = 12 * 60 * 60
_ATTEMPT_SECONDS = 60
_MAX_ATTEMPTS = 5
_MAX_USERNAME_LENGTH = 128
_MAX_PASSWORD_LENGTH = 1024


class WebAuth:
    def __init__(self, username: str, password_hash: str) -> None:
        self.username = username
        self.password_hash = password_hash.encode()
        self.sessions: dict[str, float] = {}
        self.failed: dict[str, deque[float]] = defaultdict(deque)

    @classmethod
    def from_environment(cls) -> WebAuth | None:
        if os.environ.get("EDISON_WEB_LOGIN") != "1":
            return None
        username = os.environ["EDISON_WEB_USERNAME"]
        password_hash = Path(os.environ["EDISON_WEB_PASSWORD_HASH_FILE"]).read_text().strip()
        if not username or not password_hash:
            raise ValueError("Web login requires a username and password hash")
        return cls(username, password_hash)

    def valid(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        expires = self.sessions.get(session_id, 0)
        if expires <= time.monotonic():
            self.sessions.pop(session_id, None)
            return False
        return True

    def password_matches(self, username: str, password: str) -> bool:
        import bcrypt

        # Always check the hash, including for an unknown username.
        password_ok = bcrypt.checkpw(password.encode(), self.password_hash)
        return password_ok and secrets.compare_digest(username, self.username)

    def attempt_allowed(self, address: str) -> bool:
        now = time.monotonic()
        attempts = self.failed[address]
        while attempts and now - attempts[0] >= _ATTEMPT_SECONDS:
            attempts.popleft()
        return len(attempts) < _MAX_ATTEMPTS

    def record_failure(self, address: str) -> None:
        self.failed[address].append(time.monotonic())

    def issue(self) -> str:
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = time.monotonic() + _SESSION_SECONDS
        return session_id


def _page(error: str = "", username: str = "") -> HTMLResponse:
    safe_error = escape(error)
    safe_username = escape(username[:_MAX_USERNAME_LENGTH], quote=True)
    message = f'<p class="error" id="form-error" role="alert" aria-live="assertive">{safe_error}</p>' if error else ""
    described_by = ' aria-describedby="form-error"' if error else ""
    username_focus = " autofocus" if not username else ""
    password_focus = " autofocus" if username else ""
    page = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>登录 Edison</title><style>
:root {{ color-scheme: light dark; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
* {{ box-sizing:border-box; }}
html {{ min-height:100%; background:#f5f4f1; }}
body {{ min-height:100vh; min-height:100svh; margin:0; display:grid; place-items:center; padding:16px; background:#f5f4f1; color:#242424; line-height:1.4; }}
main {{ width:min(400px,100%); padding:36px; background:white; border-radius:16px;
  box-shadow:0 20px 48px rgba(32,30,26,.12); }}
h1 {{ margin:0 0 8px; font-size:27px; font-weight:700; letter-spacing:-.025em; line-height:1.15; }}
p {{ color:#656565; margin:0 0 28px; line-height:1.5; }}
label {{ display:block; margin:20px 0 8px; font-size:14px; font-weight:600; }}
input {{ display:block; width:100%; height:46px; padding:0 12px; border:1px solid #b8b8b8;
  border-radius:9px; font:inherit; background:transparent; color:inherit; caret-color:#6262a9; transition:border-color 140ms ease, box-shadow 140ms ease; }}
input:hover {{ border-color:#858585; }}
input:focus-visible {{ border-color:#6262a9; outline:2px solid #6262a9; outline-offset:2px; box-shadow:0 0 0 3px rgba(98,98,169,.12); }}
button {{ width:100%; height:46px; margin-top:28px; border:0; border-radius:9px; background:#25252a;
  color:white; font:inherit; font-weight:650; cursor:pointer; transition:background-color 140ms ease, transform 140ms ease, box-shadow 140ms ease; }}
button:hover {{ background:#3a3a42; box-shadow:0 6px 14px rgba(37,37,42,.16); }}
button:active {{ transform:translateY(1px); box-shadow:none; }}
button:focus-visible {{ outline:2px solid #6262a9; outline-offset:3px; }}
.error {{ margin:18px 0 0; padding:10px 12px; border:1px solid #efcaca; border-radius:9px; color:#9f2929; background:#fff6f6; font-size:14px; line-height:1.45; }}
::selection {{ background:#deddf8; color:#24242a; }}
@media (max-width:480px) {{ main {{ padding:28px 24px; }} }}
@media (prefers-reduced-motion:reduce) {{ input, button {{ transition:none; }} }}
@media (forced-colors:active) {{ main {{ border:1px solid CanvasText; box-shadow:none; }} input {{ border:1px solid CanvasText; }} button {{ border:1px solid ButtonText; }} }}
@media (prefers-color-scheme:dark) {{ html, body {{ background:#202025; }} body {{ color:#eee; }}
 main {{ background:#29292f; box-shadow:0 20px 48px rgba(0,0,0,.32); }} p {{ color:#aaa; }}
 input {{ border-color:#777; caret-color:#9898ee; }} input:hover {{ border-color:#a2a2aa; }}
 input:focus-visible, button:focus-visible {{ border-color:#9898ee; outline-color:#9898ee; box-shadow:0 0 0 3px rgba(152,152,238,.16); }}
 button {{ background:#e7e7ea; color:#222; }} button:hover {{ background:#fff; box-shadow:0 6px 14px rgba(0,0,0,.24); }}
 .error {{ border-color:#754040; color:#ffb0b0; background:#382426; }} ::selection {{ background:#4b4a74; color:#fff; }} }}
</style></head><body><main><h1>Edison</h1><p>登录后继续使用你的工作空间。</p>
<form method="post" action="/v1/web-auth/login"{described_by}>
<label for="username">用户名</label><input id="username" name="username" type="text" autocomplete="username" autocapitalize="none" autocorrect="off" spellcheck="false" maxlength="{_MAX_USERNAME_LENGTH}" value="{safe_username}" required{username_focus}>
<label for="password">密码</label><input id="password" name="password" type="password" autocomplete="current-password" maxlength="{_MAX_PASSWORD_LENGTH}" required{password_focus}>
{message}<button type="submit">登录</button></form></main></body></html>"""
    return HTMLResponse(page, headers={"Cache-Control": "no-store", "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'"})


def attach_web_auth(app: FastAPI, auth: WebAuth) -> None:
    @app.get("/login")
    def login_page(request: Request) -> Response:
        if auth.valid(request.cookies.get(_COOKIE)):
            return RedirectResponse("/", status_code=303)
        return _page()

    @app.post("/v1/web-auth/login")
    async def login(request: Request) -> Response:
        # A foreign site cannot submit credentials or set a session through this endpoint.
        origin = request.headers.get("origin")
        # Caddy rewrites the same-origin browser Origin to localhost for the
        # existing sidecar API origin gate. A foreign Origin is left untouched.
        if origin and origin not in {f"https://{request.headers.get('host')}", "http://localhost"}:
            return JSONResponse({"error": "invalid origin"}, status_code=403)
        if request.headers.get("content-type", "").split(";", 1)[0] != "application/x-www-form-urlencoded":
            return JSONResponse({"error": "invalid form"}, status_code=415)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 4096:
                return _page("登录请求过大，请重试。")
        try:
            form = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        except UnicodeDecodeError:
            return JSONResponse({"error": "invalid form"}, status_code=400)
        usernames = form.get("username", [])
        passwords = form.get("password", [])
        username = usernames[0] if len(usernames) == 1 else ""
        password = passwords[0] if len(passwords) == 1 else ""
        address = request.client.host if request.client else "unknown"
        if not auth.attempt_allowed(address):
            return _page("尝试次数过多，请一分钟后重试。", username)
        if (
            len(usernames) != 1
            or len(passwords) != 1
            or len(username) > _MAX_USERNAME_LENGTH
            or len(password) > _MAX_PASSWORD_LENGTH
        ):
            auth.record_failure(address)
            return _page("登录信息格式无效，请重试。", username[:_MAX_USERNAME_LENGTH])
        if not auth.password_matches(username, password):
            auth.record_failure(address)
            return _page("用户名或密码不正确，请重试。", username)
        auth.failed.pop(address, None)
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(_COOKIE, auth.issue(), max_age=_SESSION_SECONDS, secure=True, httponly=True, samesite="strict", path="/")
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/v1/web-auth/check")
    def check(request: Request) -> Response:
        if auth.valid(request.cookies.get(_COOKIE)):
            return Response(status_code=204)
        original_path = request.headers.get("x-forwarded-uri", "/")
        if original_path.startswith(("/v1/", "/ws/")):
            return JSONResponse({"error": "login required"}, status_code=401)
        return RedirectResponse("/login", status_code=303)

    @app.post("/v1/web-auth/logout")
    def logout(request: Request) -> Response:
        session_id = request.cookies.get(_COOKIE)
        if session_id:
            auth.sessions.pop(session_id, None)
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(_COOKIE, path="/")
        return response
