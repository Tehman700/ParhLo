# Process — From Problem Statement to Demo

**Rule: no building until steps 1–3 are written down in `docs/research/`.** Keep each step time-boxed; a hackathon rewards a sharp, focused solution over a broad one.

## 1. Understand the problem → `research/01-problem.md`
- Restate the problem in one sentence, in our own words.
- Who is the user? What pain do they have today? How do they solve it now?
- Inputs and outputs: what data do we get, and what must the system produce?
- Judging criteria and constraints (time, data, offline, language such as Urdu/English, cost).
- Hidden requirements and edge cases.
- What does "winning" look like in the demo?

## 2. Market research → `research/02-market.md`
- Market size and context (global and Pakistan/regional, if relevant).
- Target users and segments, ranked by how badly they need this.
- Trends and why now (new models, regulation, adoption).
- Real numbers with sources (link everything; no invented stats).

## 3. Competitors & gaps → `research/03-competitors.md`
- 5–10 existing products, open-source projects and research approaches.
- For each: what it does, pricing, strengths, weaknesses, and who uses it.
- The **gap**: what nobody does well that we can show in a demo.
- Our angle in one line: "Unlike X, we ___ for ___."

## 4. Solution plan → `research/04-plan.md`
- Core user flow (3–5 steps) that the demo will show.
- Must-have vs. nice-to-have features (cut hard).
- Architecture: which starter modules we use (agent, RAG, ML, vision, MCP), which new tools, which model/router, and whether eve or Python fits better.
- Data: source, cleaning, any synthetic data needed.
- Risks and fallbacks (API limits, latency, bad model output).
- Build order with time estimates.
- Log key choices in [decisions.md](decisions.md).

## 5. Build
- Problem-specific logic goes in new `backend/app/services/<domain>/` + tools in `backend/app/tools/` + routes in `backend/app/api/`.
- Frontend: new page = `frontend/app/<route>/page.tsx` + add it to `LINKS` in `components/Nav.tsx`.
- Keep `uv run pytest -q` green and add a test per new endpoint.

## 6. Demo & pitch
- Story: problem → who suffers → market → competitors' gap → **live demo** → impact → what's next.
- Pre-demo check: backend up, key set, `/health` ok, happy path rehearsed, fallback screenshots/video ready.

---

## Research file templates

### Competitor entry
```md
### <Name> — <url>
- What: 
- Users / pricing: 
- Strengths: 
- Weaknesses: 
- Lesson for us: 
```

### Source citation
`- <claim> — <source title>, <url> (accessed YYYY-MM-DD)`
