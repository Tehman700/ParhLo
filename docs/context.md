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
| Email | SES sandbox: only `tehmanhassan@gmail.com` and `rivonna.ai@gmail.com` are verified (sender is tehmanhassan@gmail.com) |
| Auth | Own: email OTP via SES + Google OAuth → httpOnly session cookie. Demo readers via `X-Demo-User` |

All secrets are in Vercel env and the root `.env` (gitignored). Never commit or print them.

## Module status
| Module | Status |
|---|---|
| Setup, auto-deploy, schema | ✅ |
| Login (OTP + Google), Clerk removed | ✅ tested live |
| Apple-style redesign + GSAP | ✅ live |
| **A** Live AI pipeline (ingest → rank → summarize → edit → paper → PDF) | ✅ live, 19–34 s per paper |
| **B** Jev layer (topic, junk, importance, 2 Top-story slots, summary check with confidence, LLM fallback) | ✅ live, 42 tests pass |
| **C** Onboarding upgrade | ⏳ next |
| D Full flow test · E Demo readers · F Compare · G Ask your paper · H Audio · I Email | ⬜ |
| J Submission (README, diagram, Loom) | from 19:15 |

## Known issues and notes
- **Dawn blocks Vercel's IPs;** we use Google News `site:dawn.com` instead. Those links can't be read in full, so those summaries use the excerpt, and the lead story must be full-text.
- **SES sandbox:** OTP only reaches the 2 verified emails. Production access has not been requested yet.
- **Test readers in the DB:**
  - Ayesha `e9079294-e5aa-4719-92bd-1da7db1b88fd` (Lahore, AI/tech)
  - Omar `104a8db0-b1bb-4853-85b5-7606ff152ced` (Karachi, business/cricket)
  - "Fixture Reader" `3f905069-…` (to delete in Module E)
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
