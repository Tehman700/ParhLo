# Handoff: research and architecture-diagram session

_For the Claude session handling **research** and the **architecture diagram**. Written by the build session on 2026-10-17. Read this first, then [`architecture.md`](architecture.md)._

## The product in 30 seconds
**ParhLo** ("parh lo" = "read it"; only the name is Urdu, everything else is English) is a **personal morning paper**. It's our NaSCon'26 hackathon entry; the problem statement is in `NaSCon'26 Problem Statement.pdf` and summarised in `research/01-problem.md`.
- **What it does:**
  - Learns what a reader cares about.
  - Gathers articles daily from Pakistani and global outlets.
  - Prints one finite paper as a web page and a newspaper-style PDF, with an archive.
  - Gets better with use.
- **The design pitch:** "Jev decides, the LLM writes."
  - Jev (TypeSafe's System One decision model) tags, filters junk, scores importance and verifies summaries.
  - OpenAI writes the summaries and the layout.
- **Live:** https://parhlo-brown.vercel.app (no account needed: **Try the demo**). Repo: https://github.com/Tehman700/ParhLo

## Deadline and deliverables (from the problem statement)
**Submit by 20:20 PKT today (hard end 21:00):**
1. The public GitHub repo link.
2. A **Loom video, 5 minutes or less**.
3. **A design diagram of the architecture** ← this is yours.

## Your job
1. **Architecture diagram.** Build it from [`architecture.md`](architecture.md), which reflects what is actually built and live, not plans.
   - **Must show:**
     - The two Vercel services (Next.js frontend, FastAPI backend) and the cron jobs.
     - Neon Postgres + pgvector.
     - OpenAI (embeddings, gpt-5-nano summaries, gpt-5-mini editor).
     - **Jev** (topic, junk, importance, summary check), clearly marked as the decision layer.
     - AWS (SES now; S3 and Polly for PDF/audio storage and audio).
     - Google OAuth, the news sources, and the free data APIs.
   - **Also show** the 12-stage daily pipeline (§3) and the learning loop (§4: events → profile → tomorrow's paper).
   - **Optional, if useful:** a second, simpler "how a paper is made" flow diagram for the Loom.
   - **Style:** clean, white background, one blue accent (`#0066cc`), Inter or SF-like font. This matches the product UI in `Design-Files/apple-DESIGN.md`. Plain-English labels.
2. **Research** that strengthens the pitch and README: competitors, user needs, numbers with sources. Existing work is in `research/02-market.md` and `03-competitors.md`. You also produced the onboarding research; please save it as **`docs/research/05-onboarding.md`**, which the build session deliberately did not create.
3. **Loom script support (optional):** a 5-minute outline in the order onboarding → paper → learning → PDF → architecture → Jev numbers.

## Rules (two sessions share one repo)
- **Only touch files you own:**
  - `docs/research/05-*` and any newer research files
  - `docs/diagrams/` (create it) for diagram sources and exported images (`.svg`, `.png`, `.mmd`, `.excalidraw`)
  - `docs/pitch/` (create it) for Loom and pitch material
- **Don't edit:**
  - `backend/`, `frontend/`, `vercel.json`
  - `docs/context.md`, `docs/architecture.md`, `docs/decisions.md`, `docs/research/04-plan.md`

  The build session updates those. If something in them is wrong, add a note under "Notes from the research session" at the bottom of this file.
- **Git:** `git pull --rebase` before every commit, keep commits small, push right away. Pushes to `main` deploy the site automatically. Docs-only changes are harmless, but never push code.
- **Never commit secrets.** `.env` and `.env.local` are gitignored, and keys live in Vercel's environment settings.
- **Numbers:** use only the measured values in `architecture.md` §8, or figures from cited sources. Don't invent metrics.

## Status (build session)
| Module | Status |
|---|---|
| Setup: Vercel, Neon, AWS, auto-deploy | ✅ |
| Login: email OTP via SES + Google OAuth (own implementation) | ✅ live |
| Apple-style UI + GSAP, plain English | ✅ live |
| **A. Live AI pipeline**: ingest → rank → summarize → edit → paper + PDF | ✅ live |
| **B. Jev decision layer**: topic, junk, importance, common core, summary check | ✅ live |
| C. Onboarding upgrade: live preview, adaptive swipes, name prefill, transparency line, fading onboarding interests | ⏳ next |
| D. Full flow test · E. Demo readers · F. Two-persona compare · G. Ask your paper · H. Audio · I. Morning email | ⬜ planned |
| J. Submission: README, diagram (**you**), Loom | from 19:15 |

## Useful facts for the diagram and pitch
- **Measured Jev vs LLM summary check** (16 real and falsified summaries):
  - Jev: 94% correct, **434 ms median**, with a confidence score.
  - gpt-5-nano: 94%, 941 ms.
  - Both caught every falsified summary.
- **Scale:** Jev classified 1,029 articles in 30 s. A paper prints in about 20–30 s. The PDF renders in about 7 s.
- **The common core:** 2 "Top story" slots every reader gets. This responds to the Reuters Institute finding that 48% of people worry about missing important news. Personal picks and about 15% discovery picks keep readers out of a filter bubble.
- **Trust:** every summary is written only from the source and checked against it, with the original one tap away. This contrasts with the BBC study (51% of AI news answers had significant errors) and Apple pausing its AI news summaries; see `research/02-market.md`.

## Notes from the research session
_(append here)_
