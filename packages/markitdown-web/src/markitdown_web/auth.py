import base64
import hashlib
import hmac
import secrets
import time

from fastapi import HTTPException, Request, Response, status

SESSION_COOKIE = "mid_session"
CSRF_COOKIE = "mid_csrf"
CSRF_HEADER = "x-csrf-token"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 12


class AuthManager:
    def __init__(self, secret_key: str, password: str) -> None:
        self._secret = secret_key.encode("utf-8")
        self._password = password

    def verify_password(self, password: str) -> bool:
        return hmac.compare_digest(password, self._password)

    def sign_in(self, response: Response, *, secure_cookie: bool) -> None:
        issued_at = str(int(time.time()))
        nonce = secrets.token_urlsafe(18)
        csrf = secrets.token_urlsafe(24)
        payload = f"{issued_at}:{nonce}:{csrf}"
        signature = self._sign(payload)
        token = base64.urlsafe_b64encode(f"{payload}:{signature}".encode("utf-8")).decode("ascii")
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=SESSION_MAX_AGE_SECONDS,
            httponly=True,
            secure=secure_cookie,
            samesite="lax",
        )
        response.set_cookie(
            CSRF_COOKIE,
            csrf,
            max_age=SESSION_MAX_AGE_SECONDS,
            httponly=False,
            secure=secure_cookie,
            samesite="lax",
        )

    def sign_out(self, response: Response) -> None:
        response.delete_cookie(SESSION_COOKIE)
        response.delete_cookie(CSRF_COOKIE)

    def require_session(self, request: Request) -> str:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
        try:
            decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
            issued_at, nonce, csrf, signature = decoded.split(":", 3)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.") from exc
        payload = f"{issued_at}:{nonce}:{csrf}"
        if not hmac.compare_digest(signature, self._sign(payload)):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")
        if int(issued_at) + SESSION_MAX_AGE_SECONDS < int(time.time()):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")
        return csrf

    def require_csrf(self, request: Request) -> None:
        expected = self.require_session(request)
        cookie_token = request.cookies.get(CSRF_COOKIE)
        header_token = request.headers.get(CSRF_HEADER)
        if not cookie_token or not header_token:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token required.")
        if not hmac.compare_digest(expected, cookie_token) or not hmac.compare_digest(expected, header_token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token.")

    def _sign(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
