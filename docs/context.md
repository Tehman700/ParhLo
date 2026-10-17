# Project Context

_Last updated: 2026-10-16_

## The competition
- **Event:** FAST NaSCon 2026 AI Hackathon. **Solo** participant.
- **Format:** an AI problem statement is revealed, then a working solution must be built in limited time.
- **Problem statement (revealed 2026-10-17): "Build a personal morning paper"**, by Eynvision. An interest-learning, daily personalized news paper with onboarding, a newspaper-style PDF, a web reading experience with an archive, and a learning loop. Submit: public GitHub repo (commits monitored from the start), Loom ≤5 min, architecture diagram. No API ban stated. Full analysis: [research/01-problem.md](research/01-problem.md).

## Ground rules we agreed
1. **Research before building.** When the problem drops, we first do problem analysis, market research and competitor analysis. Only then do we plan and build. See [process.md](process.md).
2. **The original brief is context, not a spec.** Don't follow it literally.
3. **Stay lean.** Build only what the actual problem needs. No sample data, scaffolding folders or extra pages "just in case".
4. **Be honest in the demo.** No fake success responses. If something needs a key or isn't built, say so.

## What's already built (starter)

### `backend/` — FastAPI + uv (Python 3.12)
| Area | Where | Status |
|---|---|---|
| Config (`.env` at repo root) | `app/core/config.py` | ✅ |
| LLM service (any OpenAI-compatible API: chat, JSON, tools, streaming, embeddings) | `app/services/llm/client.py` | ✅ |
| Agent loop (tool calling, step log with timings, max iterations) | `app/services/agents/agent.py` | ✅ |
| Tool registry (`@tool` decorator → JSON schema) | `app/tools/registry.py` | ✅ |
| Example tools: calculator, list_tables/query_database (SQLite, read-only), analyze_csv/aggregate_csv, search_documents | `app/tools/` | ✅ |
| RAG: PDF/TXT/MD → chunk → embed (local hashing or API) → numpy store → search/answer with sources | `app/services/rag/` | ✅ optional (`ENABLE_RAG`) |
| ML: CSV profile, preprocessing, train/evaluate/save/predict (scikit-learn) | `app/services/ml/toolkit.py` | ✅ optional (`ENABLE_ML`) |
| Vision: Pillow preprocessing → vision model → structured JSON | `app/services/vision/analyzer.py` | ✅ optional (`ENABLE_VISION`) |
| MCP server + client (mcp 2.x `MCPServer`), exposes all tools | `app/services/mcp/` | ✅ optional (`uv sync --extra mcp`) |
| Tests (offline, fake LLM, temp data) | `tests/` | ✅ 31 passing |

**Endpoints:** `/health`, `/api/config`, `/api/chat`, `/api/chat/stream`, `/api/agent/{run,tools,tools/{name}}`, `/api/files/{upload,…}`, `/api/rag/{search,query,index,documents}`, `/api/ml/{datasets,profile,train,predict,models}`, `/api/vision/analyze`. Docs at `http://localhost:8000/docs`.

