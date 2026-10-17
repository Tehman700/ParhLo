# Decision Log

Append new entries at the bottom: date, decision, why, alternatives.

| Date | Decision | Why | Alternatives considered |
|---|---|---|---|
| 2026-10-16 | Starter = FastAPI (uv, Py 3.12) + Next.js 16 / Tailwind | Python for AI/ML/data; Next for a polished UI | Single Next.js app (weaker for ML) |
| 2026-10-16 | LLM via any OpenAI-compatible API, configured in `.env` | Swap providers or routers (AI Gateway, OpenRouter, Ollama) with zero code changes | Provider-specific SDKs |
| 2026-10-16 | Python 3.12 (not 3.14) for backend | Best wheel availability for ML/DL libraries | 3.14 (system default) |
| 2026-10-16 | Local hashing embeddings by default for RAG | Works offline instantly with no key; switch to `EMBEDDING_PROVIDER=api` for semantic search | sentence-transformers (large download) |
| 2026-10-16 | No sample data, scripts or extra pages in repo | Stay lean; build only what the real problem needs | — |
| 2026-10-16 | Research-first workflow (problem → market → competitors → plan → build) | Sharper, better-justified solution and pitch | Build immediately |
| 2026-10-16 | Keep **Jev** (TypeSafe System One model) as the go-to for fast routing, classification, scoring and guardrails; LLM for generation | Typed, calibrated decisions in ~100 ms at very low cost; strong reliability/cost story for the pitch. Not installed until a problem needs it | LLM-only routing (slower, costlier, uncalibrated) |
| 2026-10-16 | Vercel AI Gateway / OpenRouter for multi-provider LLM access; eve only as a minor option | Gateway is a `.env` change; eve only fits long-lived TS agent products | — |
| 2026-10-17 | Product name **ParhLo** ("parh lo" = "read it"); only the name is Urdu, everything else English. Public repo `Tehman700/ParhLo`; first commit = pre-event boilerplate, clearly labelled | User's choice; transparent commit history for monitored repo | Subah, The Daily You, Inkling, Folio |
| 2026-10-17 | **Hybrid hosting:** Vercel (app, cron, AI Gateway) + Neon + AWS Mumbai (S3, Polly, SES; SQS/Lambda as the scale path) | Vercel deploys in minutes; AWS is best-in-class for media/email/voice; all-AWS hosting would cost 2–3 h | All-AWS; all-Vercel (Blob, no TTS/email) |
| 2026-10-17 | Feature set from market research: verified summaries, morning box, story clustering + framing, editor's note, finite edition + 3 things + quiz | Trust 37% / AI-summary failures (BBC, Apple, WaPo); avoidance 42%; follow-up Qs most valued; Pakistan utilities & misinformation | Pure feed (like Google News) |
| 2026-10-17 | Prepare a **local, CPU-only model path** (bge-m3, bge-reranker-v2-m3, NLLB, a small GGUF LLM) in addition to the API path | Practice problem banned APIs; laptop has no GPU; 3-hour limit leaves no time to download models on the day | API-only (risk of disqualification) |
| 2026-10-17 | **OpenAI direct** instead of Vercel AI Gateway | Gateway needed a credit card; same OpenAI-compatible client, model names auto-converted | AI Gateway |
| 2026-10-17 | **Own auth**: email OTP via SES + Google OAuth + httpOnly session cookie; **Clerk removed** | User wanted a simple OTP flow and our own UI; Clerk required password and bot-protection settings that blocked code-only sign-up | Clerk, Auth.js |
| 2026-10-17 | **Apple design system exactly** (white/`#f5f5f7`, one blue `#0066cc`, Inter, pills, GSAP) + **plain-English copy** | User direction after a light-brown variant was rejected | Newspaper/serif chrome, brown theme |
| 2026-10-17 | Work **on production only**; GitHub → Vercel auto-deploy on every push | User direction; every module is tested on the live site | Local development |
| 2026-10-17 | Dawn via **Google News `site:dawn.com` fallback** | Dawn's RSS blocks Vercel/cloud IPs (HTTP errors), works from home IPs | Drop Dawn; proxy |
| 2026-10-17 | `reasoning_effort` minimal (summaries, extraction) / low (editor) for GPT-5 models | Paper generation 117 s → 19–34 s with no visible quality loss | Default (medium) reasoning |
| 2026-10-17 | Lead story must be **full-text** grounded; excerpt-only stories get 1-sentence summaries | Google News links can't be fetched in full; front page needs a real summary and a real ✓ | Let the LLM pick any lead |
| 2026-10-17 | **Jev decision layer live**: Choice topic + Noul junk + Score importance per article; Noul summary check replaces the 2nd LLM call; **LLM/embedding fallback** if Jev fails | Benchmark: same 94% accuracy as gpt-5-nano, 434 ms vs 941 ms median, plus calibrated confidence; junk (quizzes, podcasts, tag pages, crypto promos) now filtered | LLM-only checks; hard-coded blocklist |
| 2026-10-17 | **2 "Top story" common-core slots** (Jev importance ≥ 0.7, + outlet coverage) for every reader | Reuters Institute: 48% worry about missing important news; avoids filter bubbles | Purely personal ranking |
| 2026-10-17 | Thresholds: junk ≥ **0.78** hidden; ✓ only if unsupported-claim probability < **0.3** | 0.70 hid real stories (e.g. Ferrari driver change); low-confidence ✓ (16%) was misleading | 0.5 defaults |
| 2026-10-17 | Second Claude session owns research + architecture diagram (`docs/research/05+`, `docs/diagrams/`, `docs/pitch/`); build session owns code + core docs | Parallel work without merge conflicts | One session for everything |
| 2026-10-17 | **Onboarding upgrade** from the research (Pinterest/Flipboard/Spotify/Particle): live front-page preview, adaptive swipes, transparency note, fading onboarding interests | Show value immediately; fewer, smarter questions; Reuters: explain personalisation and keep a common core; let behaviour take over | Value-before-sign-up (kept for the roadmap: touches auth, too risky today) |
| 2026-10-17 | Starter-only deps moved to optional `starter` extra; starter routes behind `ENABLE_STARTER` | Vercel installs Python deps on cold start; cold start 12 s → 4.5 s | Keep everything installed |
| 2026-10-17 | OTP email via **Gmail SMTP** (app password) first, **SES fallback** | SES was in sandbox (verified addresses only); after production access was granted, Gmail stays primary because a gmail.com sender through SES fails DMARC | SES only; Resend (needs a domain) |
| 2026-10-17 | Session cookie/Bearer **always beats** the `X-Demo-User` header; demo storage cleared on real sign-in | A signed-in user was still seeing the demo reader | Separate demo subdomain |
| 2026-10-17 | `/dashboard` replaces `/profile`: settings-style page with profile, topic switches (on = 0.8 + anchor, off = 0.05, anchor removed), following, about you, memory, account deletion | Each reader needs to see and edit what ParhLo knows; GDPR-style delete | Separate settings pages |
| 2026-10-17 | Sign-out = clear storage + logout + `location.replace("/")` | A state-only sign-out let protected pages redirect to `/sign-in` first (race) | `router.push` after state change |
| 2026-10-17 | Web app presented as a **general consumer product** (privacy, terms, about, how-it-works, footer; no event branding) | User direction | — |
