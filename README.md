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

## Why we built it this way (market research)

Before building, we studied how people actually feel about news today, and what goes wrong when AI touches it. Every major feature answers one of these findings. Sources and more detail: [docs/research/02-market.md](docs/research/02-market.md) and [docs/research/03-competitors.md](docs/research/03-competitors.md).

### What people think about news
| What people say or do | The evidence | What we built |
|---|---|---|
| **"It's too much."** People are switching off. | **42%** sometimes or often avoid the news (up from 29% in 2017); constant updates "risk creating a sense of overload" (Reuters Institute Digital News Report 2026, ~100k people, 48 markets). | A **finite** paper sized to your reading time (5–20 min) that **ends**, plus "3 things to remember" so you finish knowing something. |
| **"I don't know what to trust."** | Trust in news is **37%**, the lowest since 2015; trust in news on social media 22%; 62% worry about fake news. In Pakistan, **9 in 10** see misinformation as a problem and only 3 in 10 can always spot it. | Trusted outlets only, **every summary checked against its source** (✓ with confidence), every story links to the original, and the same event appears once, not five times. |
| **"I don't trust AI with news."** And they're right. | Only **20%** trust chatbot news answers. A BBC study found **51%** of AI assistants' news answers had significant issues and **13%** of quotes were altered or invented. Apple **switched off** AI news summaries after a false headline. | Summaries written **only from the article text**, verified by a second model (Jev), excerpt-only stories labelled as such, and Ask your paper **refuses** to answer beyond your paper. |
| **"Let me ask follow-up questions."** | Asking follow-ups is the **most valued** AI news feature (42%), and 42% click through to sources. | **Ask your paper**, with sources on every answer and "Ask about this story" on every card. |
| **"My news is scattered everywhere."** | Platforms (54%) now beat going direct to publishers (51%). Young Pakistanis get news from **WhatsApp (93%)** and Facebook (83%) and see TV channels as biased. | **One place**: Pakistani and world outlets in one paper, on the web, as a PDF and in your inbox, ranked for you. |
| **"Why am I seeing this?"** | Personal feeds feel like black boxes, and 48% worry about missing important news. | **Why-lines on every story**, a dashboard showing everything ParhLo remembers (removable), and **two Top stories for everyone** so you never miss the big news. |
| **"I like a paper, not a feed."** | A Dawn reader calls the paper "mandatory intake with my breakfast"; short newsletters with a clear editor's voice get **~45% open rates** (Morning Brew, TLDR). | A real **edition**: masthead, lead, sections, editor's note, a newspaper-style PDF, an archive, and a 6 AM email. |
| **"Give me the morning basics."** | Pakistanis check the dollar rate, petrol prices, weather and smog, and cricket every morning. | A **morning box**: weather, air quality with smog alerts, PKR rates, the latest cricket. |

### The competition, and the gap
| Product | Strength | What's missing |
|---|---|---|
| ChatGPT Pulse | Proactive, personal morning cards | Pro-only, not a newspaper, chatbot trust ~20% |
| Google News / Apple News | Huge coverage, personal feed | Infinite feed, little explanation, no edition |
| Morning Brew, TLDR | Habit and voice (~45% opens) | The same email for everyone |
| Digest, Readless | Merge your sources into one AI email | Plain email, no learning you can see or control |
| PaperLater | Proof that people love a *paper* object | Manual, no AI |
| Dawn app / e-paper | Trusted brand | No personalization, one source, scanned e-paper |

**No product combines all four:** a real **edition** (finite, newspaper-designed, web + PDF + archive), **visible, controllable learning**, **AI that shows its work** (grounded, checked, sourced), and **Pakistan plus the world** in one paper with the morning essentials. That's ParhLo: *"one finite, newspaper-quality paper each morning that is personal, verifiable, and gets smarter every day."*

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

## How ParhLo learns (and gets better every day)

ParhLo's memory has three layers, all in Postgres:

| Layer | What it is | Example |
|---|---|---|
| **Short-term: reading events** | Every open, read, like, dislike, save, skip and question, as it happens | "Opened the Verstappen story, read it for 70 s" |
| **Long-term: interests** | A weight per topic (0–1), the outlets you prefer, and **interest anchors**: vectors for things you care about | Formula 1 0.8 · "Babar Azam" · a story you liked |
| **History: snapshots** | What changed each night, and why | "Cricket 0.62 → 0.71 · You engaged with 2 Cricket stories" |

**1. Every action is a signal.** Like or save **+1**, open **+0.6**, asking about a story **+0.5**, reading time up to **+0.4** (about a minute of reading), skip **−0.3**, dislike **−1**. If you undo a like or a save, it stops counting.

**2. Strong signals act straight away.** A like, save or dislike turns that story's meaning (its embedding) into an anchor: **+0.8** for "more like this", **−0.8** for "less like this". The very next print ranks every story against these anchors in Postgres (pgvector), so similar stories rise and disliked kinds of story sink.

**3. Every night, ParhLo consolidates** what you did that day:
- **Topics move toward what you actually read:** each topic shifts by up to 0.12 per night, in proportion to that day's signals (bounded, so one evening can't flip your paper).
- **Unused interests fade slowly,** by 2% a night.
- **Stories you read properly become memories** (weight 0.5), so ParhLo learns specific interests your topic picks don't capture, like "Pakistan's IT exports".
- **Your onboarding choices fade gradually** (a half-life of about 2 months, never below 0.3), so **what you read takes over from what you said**, the way Spotify treats its onboarding. Older one-off memories decay too (3% a night).
- **The outlets you engage with** get a small preference.
- **A snapshot records every change with a reason,** shown on your dashboard.

**4. You stay in control.** The dashboard shows everything ParhLo remembers ("You chose Cricket", "You follow Nvidia", "You liked …") and you can remove any of it. Switching topics, following a name (or tapping **Follow** in search), or describing yourself in your own words (the AI extracts interests and names) **reprints today's paper in about 2.5 seconds**. **Update now** runs the nightly learning on demand.

**5. It learns without trapping you.** Every paper keeps **two Top stories for everyone** and about **15% "something new"** from topics you haven't chosen (never ones you switched off). Variety (MMR) avoids five near-identical stories, the same event appears once, and yesterday's events aren't repeated. With **Learn from friends** on (both people opt in), your interests drift slightly toward friends' strong interests, at most +0.03 per topic per night.

**What it looks like over time.** On day 1 your paper comes from the topics you picked and a few swipes. After a few days of reading, the stories you open and like shape it more than your initial picks, specific interests appear as their own memories, and the topics you skip quietly shrink. By week three it's built mostly from what you actually read. Every step is visible and reversible on the dashboard.

Ranking, for the curious: `score = 0.40·best interest match + 0.17·topic weight + 0.11·recency + 0.08·importance (Jev) + 0.08·source quality + 0.07·Pakistan/world fit + 0.05·outlet coverage + 0.05·outlet preference − 0.55·match to things you disliked`.

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
