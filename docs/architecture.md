# ParhLo Architecture (as built)

_Source of truth for the architecture diagram and the README. Last updated: 2026-10-17, after Module B._
Live: **https://parhlo-brown.vercel.app** · Repo: **https://github.com/Tehman700/ParhLo** (every push to `main` auto-deploys)

## 1. One-line summary
Every night ParhLo **collects** ~900 articles from Pakistani and global outlets, uses **Jev** to *decide* (topic, junk, importance) and **OpenAI** to *write* (summaries, layout), then prints **one finite paper per reader** (web + PDF). The paper **learns** from what the reader opens, skips and likes.

## 2. System context
```
                    ┌──────────────────────────── Vercel (one project, two services) ────────────────────────────┐
 Reader (browser) ─►│  frontend: Next.js 16 (React 19, Tailwind 4, GSAP)       backend: FastAPI (Python 3.12)     │
                    │  / landing · /sign-in · /onboarding · /paper[/date]       /api/*  (all routes under /api)    │
                    │  /paper/[date]/print · /archive · /profile · /demo        Cron: 00:00 UTC ingest,            │
                    │  /pdf/[date] → headless Chromium (puppeteer + chromium-min)       00:30 UTC (05:30 PKT) papers│
                    └───────────┬───────────────────────────────────────────────────────┬──────────────────────────┘
                                │                                                       │
        ┌───────────────────────┼─────────────────┬──────────────────┬─────────────────┼──────────────────────┐
        ▼                       ▼                 ▼                  ▼                 ▼                      ▼
  Neon Postgres +        OpenAI API          TypeSafe Jev       AWS (ap-south-1)   Google OAuth      Free data APIs
  pgvector (HNSW)        gpt-5-mini (editor,  jev-latest         SES: sign-in codes  (sign in with     Open-Meteo weather +
  users, profiles,       extraction)          Choice/Noul/Score  (+ morning email)   Google)           air quality, open.er-api
  interest_anchors,      gpt-5-nano           topic · junk ·     S3: PDFs/audio                         (PKR rates)
  articles(+vectors),    (summaries)          importance ·       Polly: audio                           RSS: Dawn, Tribune,
  editions(JSON),        text-embedding-3-    summary check      (planned)                              Geo, The News,
  events, otp_codes,     small (1536-d)                                                                 Recorder, BBC, Guardian,
  profile_snapshots                                                                                     NYT, TechCrunch, Verge,
                                                                                                        Ars, HN, Cricinfo,
                                                                                                        Google News search
```

