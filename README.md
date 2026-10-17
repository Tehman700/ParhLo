# ParhLo

**Your personal morning paper.** ParhLo learns what you care about, gathers the articles that matter to you from across the web every day, and delivers one personal paper. You can read it on the web or download it as a newspaper-style PDF, and it gets better the more you read.

> Built for the NaSCon'26 hackathon. Problem statement: "Build a personal morning paper" (Eynvision).

## Status
🚧 In progress. The first commit is our pre-event **boilerplate starter** (FastAPI backend + Next.js frontend + docs); product work starts after it.

## Repo layout
| Path | What |
|---|---|
| `backend/` | FastAPI (Python 3.12, uv): LLM service, agent/tool loop, RAG, ML and vision modules, tests |
| `frontend/` | Next.js 16 + Tailwind v4 web app |
| `docs/` | Context, process, decision log and research. Start at [docs/README.md](docs/README.md) |
| `Design-Files/` | UI design references |

## Run locally
```powershell
copy .env.example .env    # add your LLM key

cd backend;  uv sync; uv run uvicorn app.main:app --reload --port 8000   # API docs: http://localhost:8000/docs
cd frontend; pnpm install; pnpm dev                                       # http://localhost:3000
cd backend;  uv run pytest -q                                             # tests
```
