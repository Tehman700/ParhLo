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