## 3. The daily pipeline (backend/app/parhlo/)
| Stage | File | AI used | What happens |
|---|---|---|---|
| ① **Ingest** (shared) | `ingest.py`, `sources.py` | — | 24 RSS feeds + Google News search per followed name. Dawn blocks cloud IPs → automatic **Google News `site:dawn.com` fallback**. Skip known URLs, same-outlet duplicate headlines and section pages |
| ② **Embed** | `embed.py` | OpenAI `text-embedding-3-small` | Title + excerpt → 1536-d vector (pgvector, HNSW) |
| ③ **Decide** | `jev.py` | **Jev** (1 call/article, 3 questions) | **Choice** topic (17 topics) · **Noul** junk (quiz, podcast, tag page, promo…) · **Score** importance (5 levels). Fallback: embedding-similarity topics |
| ④ **Group** | `ingest.py` | pgvector | Same story from different outlets (cosine ≥ 0.84, 3 days) → one cluster → "Also in Dawn, Geo…" |
| ⑤ **Rank** (per reader) | `rank.py` | — (numpy) | score = 0.40·best interest-anchor match + 0.17·topic weight + 0.11·recency + 0.08·Jev importance + 0.05·outlet coverage + 0.08·source quality + 0.07·Pakistan/world fit + 0.05·source affinity − 0.55·disliked match. Junk (≥ 0.78) dropped, 1 article per story, MMR for variety |
| ⑥ **Select** | `rank.py` | — | **2 "Top story" core slots** (day's biggest: 0.7·importance + 0.3·coverage, importance ≥ 0.7) + personal picks + ~15% **discovery** outside the profile |
| ⑦ **Summarize** (cached, shared) | `summarize.py` | `gpt-5-nano` (minimal reasoning) | Full text via trafilatura (or excerpt) → plain 2–3 sentence summary + key points, **only from the source** |
| ⑧ **Verify** | `summarize.py` + `jev.py` | **Jev Noul** (LLM fallback) | "Does the summary contain any claim not in the source?" → ✓ only if unsupported-probability < 0.3; confidence shown on the badge |
| ⑨ **Edit** (per reader) | `editor.py` | `gpt-5-mini` (low reasoning), Pydantic-validated JSON | Lead (must be full-text), sections, plain headlines, "Why this story: Because you follow…", 3 things to remember, 3-question quiz, 2-sentence brief. Deterministic fallback layout |
| ⑩ **Morning box** | `morning.py` | — | Weather + air quality (smog alert ≥ 151 AQI) for the reader's city, USD/EUR/GBP/SAR/AED → PKR, cricket headline |
| ⑪ **Publish** | `editions.py` | — | Frozen edition JSON per reader per day → web page and PDF render the same data; archive |
| ⑫ **Learn** | `learn.py` | — | Events → topic weights (bounded, decaying), new anchors from liked/read stories, negative anchors from dislikes, source affinity, snapshot with plain-English reasons ("You engaged with 3 Cricket stories") |

## 4. Reader memory (3 layers, all in Postgres)
1. **Profile** — explicit: topic weights, followed names, city, reading time, Pakistan/world mix (`profiles`, `users`).
2. **Interest anchors** — long-term semantic memory: embeddings of chosen topics, followed names, "about me" interests, liked/read (+) and disliked (−) stories (`interest_anchors`, max 80). An article's personal score is its best match.
3. **Event log** — short-term: open, dwell (≥ 8 s visible), like, dislike, save, skip, quiz answers (`events`).
Snapshots (`profile_snapshots`) power the **Interests** page ("what changed and why").
**Onboarding signals fade:** onboarding/followed-name anchors decay ×0.988 per nightly learn (half-life ≈ 57 days, floor 0.3) so real reading takes over (Spotify-style). Swipe passes lower a topic's weight; two passes on a topic remove it from the swipe queue.

## 5. Auth (own implementation, no third-party auth provider)
- **Email OTP:** 6-digit code, only an HMAC hash stored (`otp_codes`), 10-min expiry, 5 attempts, 5/hour per email; sent via **Gmail SMTP** (app password), falling back to **AWS SES** (production access, 50k/day).
- **Google OAuth:** authorization-code flow; ID token verified against Google JWKS (`email_verified` required).
- **Session:** HS256 JWT in an **httpOnly, Secure, SameSite=Lax** cookie (30 days). **Demo readers:** `X-Demo-User` header (no sign-up), used only when no valid session cookie/Bearer is present: a real account always wins. Sign-out is a full page reload to `/`.

## 6. Data model (Neon Postgres, `backend/app/core/schema.sql`)
`users` (id, name, email, google_sub, city, lat/lon, reading_minutes, region_mix, onboarded, is_demo) · `profiles` (topics jsonb, entities, about, source_affinity) · `interest_anchors` (label, kind, weight, embedding vector(1536)) · `articles` (url, source, region, title, rss_summary, content, image, published_at, topics[], embedding vector(1536) HNSW, cluster_id, ai_summary, ai_points jsonb{points, grounded_in, check{by, confidence, ms}}, summary_verified, **importance, junk, topic_confidence, jev_checked_at**) · `editions` (user_id, edition_date, number, data jsonb, pdf_key, audio_key) · `events` · `profile_snapshots` · `otp_codes`.

## 7. API (FastAPI, all under `/api`)
Auth: `POST /auth/otp/request`, `POST /auth/otp/verify`, `GET /auth/google/start`, `GET /auth/google/callback`, `GET /auth/me`, `POST /auth/logout`
Reader: `GET /me`, `POST /onboarding`, `PATCH /me` (name, city, reading time, mix, about → re-extracted into anchors), `PUT /me/topics/{slug}` {on}, `POST /me/following`, `DELETE /me/following?name=`, `DELETE /me` (account + all data; not for demo readers), `PATCH /me/topics`, `DELETE /me/anchors/{id}`, `POST /editions/generate`, `GET /editions`, `GET /editions/{date}`, `POST /events`, `POST /learn`, `GET /morning`
Public/demo: `GET /health`, `GET /topics`, `GET /onboarding/headlines?topics=` (chosen topics first, then 3 discovery), `GET /onboarding/preview?topics=&entities=` (live front page), `GET /demo/personas`, `POST /demo/start`
Cron (Bearer `CRON_SECRET`): `GET /cron/ingest` (ingest + Jev backfill), `GET /cron/daily` (learn + print everyone's paper)
Frontend pages: `/`, `/sign-in`, `/start`, `/onboarding`, `/paper`, `/paper/{date}`, `/archive`, `/dashboard` (`/profile` redirects), `/demo`, `/privacy`, `/terms`, `/about`, `/how-it-works`; site-wide footer.
Frontend route: `GET /pdf/{date}` (Next.js route handler → Chromium → A4 PDF)

## 8. Measured numbers (production, 2026-10-17)
| Metric | Value |
|---|---|
| Ingest run | ~900 fetched, ~220 new, 10 s (incl. embeddings + Jev for all new) |
| Jev classification at scale | 1,029 articles in 30 s (12 concurrent); 139 flagged junk |
| **Summary verification** (16 real + falsified summaries) | **Jev: 94% correct, 434 ms median / 487 ms p90**; gpt-5-nano: 94%, 941 ms / 1,475 ms → same accuracy, **2–3× faster, plus calibrated confidence** |
| Paper generation (cold, 10 stories) | 19–34 s (was 117 s before reasoning-effort tuning) |
| PDF | ~320 KB, 7 s cold / 2.6 s warm |
| Sign-in | OTP email sent + verified end-to-end on production |
| Onboarding E2E (production) | 15/15 checks; preview ~1.4 s warm; first paper 22.8 s after "Create my paper" |
| Backend cold start | 12 s → **4.5 s** after moving starter-only deps (pandas, sklearn, pypdf, pillow) to an optional extra |

## 9. Repo map
```
backend/app/main.py            FastAPI app, routers, error handling
backend/app/api/{auth,parhlo}.py   HTTP routes
backend/app/parhlo/            the product: auth, ingest, sources, embed, jev, rank, summarize, editor,
                               editions, morning, profile, learn, mailer, topics
backend/app/services/llm/      OpenAI-compatible LLM client (chat, JSON, embeddings, reasoning effort)
backend/tests/                 42 tests (offline; fake LLM / fake Jev)
frontend/app/                  pages (landing, sign-in, onboarding, paper, print, archive, profile, demo, pdf route)
frontend/components/           Logo, ui, AuthCard, PaperMock, paper/{PaperView, StoryCard, EditionScreen, PrintingPress}
frontend/lib/                  api client + types, auth session, reading-signal tracker, print template
vercel.json                    services (frontend + backend), /api/* → backend, crons
docs/                          context, architecture (this file), process, decisions, research
```
