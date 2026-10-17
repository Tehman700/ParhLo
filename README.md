# ParhLo

[![CI](https://github.com/Tehman700/ParhLo/actions/workflows/ci.yml/badge.svg)](https://github.com/Tehman700/ParhLo/actions/workflows/ci.yml)
[![Smoke test (production)](https://github.com/Tehman700/ParhLo/actions/workflows/smoke.yml/badge.svg)](https://github.com/Tehman700/ParhLo/actions/workflows/smoke.yml)

**Your news, in one paper.** ParhLo reads the news from trusted outlets in Pakistan and around the world every night, picks what matters to you, and gives you one short, finished paper every morning: on the web, as a newspaper-style PDF, and in your inbox. It learns from what you read, explains every choice, and updates the moment you change your interests.

**Live:** https://parhlo-brown.vercel.app · **Try without an account:** [/demo](https://parhlo-brown.vercel.app/demo) (sample readers Ayesha and Omar)

> Built for NaSCon'26 · Problem statement: "Build a personal morning paper" (Eynvision).

---

## What it does

| The brief asked for | ParhLo |
|---|---|
| **Onboarding** | Sign in with Google or an emailed code. Pick topics with a **live front-page preview**, swipe a few real headlines (adaptive: topics you pass on stop appearing), follow people/teams/companies, or describe yourself in your own words. The first paper is on screen **~2.7 s** after "Create my paper". |
| **A daily newspaper-style PDF** | Every paper downloads as an A4 newspaper (masthead, lead story, columns, "3 things to remember"), rendered by headless Chromium. |
| **Web edition + archive** | A finite paper sized to your reading time (5–20 min): your stories, the day's **two biggest stories for everyone**, and ~15% **"something new"** so it doesn't narrow. Morning box (weather, air quality/smog alert, PKR rates, cricket). Every past paper stays in **Past papers**. |
| **Learns from usage** | Opens, reading time, likes, dislikes, saves, skips and questions update your interests every night; your dashboard shows each change and why ("You engaged with 2 Cricket stories"). Onboarding picks fade slowly so real reading takes over. |
| **Room to explore** | Discovery slots, **Ask your paper**, **search**, friends' picks, and every story links to the original. |

**Beyond the brief**
- **Trust:** every summary is written from the original article and **checked against it by Jev** (✓ with confidence); excerpt-only stories say so. Every story says **why it's in your paper**.
- **Instant updates:** switch a topic on → **new paper on screen in ~2.5 s**, polished by AI in the background ~15 s later.
- **Ask your paper:** questions answered only from your paper, with sources; "Ask about this story" on every card.
- **Search:** by meaning ("fuel prices" finds "petrol cut by Rs3.93") and by name; your paper first; Follow / Save / Ask from results; opens the original.
- **Morning email** at ~6 AM (newspaper layout, one-click unsubscribe), **friends** (invite links, notifications, opt-in "Learn from friends"), **saved stories**, **dashboard** to edit everything ParhLo remembers, **Help & contact**, privacy policy, account deletion.

## Architecture

```
                    ┌──────────────── Vercel (one project, two services) ─────────────────┐
 Browser ──HTTPS──► │  Next.js 16 (React 19, Tailwind 4, GSAP)    /api/* ─► FastAPI (Python 3.12) │
                    │  paper · dashboard · search · Ask · PDF route (Chromium)                │
                    └──────────────────────────────┬───────────────────────────────────────────┘
                                                   │
   Vercel Cron ─► /cron/ingest (00:00 UTC) ──► 28 RSS feeds + Google News ─► embed ─► Jev (topic, junk,
                                               importance) ─► cluster ─► story bank (summaries pre-written)
   Vercel Cron ─► /cron/daily  (00:30 UTC) ──► learn (events → interests) ─► print every paper ─► email queue
   Vercel Cron ─► /cron/email  (01:00 UTC) ──► drain email queue (retries)
                                                   │
        Neon Postgres + pgvector ◄─────────────────┤  users · profiles · interest_anchors (vectors) · articles
                                                   │  (HNSW) · editions (frozen JSON) · events · article_state
        OpenAI  gpt-5-mini / gpt-5-nano / embeddings · TypeSafe Jev · AWS SES/S3 · Gmail SMTP · Open-Meteo
        n8n Cloud ◄── signed "interests changed" event ──► check ─► reprint + polish (when the page is closed)
```

**How a paper is made.** Ingest → embed (text-embedding-3-small) → **Jev** classifies topic, junk and importance (434 ms median, calibrated) → cluster duplicates → **rank in Postgres** (pgvector: each story vs the reader's interest anchors, + topic weight, recency, importance, outlet coverage, source quality, region mix) → select (personal picks with MMR variety, 2 shared Top stories, discovery; every switched-on topic gets a story, switched-off topics never appear) → summaries (full text via trafilatura, gpt-5-nano, Jev check) → AI editor (gpt-5-mini: headlines, why-lines, sections, note, 3 things, quiz) → frozen edition JSON → web, PDF, email.

**Instant reprints.** A change stamps the reader and sends a signed event to **n8n**. The page waits 0.9 s for more changes, then asks for a **fast print** (no AI in the critical path: SQL ranking ~0.2 s, pre-written summaries or excerpts, simple layout) and swaps it in from the response; then an **AI polish** upgrades it silently. n8n (Webhook → Wait → check → reprint + polish) is the guarantee when the page is closed.

**Morning email** uses a **job queue in Postgres** (outbox + `FOR UPDATE SKIP LOCKED`, retries, idempotent per reader and paper): serverless-friendly, no Redis or Celery.

More: [docs/architecture.md](docs/architecture.md) · decisions and trade-offs: [docs/decisions.md](docs/decisions.md)

## Measured on production

| | |
|---|---|
| Interest change → new paper on screen | **2.4–2.9 s** (server build ~0.2 s; was ~30 s) |
| First paper after onboarding | **2.7 s** (was 18–30 s); AI polish lands ~20 s later |
| Ranking in Postgres | 142 ms in the database (was ~9.5 s pulling 1,300 embeddings) |
| Jev summary check vs gpt-5-nano | same accuracy (94%), **434 ms vs 941 ms** median, plus confidence |
| Ask your paper | Jev routes the question in ~0.4 s; answer in 3–6 s with sources |
| Search | results as you type in ~1.5 s |
| Tests | 66 backend tests + end-to-end browser suites on production (full flow 31/31, speed 11/11, search & help 21/21, email 18/18, demo 23/23) |

## Tech stack
Next.js 16 · React 19 · Tailwind CSS 4 · GSAP · FastAPI · Python 3.12 · uv · Neon Postgres + pgvector · OpenAI (gpt-5-mini, gpt-5-nano, text-embedding-3-small) · TypeSafe Jev · n8n Cloud · AWS (SES, S3) · Gmail SMTP · Vercel (Services, Cron) · puppeteer-core + @sparticuz/chromium · GitHub Actions

## Repo layout
| Path | What |
|---|---|
| `backend/app/parhlo/` | The product: `ingest`, `sources`, `jev`, `rank`, `summarize`, `editor`, `editions`, `refresh` (instant reprints), `learn`, `profile`, `friends`, `digest` (email queue), `ask`, `search`, `support`, `auth`, `mailer`, `morning` |
| `backend/app/api/` | HTTP routes (`auth.py`, `parhlo.py`), all under `/api` |
| `backend/app/core/schema.sql` | Database schema (idempotent, applied on startup) |
| `backend/tests/` | 66 tests (Jev, ranking, friends, email, search helpers, personas, refresh tokens…) |
| `frontend/app/` | Pages: landing, sign-in, onboarding, paper, archive, dashboard, demo, invite, help, privacy, terms, about, how-it-works, jev, PDF route |
| `frontend/components/` | Paper, story card, Ask widget, search, dashboard panels, notifications, tour |
| `n8n/paper-refresh.workflow.json` | n8n workflow (import into n8n, activate, put its webhook URL in `N8N_WEBHOOK_URL`) |
| `.github/workflows/` | CI (lint, tests, type check, build) and the production smoke test |
| `docs/` | Context, architecture, decisions, research. Start at [docs/README.md](docs/README.md) |

## Run locally
Needs Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 24 + pnpm, and a Postgres database with **pgvector** (e.g. a free Neon project).

```bash
cp .env.example .env            # fill in DATABASE_URL, LLM_API_KEY, SESSION_SECRET (others optional)

cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000     # creates the schema on startup; API docs at /docs

cd ../frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
pnpm install && pnpm dev                              # http://localhost:3000
```

Fetch news once (the cron does this daily in production):
```bash
cd backend && uv run python -c "import asyncio; from app.parhlo.ingest import ingest; print(asyncio.run(ingest()))"
```

## Tests and CI
```bash
cd backend && uv run --extra starter pytest -q        # 66 tests; no API keys needed (Jev, LLM, DB faked)
cd frontend && pnpm exec next typegen && pnpm exec tsc --noEmit && pnpm lint && pnpm build
```
Every push runs **CI** (ruff + pytest, typegen + tsc + ESLint + build). Every production deploy runs the **smoke test**: it waits until `/api/health` reports the deployed commit, then checks the API and key pages.

## Deploy
One Vercel project with two services (`frontend/` Next.js, `backend/` FastAPI); `/api/*` routes to the backend (`vercel.json`). Three crons: ingest 00:00, daily print 00:30, email 01:00 (UTC). Set the variables from `.env.example` in Vercel. GitHub → Vercel auto-deploys `main`.

## Privacy and safety
No ad trackers, nothing sold. Readers see and can remove everything ParhLo remembers, turn off email and friends, and delete their account in one step. Summaries are grounded in and checked against the source, and every story links to the original. Details: [/privacy](https://parhlo-brown.vercel.app/privacy).
