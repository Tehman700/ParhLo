# Original Brief (restored copy of main-context.md)

> This was the pre-competition brief. Treat it as **background, not a spec**. See [context.md](context.md) for current decisions.

# Project: NaSCon 2026 AI Hackathon — Universal AI Starter

## Context

I am participating **solo** in the FAST NaSCon 2026 AI Hackathon.

This is a fast-paced competition where participants receive an AI-related problem statement and must develop a working solution within a limited time.

The problem could involve machine learning, deep learning, LLMs, AI agents, RAG, computer vision, data processing, automation, MCP, or a combination of these technologies.

**Our objective is to prepare a flexible, reusable AI application foundation before the competition.**

We do not know the actual problem statement yet, so do not build a specific final product. Instead, create a well-organized starter project that can be rapidly adapted to different AI challenges.

The project should prioritize:
- Fast development and iteration.
- Reusable components.
- Easy integration of different AI models and APIs.
- Clean frontend and backend separation.
- Simple configuration.
- Working demonstrations.
- Easy debugging and modification.

Avoid unnecessary enterprise architecture, excessive abstractions, complicated security systems, or infrastructure that slows down development.

## 1. Technology Stack

**Frontend**: Next.js with TypeScript, Tailwind CSS, modern responsive dashboard, reusable UI components, charts when needed.

**Backend**: Python with FastAPI, Pydantic models, modular services and API routes, async where useful.

**AI Integration**: OpenAI-compatible LLM API, configurable model and provider, tool/function calling, structured JSON outputs, optional local models, image-capable models.

**Data**: SQLite, Pandas and NumPy, Scikit-learn, optional FAISS or Chroma, support for CSV, JSON, PDF and images.

**Optional**: MCP Python SDK, LangGraph if complex orchestration is needed, PyTorch / Hugging Face Transformers for ML/DL.

Do not install every optional dependency immediately. Keep optional modules independent and easy to enable.

## 2. Project Structure

A clean monorepo: `frontend/` (app, components, lib, public), `backend/` (app/main.py, api, core, services/{llm,agents,rag,ml,vision}, tools, models, utils, tests), plus `.env.example` and `README.md`. Adjust if a simpler arrangement is more practical. No unnecessary empty files or complicated modules.

## 3. Core Features

- **A. LLM Integration** — configurable key/model/provider, chat completion, structured JSON, tool calling, conversation history, error handling, optional streaming. Everything else uses this service.
- **B. AI Agent System** — receive request, LLM picks tools, execute, feed results back, final response, record steps for the frontend. Simple tool-calling loop; 2–3 example tools.
- **C. RAG Module** — upload PDF/TXT, extract, chunk, embed, store/search vectors, retrieve, answer with source references. Independent / optional.
- **D. ML Module** — CSV loading/exploration, missing values, preprocessing, train/test split, training, evaluation, save/load, predictions (scikit-learn utilities).
- **E. Vision** — image upload, preprocessing, vision-capable model, structured analysis. No large model downloads.
- **F. MCP** — optional server, register Python functions as tools, client discovery/invocation. Must not be a dependency of the whole app.

## 4. Frontend

Professional AI dashboard: chat input, responses, loading, errors, history; tool execution panel (tools used, results, timing); file upload (PDF, CSV, images) with processing results; results workspace (JSON, tables, charts, reports/predictions). Polished for a demo, easy to modify, no complicated design system.

## 5. API Endpoints

`GET /health`, `POST /api/chat`, `POST /api/agent/run`, `POST /api/files/upload`, `POST /api/rag/query`, `POST /api/ml/predict`, `POST /api/vision/analyze`. Only expose implemented features; no fake success responses. FastAPI auto docs.

## 6. Configuration and Development

`.env.example`, install instructions, start commands, example requests, basic tests. Must work locally on Windows. Avoid Docker, cloud deployment, auth, Redis, Kafka, Celery unless genuinely necessary.

## 7. Adaptability

Document intelligence → RAG. Business automation → agent + new tools. Predictive ML → ML utilities + prediction API. Computer vision → vision module. MCP → extend MCP module. Avoid coupling modules.

## 8. Competition-Day Docs

`HACKATHON_GUIDE.md` (start project, where problem logic goes, add a tool, change LLM provider, add endpoint, add frontend page, enable modules, testing, common commands) and `DEMO_CHECKLIST.md`.

## 9. Implementation Priorities

Phase 1 foundation (backend, frontend, LLM, chat, FE↔BE) → Phase 2 agent (registry, execution, history, tools) → Phase 3 modules (RAG, ML, vision, MCP) → Phase 4 polish (UI, tests, docs). Phase 1 must fully work first.

## 10. How to Work

Inspect environment → explain architecture → create structure → implement foundation → install deps → run and fix → test → continue with modules → summarize what works vs. optional. Make practical decisions independently. Don't over-build for hypothetical problems.
