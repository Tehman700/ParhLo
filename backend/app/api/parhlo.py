"""ParhLo HTTP API. Everything under /api (Vercel routes /api/* to this service)."""

import datetime as dt

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import db
from app.core.errors import AppError, NotFoundError
from app.parhlo import editions, friends, learn, profile
from app.parhlo.auth import AuthError, clear_session, current_user
from app.parhlo.ingest import ingest, jev_backfill
from app.parhlo.morning import morning_box
from app.parhlo.topics import TOPICS

router = APIRouter(prefix="/api", tags=["parhlo"])


# ---------- public ----------

@router.get("/health")
def health():
    s = get_settings()
    return {"status": "ok", "app": s.app_name, "llm": s.llm_configured, "db": bool(s.database_url)}


@router.get("/topics")
def topics():
    return [{"slug": k, **v} for k, v in TOPICS.items()]


@router.get("/onboarding/headlines")
def onboarding_headlines(topics: str = ""):
    """Headlines to swipe on; pass ?topics=ai,cricket for chosen topics first + 3 discovery."""
    return profile.onboarding_headlines([t for t in topics.split(",") if t])


@router.get("/onboarding/preview")
def onboarding_preview(topics: str = "", entities: str = ""):
    """Live front-page preview while the reader picks topics."""
    return profile.onboarding_preview([t for t in topics.split(",") if t], [e for e in entities.split(",") if e])


# ---------- reader ----------

@router.get("/me")
def me(user=Depends(current_user)):
    return profile.get_profile(user["id"])


@router.post("/onboarding")
async def onboarding(data: profile.OnboardingIn, user=Depends(current_user)):
    return await profile.onboard(user, data)


class TopicWeights(BaseModel):
    topics: dict[str, float]


@router.patch("/me/topics")
def update_topics(body: TopicWeights, user=Depends(current_user)):
    from psycopg.types.json import Jsonb

    clean = {k: max(0.0, min(1.0, v)) for k, v in body.topics.items() if k in TOPICS}
    with db() as conn:
        conn.execute("update profiles set topics = topics || %s, updated_at=now() where user_id=%s",
                     (Jsonb(clean), user["id"]))
    return profile.get_profile(user["id"])


@router.patch("/me")
async def update_me(body: profile.ProfileUpdate, user=Depends(current_user)):
    return await profile.update_profile(user, body)


class TopicToggle(BaseModel):
    on: bool


@router.put("/me/topics/{slug}")
async def toggle_topic(slug: str, body: TopicToggle, user=Depends(current_user)):
    return await profile.set_topic(user, slug, body.on)


class FollowIn(BaseModel):
    name: str


@router.post("/me/following")
async def follow(body: FollowIn, user=Depends(current_user)):
    return await profile.follow(user, body.name)


@router.delete("/me/following")
def unfollow(name: str, user=Depends(current_user)):
    return profile.unfollow(user, name)


@router.delete("/me")
def delete_me(response: Response, user=Depends(current_user)):
    """Delete the account and all its data, and sign out."""
    if user.get("is_demo"):
        raise AppError("Demo readers can't be deleted. Use Exit demo instead.", 400)
    profile.delete_account(user)
    clear_session(response)
    return {"deleted": True}


@router.delete("/me/anchors/{anchor_id}")
def delete_anchor(anchor_id: int, user=Depends(current_user)):
    with db() as conn:
        conn.execute("delete from interest_anchors where id=%s and user_id=%s", (anchor_id, user["id"]))
    return {"deleted": anchor_id}


class GenerateIn(BaseModel):
    date: dt.date | None = None
    force: bool = False


@router.post("/editions/generate")
async def generate(body: GenerateIn, user=Depends(current_user)):
    if not user.get("onboarded"):
        raise AppError("Finish onboarding first", 409)
    return _with_state(user, await editions.generate_edition(user, body.date, body.force))


