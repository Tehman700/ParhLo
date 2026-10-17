import secrets

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.parhlo import auth
from app.parhlo.mailer import otp_email, send_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


class OtpRequest(BaseModel):
    email: str


class OtpVerify(BaseModel):
    email: str
    code: str


def _public(user: dict) -> dict:
    return {"id": str(user["id"]), "name": user["name"], "email": user.get("email"),
            "onboarded": user["onboarded"], "is_demo": user["is_demo"]}


@router.post("/otp/request")
async def otp_request(body: OtpRequest):
    code = auth.create_otp(body.email)
    subject, html, text = otp_email(code)
    await send_email(auth.normalize_email(body.email), subject, html, text)
    return {"sent": True, "expires_in_minutes": auth.OTP_TTL_MIN}


@router.post("/otp/verify")
def otp_verify(body: OtpVerify, response: Response):
    user = auth.verify_otp(body.email, body.code)
    auth.issue_session(response, user["id"])
    return {"user": _public(user)}


@router.get("/google/start")
def google_start():
    state = secrets.token_urlsafe(24)
    res = RedirectResponse(auth.google_auth_url(state), status_code=302)
    res.set_cookie(auth.STATE_COOKIE, state, max_age=600, httponly=True, secure=auth._secure(), samesite="lax", path="/")
    return res


@router.get("/google/callback")
async def google_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    base = get_settings().public_url.rstrip("/")
    if error or not code:
        return RedirectResponse(f"{base}/sign-in?error=google_cancelled", status_code=302)
    if not state or state != request.cookies.get(auth.STATE_COOKIE):
        return RedirectResponse(f"{base}/sign-in?error=google_state", status_code=302)
    try:
        claims = await auth.google_exchange(code)
    except Exception:
        return RedirectResponse(f"{base}/sign-in?error=google_failed", status_code=302)
    user = auth.find_or_create_user(claims["email"], claims.get("given_name") or claims.get("name"), claims["sub"])
    res = RedirectResponse(f"{base}/start", status_code=302)
    res.delete_cookie(auth.STATE_COOKIE, path="/")
    auth.issue_session(res, user["id"])
    return res


@router.get("/me")
def me(user=Depends(auth.current_user)):
    return {"user": _public(user)}


@router.post("/logout")
def logout(response: Response):
    auth.clear_session(response)
    return {"signed_out": True}
