"""Who is calling? ParhLo's own auth — no third-party auth provider.

- Email OTP: 6-digit code (hash stored, 10-min expiry, 5 attempts, rate-limited), emailed via SES.
- Google OAuth: authorization-code flow; Google's ID token is verified against Google's JWKS.
- Session: HS256 JWT in an httpOnly cookie (30 days). Demo personas: X-Demo-User header.
"""

import hashlib
import hmac
import re
import secrets
import time
from functools import lru_cache
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import Header, Request, Response

from app.core.config import get_settings
from app.core.database import db
from app.core.errors import AppError

SESSION_COOKIE = "parhlo_session"
STATE_COOKIE = "parhlo_oauth_state"
SESSION_DAYS = 30
OTP_TTL_MIN = 10
OTP_MAX_ATTEMPTS = 5
OTP_MAX_PER_HOUR = 5
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


class AuthError(AppError):
    status_code = 401


def _secret() -> str:
    s = get_settings().session_secret
    if not s:
        raise AppError("SESSION_SECRET is not configured", 503)
    return s


def _secure() -> bool:
    return get_settings().public_url.startswith("https://")


# ---------- sessions ----------

def issue_session(response: Response, user_id) -> None:
    now = int(time.time())
    token = jwt.encode({"sub": str(user_id), "iat": now, "exp": now + SESSION_DAYS * 86400}, _secret(), "HS256")
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True,
                        secure=_secure(), samesite="lax", path="/")


def clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def _user_from_token(token: str) -> dict:
    try:
        claims = jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise AuthError("Session expired — please sign in again") from e
    with db() as conn:
        row = conn.execute("select * from users where id::text = %s", (claims["sub"],)).fetchone()
    if not row:
        raise AuthError("Account not found")
    return row


def current_user(
    request: Request,
    authorization: str | None = Header(None),
    x_demo_user: str | None = Header(None),
) -> dict:
    """FastAPI dependency → the users row. A signed-in account always wins over a demo header."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if token:
        try:
            return _user_from_token(token)
        except AuthError:
            if not x_demo_user:
                raise
    if x_demo_user and get_settings().allow_demo_users:
        with db() as conn:
            row = conn.execute("select * from users where id::text = %s and is_demo", (x_demo_user,)).fetchone()
        if row:
            return row
        raise AuthError("Unknown demo reader")
    raise AuthError("Sign in required")


def find_or_create_user(email: str, name: str | None = None, google_sub: str | None = None) -> dict:
    email = email.strip().lower()
    with db() as conn:
        row = None
        if google_sub:
            row = conn.execute("select * from users where google_sub = %s", (google_sub,)).fetchone()
        if not row:
            row = conn.execute("select * from users where lower(email) = %s", (email,)).fetchone()
        if row:
            if google_sub and not row.get("google_sub"):
                row = conn.execute("update users set google_sub = %s where id = %s returning *",
                                   (google_sub, row["id"])).fetchone()
            return row
        return conn.execute(
            "insert into users (email, name, google_sub) values (%s, %s, %s) returning *",
            (email, (name or "Reader").strip()[:60], google_sub),  # "Reader" = ask in onboarding
        ).fetchone()


# ---------- email OTP ----------

def _code_hash(email: str, code: str) -> str:
    return hmac.new(_secret().encode(), f"{email}:{code}".encode(), hashlib.sha256).hexdigest()


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise AppError("Please enter a valid email address", 422)
    return email


def create_otp(email: str) -> str:
    """Store a fresh code for this email and return it (caller emails it)."""
    email = normalize_email(email)
    with db() as conn:
        recent = conn.execute("select count(*) as n from otp_codes where lower(email) = %s "
                              "and created_at > now() - interval '1 hour'", (email,)).fetchone()["n"]
        if recent >= OTP_MAX_PER_HOUR:
            raise AppError("Too many codes requested. Please wait a few minutes.", 429)
        code = f"{secrets.randbelow(1_000_000):06d}"
        conn.execute("update otp_codes set used = true where lower(email) = %s and not used", (email,))
        conn.execute("insert into otp_codes (email, code_hash, expires_at) values "
                     "(%s, %s, now() + make_interval(mins => %s))", (email, _code_hash(email, code), OTP_TTL_MIN))
    return code


def verify_otp(email: str, code: str) -> dict:
    email = normalize_email(email)
    code = re.sub(r"\D", "", code or "")
    with db() as conn:
        row = conn.execute("select * from otp_codes where lower(email) = %s and not used and expires_at > now() "
                           "order by created_at desc limit 1", (email,)).fetchone()
        if not row:
            raise AuthError("That code has expired. Request a new one.")
        if row["attempts"] >= OTP_MAX_ATTEMPTS:
            conn.execute("update otp_codes set used = true where id = %s", (row["id"],))
            raise AuthError("Too many wrong attempts. Request a new code.")
        if not hmac.compare_digest(row["code_hash"], _code_hash(email, code)):
            conn.execute("update otp_codes set attempts = attempts + 1 where id = %s", (row["id"],))
            left = OTP_MAX_ATTEMPTS - row["attempts"] - 1
            raise AuthError(f"Wrong code. {left} attempt{'s' if left != 1 else ''} left.")
        conn.execute("update otp_codes set used = true where id = %s", (row["id"],))
    return find_or_create_user(email)


# ---------- Google OAuth ----------

def google_redirect_uri() -> str:
    return f"{get_settings().public_url.rstrip('/')}/api/auth/google/callback"


def google_auth_url(state: str) -> str:
    s = get_settings()
    if not s.google_client_id:
        raise AppError("Google sign-in is not configured", 503)
    return GOOGLE_AUTH + "?" + urlencode({
        "client_id": s.google_client_id, "redirect_uri": google_redirect_uri(), "response_type": "code",
        "scope": "openid email profile", "state": state, "prompt": "select_account",
    })


@lru_cache(maxsize=1)
def _google_jwks() -> jwt.PyJWKClient:
    return jwt.PyJWKClient("https://www.googleapis.com/oauth2/v3/certs", cache_keys=True)


async def google_exchange(code: str) -> dict:
    s = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(GOOGLE_TOKEN, data={
            "code": code, "client_id": s.google_client_id, "client_secret": s.google_client_secret,
            "redirect_uri": google_redirect_uri(), "grant_type": "authorization_code"})
    if r.status_code != 200:
        raise AuthError(f"Google sign-in failed ({r.json().get('error', r.status_code)})")
    id_token = r.json()["id_token"]
    key = _google_jwks().get_signing_key_from_jwt(id_token)
    claims = jwt.decode(id_token, key.key, algorithms=["RS256"], audience=s.google_client_id, leeway=30)
    if claims.get("iss") not in GOOGLE_ISSUERS or not claims.get("email_verified"):
        raise AuthError("Google account email is not verified")
    return claims