### `frontend/` — Next.js 16.4 + Tailwind v4 + recharts
- Workspace page (`app/page.tsx`): Agent/Chat toggle, streaming chat, tool execution panel, raw result view, tool list.
- Shared bits: `lib/api.ts` (typed API client + SSE), `lib/hooks.ts`, `components/` (ui kit, Nav, ToolSteps, BarChart, FileDrop).
- Styling follows `Design-Files/apple-DESIGN.md`: one blue accent (#0066cc), parchment/white/near-black surfaces, pill buttons, 18px cards, no decorative shadows or gradients.
- ⚠️ Next 16 differs from older versions. Read `frontend/node_modules/next/dist/docs/` before using unfamiliar APIs (see `frontend/AGENTS.md`).

### Run it
```powershell
# backend
cd backend; uv sync --extra mcp; uv run uvicorn app.main:app --reload --port 8000
# frontend
cd frontend; pnpm install; pnpm dev        # http://localhost:3000
# tests
cd backend; uv run pytest -q
```
Without `LLM_API_KEY`, chat, agent and vision return 503 with a clear message. Tools, retrieval and ML still work.

Runtime files (uploads, sqlite, indexes, models) are written to `data/`, which is gitignored and created automatically.

## ⚠️ Lesson from a practice problem (see research/practice-e-sahulat-analysis.md)
A similar Pakistani competition **banned all API calls** (models had to be open-source and loaded in our own code) and gave only **3–3.5 hours**. If NaSCon does the same:
- The API-based LLM service, Jev and AI Gateway are **not allowed**. We need the **local-model path** (transformers / llama-cpp-python, in-process). Shortlist: [research/urdu-models.md](research/urdu-models.md).
- Our laptop is **CPU-only** (Ryzen 5 5600H, 16 GB RAM, no NVIDIA GPU). Prefer small models (≤4B, GGUF Q4), cached embeddings and extractive answers.
- Judges reward **retrieval quality, grounding/abstention and measured evaluation** far more than UI polish.

## Infrastructure available
- **Hardware:** Ryzen 5 5600H, 16 GB RAM, AMD integrated GPU (no CUDA), ~143 GB free on C:.
- **Offline model kit:** `C:\Users\Tehman Hassan\Desktop\AI-Models\` contains bge-m3, multilingual-e5-small, bge-reranker-v2-m3, NLLB-600M, and GGUF tiny-aya-global, Qwen3-4B and Qalb-8B. See its README.
- **Vercel** (CLI and account): hosting, **AI Gateway**, eve.
- **Neon** (Postgres): use if we need a real hosted DB instead of SQLite.
- **AWS CLI**: S3, Bedrock, etc. if a problem calls for it.

## Tech options to keep in mind (use only if the problem needs them)

### Jev (TypeSafe AI): fast typed decisions and routing
- **What it is:** a "System One" **decision model**, not a chat LLM. You give it a state (text, JSON or images) and typed questions. It returns typed answers with **calibrated probabilities and confidence**, with no free-text generation. Released 2026-09 in early access. Sources: https://typesafe.ai/blog/introducing-system-one-models-and-jev · docs: https://docs.typesafe.ai/llms.txt
- **Question types:**
  - `Choice`: pick one of N labels, max 255 options.
  - `Score`: rate against ordered levels.
  - `Noul`: yes/no probability from 0 to 1.
  - `Box`: bounding box in an image.

  Many questions can go in one parallel call.
- **Vendor claims (their own evals, not independently verified):**
  - Latency of about 70–500 ms, roughly 40–200× faster than LLMs on these tasks.
  - Input costs $0.042 per million tokens; output is free. The pricing may be subsidized.
- **Where it fits for us:**
  - **LLM router / intent routing:** decide which tool, specialist LLM or human handles a request. Use confidence to gate whether to act or escalate.
  - Classification, scoring and extraction at scale (map-reduce over big data). Cheap, fast feature generation for ML.
  - Guardrails and verification: screen LLM inputs and outputs, check citations, score RAG passages before answering.
  - Function or skill selection as a fast pre-step before the agent loop.
- **Not for:** chat, long-form answers or report writing. Those stay on the LLM service.
- **Integration (when needed):**
  - Install with `uv add typesafe-sdk` (Python) or `pnpm add @typesafe-ai/sdk` (frontend).
  - Set the env var `TYPESAFE_API_KEY`.
  - Call it with `TypeSafeClient(model="jev-latest").system_one(state=..., questions={...})`. The HTTP form is `POST https://api.typesafe.ai/v1/systemone` with `Authorization: Bearer <key>`.
  - Plan: a small `backend/app/services/jev/` wrapper, exposed as agent tools and/or a `route()` step in front of the agent.
- **Watch out:**
  - Access requires the early-access waitlist and an API key. **Get the key before the hackathon.**
  - Read the known rough edges: https://docs.typesafe.ai/model-jaggedness/jev-1.13.md
- **Pitch angle:** a "Jev routes/decides → LLM explains" pipeline is a strong story on cost, latency and reliability, and judges like measurable numbers.

### LLM gateway (multi-provider access)
Our LLM service already speaks the OpenAI-compatible protocol, so switching gateways is just a `.env` change:
- **Vercel AI Gateway**: `LLM_BASE_URL=https://ai-gateway.vercel.sh/v1`, models like `openai/...` or `anthropic/...`. One key for many providers, plus fallbacks and spend tracking. **Preferred**, since we have Vercel.
- **OpenRouter**: `LLM_BASE_URL=https://openrouter.ai/api/v1`. Similar idea.
- **Local**: Ollama or LM Studio (`http://localhost:11434/v1`).
- **Per-task routing** (cheap model for simple steps, strong model for reasoning): Jev can make the routing decision, or a small `pick_model(task)` can. Only add this if the problem benefits.

### eve (Vercel's durable agent framework): minor option
TypeScript framework for long-running agents (durable sessions, schedules, subagents). Docs: https://eve.dev/docs. Only consider it if the problem is a long-lived agent product deployed on Vercel.

### Other optional pieces
LangGraph (complex orchestration), FAISS/Chroma (bigger vector stores), sentence-transformers (semantic local embeddings), PyTorch/HF (DL), Neon Postgres (multi-user data).

## Open questions
- Which LLM provider/key will we use on the day? (AI Gateway recommended.)
- Do we have Jev early access / a `TYPESAFE_API_KEY` yet?
- Deploy for the demo (Vercel), or run locally?
