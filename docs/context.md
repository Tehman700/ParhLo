# Project Context

_Last updated: 2026-10-17, ~15:30 PKT (after Module B). Read this first in any new session._

## The competition
- **Event:** FAST NaSCon'26 hackathon, solo participant. **Problem (by Eynvision): "Build a personal morning paper."**
- **Deliverables:** public GitHub repo (commits monitored), Loom video of 5 minutes or less, architecture design diagram. **Submit by 20:20 PKT, hard end 21:00.**
- Full analysis: [research/01-problem.md](research/01-problem.md) · Market and competitors: [02](research/02-market.md), [03](research/03-competitors.md) · Plan: [04](research/04-plan.md)

## The product: ParhLo
"Parh lo" means "read it". Only the name is Urdu; the UI and content are in English.

ParhLo learns what a reader cares about, collects news from Pakistani and global outlets every night, and prints **one finite, personal paper**:
- a web page and a newspaper-style PDF
- an archive of past papers
- learning from opens, skips and likes

The pitch: **"Jev decides, the LLM writes."**

- **Live:** https://parhlo-brown.vercel.app · **Repo:** https://github.com/Tehman700/ParhLo (push to `main` → auto-deploy)
- **Technical source of truth:** [architecture.md](architecture.md)
- **Another Claude session** handles research and the architecture diagram: [HANDOFF-research-session.md](HANDOFF-research-session.md)

## Ground rules
1. Research before building; the brief is context, not a spec.
2. Work on production, not localhost: every push deploys, and features are tested on the live site.
3. Design: **exactly `Design-Files/apple-DESIGN.md`**. White/`#f5f5f7` surfaces, one blue `#0066cc`, Inter, pill buttons, GSAP motion. **Plain English copy**, no flourishes like "Good morning.".
4. Honest product: no fake success states, every summary sourced and checked, junk hidden.
5. Build module by module, test each, then stop for the user's go-ahead.

## Stack and accounts
| Layer | Choice |
|---|---|
| Hosting | Vercel project `tehman-hassans-projects/parhlo` (services: `frontend/` Next.js 16 + `backend/` FastAPI), crons in `vercel.json` |
| Database | Neon Postgres + pgvector (via Vercel Marketplace; same DB for all environments) |
| LLM | OpenAI direct (`LLM_API_KEY`): gpt-5-mini (editor, extraction), gpt-5-nano (summaries), text-embedding-3-small |
| Decision model | **Jev** (TypeSafe System One, `TYPESAFE_API_KEY`, `jev-latest`) |
| AWS (ap-south-1) | IAM user `parhlo-vercel` (S3 bucket `parhlo-media-109257212304`, Polly, SES). Keys are `PARHLO_AWS_*`, because Vercel reserves `AWS_*` and injects `AWS_REGION=us-east-1` |
| Email | **Gmail SMTP** (`GMAIL_USER` + `GMAIL_APP_PASSWORD`, sender tehmanhassan@gmail.com) reaches any address; **SES** (out of sandbox, 50k/day) is the automatic fallback |
| Auth | Own: email OTP (Gmail SMTP) + Google OAuth → httpOnly session cookie. Demo readers via `X-Demo-User` |

All secrets are in Vercel env and the root `.env` (gitignored). Never commit or print them.

## Module status
| Module | Status |
|---|---|
| Setup, auto-deploy, schema | ✅ |
| Login (OTP + Google), Clerk removed | ✅ tested live |
| Apple-style redesign + GSAP | ✅ live |
| **A** Live AI pipeline (ingest → rank → summarize → edit → paper → PDF) | ✅ live, 19–34 s per paper |
| **B** Jev layer (topic, junk, importance, 2 Top-story slots, summary check with confidence, LLM fallback) | ✅ live, 42 tests pass |
| **C** Onboarding upgrade (live preview, adaptive swipes, transparency, fading) | ✅ live, E2E 15/15 |
| Account batch: demo/login fix, OTP to any email, `/dashboard`, privacy/terms/about/how-it-works, footer | ✅ live, E2E 32/32 |
| Background first paper, animated How it works, persistent reactions + saved, friends (invites, bell, Learn from friends) | ✅ live |
| **D** Full flow test | ✅ live, E2E 31/31 with two accounts |
| **E** Demo readers (2 read-only sample readers, guest cleanup) | ✅ live, E2E 23/23 |
| **G** Ask your paper + personal front page fix | ✅ live, E2E 13/13 |
| **I** Morning email (Postgres queue) | ✅ live, E2E 18/18 |
| Reprint on interest change (n8n Cloud workflow + page fallback) | ✅ live via n8n Cloud (`hackathonss.app.n8n.cloud`), reprint ≈ 28 s after a change; E2E 10/10 |
| CI/CD (GitHub Actions + production smoke test) | ✅ |
| F Compare · H Audio | ✂ dropped (user decision) |
| J Submission (README, diagram, Loom) | from 19:15 |

## Known issues and notes
- **Dawn blocks Vercel's IPs;** we use Google News `site:dawn.com` instead. Those links can't be read in full, so those summaries use the excerpt, and the lead story must be full-text.
- **Email:** Gmail stays primary even though SES is out of sandbox, because SES sending from a gmail.com address fails DMARC and lands in spam. Move to SES once we own a domain.
- **Sample readers:** `users.persona` (Ayesha `e9079294-…`, Omar `104a8db0-…`). Read-only; nightly cron prints their paper but never consolidates them. Demo guests (`is_demo and not persona`) are deleted after 3 days.
- **Web app copy is a general consumer product:** no event or hackathon names anywhere in the UI.
- **n8n:** workflow lives in `n8n/paper-refresh.workflow.json` (import into n8n, activate, copy the Webhook node's Production URL into Vercel env `N8N_WEBHOOK_URL`, redeploy). Without it, the paper page asks for the reprint itself after 25 s. Local test n8n: `docker run … n8nio/n8n` with `MSYS_NO_PATHCONV=1` in Git Bash.
- **CI:** every push runs `.github/workflows/ci.yml`; every production deploy runs `smoke.yml`. The frontend build retries once (Google Fonts fetch is flaky on runners). Another Claude session also pushes UI work to `main`: always `git pull --rebase` before pushing.
- **Local `PUBLIC_URL` is localhost** (production has the real one); links built locally (emails, unsubscribe) point at localhost.
- **Full flow E2E:** `ui/full_flow.mjs` (two accounts, ~4 min, deletes both at the end).
- **Production E2E scripts** live in the session scratchpad (`ui/batch_e2e.mjs`, `ui/mkotp.py` creates a sign-in code in the DB without sending email; `ui/cleanup.py` deletes `rivonna.ai+e2e*` test accounts).
- **Windows dev:** set `PYTHONUTF8=1`. Python from bash can't read `/tmp`, so use the scratchpad.

## Run / test
```powershell
cd backend; uv run --extra starter pytest -q      # offline tests (starter extra needed)
cd frontend; npx tsc --noEmit; npx next build     # type + build check
# production checks: https://parhlo-brown.vercel.app/api/health
```

## Other resources
- Offline model kit (from the earlier no-API practice problem): `C:\Users\Tehman Hassan\Desktop\AI-Models\`. Not used by ParhLo.
- [original-brief.md](original-brief.md) (pre-event starter brief) · [process.md](process.md) · [decisions.md](decisions.md)
