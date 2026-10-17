"""Who is calling? A Clerk session JWT (Google / email-OTP sign-in) or, for demo personas, X-Demo-User.

The frontend sends `Authorization: Bearer <await getToken()>`. We verify it against Clerk's JWKS
(issuer comes from the token itself and must be a Clerk domain), then map the Clerk user to our users row.
"""

import base64
from functools import lru_cache

import jwt
from fastapi import Header

from app.core.config import get_settings
from app.core.database import db
from app.core.errors import AppError


class AuthError(AppError):
    status_code = 401


@lru_cache(maxsize=4)
def _jwks(issuer: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json", cache_keys=True)


@lru_cache(maxsize=1)
def trusted_issuers() -> frozenset[str]:
    """Our Clerk instance's issuer, decoded from the publishable key (pk_test_<base64("domain$")>)."""
    s = get_settings()
    issuers = set(s.clerk_issuers)
    pk = s.next_public_clerk_publishable_key
    if pk.count("_") >= 2:
        encoded = pk.split("_", 2)[2]
        domain = base64.b64decode(encoded + "=" * (-len(encoded) % 4)).decode().rstrip("$")
        issuers.add(f"https://{domain}")
    return frozenset(issuers)


def verify_clerk_token(token: str) -> dict:
    try:
        issuer = jwt.decode(token, options={"verify_signature": False}).get("iss", "")
        if issuer not in trusted_issuers():
            raise AuthError("Untrusted token issuer")
        key = _jwks(issuer).get_signing_key_from_jwt(token)
        return jwt.decode(token, key.key, algorithms=["RS256"], issuer=issuer, leeway=30,
                          options={"verify_aud": False})
    except AuthError:
        raise
    except Exception as e:
        raise AuthError(f"Invalid session: {type(e).__name__}") from e


def current_user(
    authorization: str | None = Header(None),
    x_demo_user: str | None = Header(None),
) -> dict:
    """FastAPI dependency → the users row (creates it on first sign-in)."""
    if x_demo_user and get_settings().allow_demo_users:
        with db() as conn:
            row = conn.execute("select * from users where id::text = %s and is_demo", (x_demo_user,)).fetchone()
        if row:
            return row
        raise AuthError("Unknown demo user")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Sign in required")
    claims = verify_clerk_token(authorization.split(" ", 1)[1])
    clerk_id = claims["sub"]
    with db() as conn:
        row = conn.execute("select * from users where clerk_id = %s", (clerk_id,)).fetchone()
        if not row:
            row = conn.execute(
                "insert into users (clerk_id, name, email) values (%s, %s, %s) returning *",
                (clerk_id, claims.get("name") or claims.get("first_name") or "Reader", claims.get("email")),
            ).fetchone()
    return row