def _with_state(user: dict, ed: dict) -> dict:
    """Attach the reader's likes/dislikes/saves for this paper's stories."""
    return {**ed, "state": learn.reader_state(user["id"], [s["id"] for s in ed.get("stories", [])])}


@router.get("/editions")
def archive(user=Depends(current_user)):
    return editions.list_editions(user["id"])


@router.get("/editions/{edition_date}")
def edition(edition_date: dt.date, user=Depends(current_user)):
    return _with_state(user, editions.get_edition(user["id"], edition_date))


@router.post("/events")
def events(body: list[learn.EventIn], user=Depends(current_user)):
    return learn.record_events(user, body)


@router.get("/me/saved")
def saved(user=Depends(current_user)):
    return learn.saved_stories(user["id"])


# ---------- friends and notifications ----------

@router.get("/me/friends")
def my_friends(user=Depends(current_user)):
    return friends.list_friends(user)


@router.delete("/me/friends/{friend_id}")
def unfriend(friend_id: str, user=Depends(current_user)):
    return friends.remove_friend(user, friend_id)


@router.get("/invites/{code}")
def invite(code: str):
    return friends.invite_info(code)


@router.post("/invites/{code}/accept")
def accept_invite(code: str, user=Depends(current_user)):
    return friends.accept_invite(user, code)


@router.get("/notifications")
def notifications(user=Depends(current_user)):
    return friends.list_notifications(user["id"])


@router.post("/notifications/read")
def notifications_read(user=Depends(current_user)):
    return friends.mark_read(user["id"])


@router.post("/learn")
def consolidate(user=Depends(current_user)):
    return learn.consolidate(user)


@router.get("/morning")
async def morning(user=Depends(current_user)):
    return await morning_box(user["city"], user["lat"], user["lon"])


# ---------- demo personas (two-persona comparison) ----------

@router.get("/demo/personas")
def personas():
    """Seeded, onboarded demo readers (for visitors trying ParhLo without an account)."""
    with db() as conn:
        return conn.execute(
            """select u.id, u.name, u.city, p.about,
                      (select array_agg(k order by (p.topics->>k)::float desc) from jsonb_object_keys(p.topics) k
                        where (p.topics->>k)::float >= 0.5) as top_topics
               from users u join profiles p on p.user_id = u.id
               where u.is_demo and u.onboarded and u.name <> 'Guest' order by u.created_at limit 6""").fetchall()


@router.post("/demo/start")
def demo_start():
    """Instant guest reader without sign-up (then onboarding as usual)."""
    if not get_settings().allow_demo_users:
        raise AuthError("Demo readers are disabled")
    with db() as conn:
        row = conn.execute("insert into users (name, is_demo) values ('Guest', true) returning id").fetchone()
    return {"id": str(row["id"])}


# ---------- cron (Vercel Cron sends Authorization: Bearer $CRON_SECRET) ----------

def _cron_auth(authorization: str | None = Header(None)):
    secret = get_settings().cron_secret
    if not secret or authorization != f"Bearer {secret}":
        raise AuthError("Bad cron secret")


@router.get("/cron/ingest", dependencies=[Depends(_cron_auth)])
async def cron_ingest():
    with db() as conn:
        rows = conn.execute("select entities from profiles").fetchall()
    queries = list(dict.fromkeys(e for r in rows for e in (r["entities"] or [])))[:12]
    stats = await ingest(extra_queries=queries)
    return {**stats, **(await jev_backfill())}


@router.get("/cron/daily", dependencies=[Depends(_cron_auth)])
async def cron_daily():
    """05:30 PKT: learn from yesterday, then print everyone's paper."""
    with db() as conn:
        users = conn.execute("select * from users where onboarded").fetchall()
    done, failed = 0, []
    for u in users:
        try:
            learn.consolidate(u)
            await editions.generate_edition(u)
            done += 1
        except Exception as e:  # one reader's failure must not block the others
            failed.append({"user": str(u["id"]), "error": str(e)[:200]})
    if not users:
        raise NotFoundError("No onboarded readers yet")
    return {"generated": done, "failed": failed}
