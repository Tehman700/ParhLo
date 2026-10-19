"""Ask your paper: questions answered only from the reader's own edition, with sources.

1. ROUTE  — Jev (Choice) decides which story the question is about, the whole paper, or something not in it.
            Fallback: headline word overlap.
2. ANSWER — the LLM answers from the paper's summaries plus the full text of the routed stories; it must say
            so when the paper doesn't cover the question.
3. LEARN  — asking about a story is a reading signal (event "ask").
"""

import logging
import re
import time
import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from app.core.database import db
from app.core.errors import NotFoundError
from app.parhlo import jev, learn
from app.parhlo.topics import TOPICS
from app.services.llm import get_llm

log = logging.getLogger("parhlo.ask")

FOCUS_MIN = 0.2       # Jev probability for a story to count as a focus
MAX_FOCUS = 3
FULLTEXT_CHARS = 3500
OFFER = re.compile(r"^(would you|do you want|are you|shall i|should i check)", re.I)  # follow-ups are the reader's questions


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    date: dt.date | None = None
    story_id: int | None = Field(default=None, description="the story the reader opened the question from")
    history: list[Turn] = Field(default=[], max_length=10)


class AnswerOut(BaseModel):
    answer: str = Field(description="Plain-English answer using only the paper. Short paragraphs, or a list with "
                                    "each '- ' bullet on its own line; **bold** allowed. Max ~150 words unless the "
                                    "reader asks for detail.")
    story_ids: list[int] = Field(description="ids of the stories the answer actually uses")
    in_paper: bool = Field(description="false when the paper doesn't cover the question")
    follow_ups: list[str] = Field(description="2-3 short follow-up questions in the reader's own voice, answerable "
                                              "from this paper (e.g. 'What happens next?', 'Why are fuel prices "
                                              "falling?'). Never offers like 'Would you like…' or 'Do you want…'.")


def _edition(user_id, edition_date: dt.date | None) -> dict:
    with db() as conn:
        if edition_date:
            row = conn.execute("select id, edition_date, data from editions where user_id=%s and edition_date=%s",
                               (user_id, edition_date)).fetchone()
        else:
            row = conn.execute("select id, edition_date, data from editions where user_id=%s "
                               "order by edition_date desc limit 1", (user_id,)).fetchone()
    if not row:
        raise NotFoundError("Your paper isn't ready yet. Ask again once it's printed.")
    return row


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{4,}", text.lower()))


async def route(question: str, stories: list[dict], story_id: int | None) -> tuple[list[int], dict]:
    """Which stories is the question about? Returns (focus ids, route info for the UI)."""
    t0 = time.perf_counter()
    picked = next((s for s in stories if s["id"] == story_id), None)
    state = {"question": question}
    if picked:
        state["reader_is_looking_at"] = picked["headline"]
    criteria = {f"s{s['id']}": f"{s['headline']}. {s['summary'][:160]}" for s in stories}
    criteria["whole_paper"] = "The paper as a whole or several stories at once (e.g. 'what are today's main stories?')"
    criteria["not_in_paper"] = "Something no story in this paper is about"
    answers = await jev.ask(state, {"focus": {
        "type": "choice", "instructions": "Which story in this newspaper is the reader's question about?", "criteria": criteria}})
    ms = round((time.perf_counter() - t0) * 1000)
    ids = {s["id"] for s in stories}
    try:
        probs = sorted(answers["focus"]["probabilities"].items(), key=lambda kv: -kv[1])
        focus = [int(k[1:]) for k, p in probs if k.startswith("s") and p >= FOCUS_MIN and int(k[1:]) in ids][:MAX_FOCUS]
        info = {"by": "jev", "ms": ms, "choice": answers["focus"]["choice"], "confidence": round(float(answers["focus"]["confidence"]), 2)}
    except (TypeError, KeyError, ValueError):  # Jev unavailable → headline/summary word overlap
        q = _words(question)
        scored = sorted(((len(q & _words(s["headline"] + " " + s["summary"])), s["id"]) for s in stories), reverse=True)
        focus = [i for n, i in scored if n >= 2][:2]
        info = {"by": "keywords", "ms": ms, "choice": None, "confidence": None}
    if picked and picked["id"] not in focus:
        focus = [picked["id"], *focus][:MAX_FOCUS]
    return focus, info


def _context(stories: list[dict], focus: list[int], lead_id: int) -> str:
    with db() as conn:
        full = {r["id"]: r["content"] for r in conn.execute(
            "select id, content from articles where id = any(%s) and content is not null", (focus,)).fetchall()} if focus else {}
    parts = []
    for s in stories:
        tags = [t for t in ("front-page story" if s["id"] == lead_id else "", "one of today's biggest stories" if s.get("core") else "") if t]
        topic = TOPICS.get((s.get("topics") or [""])[0], {}).get("label", "")
        block = (f"[{s['id']}] {s['headline']} ({s['source']}, {topic}{', ' + ', '.join(tags) if tags else ''})\n"
                 f"Summary: {s['summary']}")
        if s.get("points"):
            block += "\nKey points: " + " | ".join(s["points"])
        if s["id"] in full:
            block += f"\nFULL ARTICLE (excerpt): {full[s['id']][:FULLTEXT_CHARS]}"
        parts.append(block)
    return "\n\n".join(parts)


async def ask_paper(user: dict, body: AskIn) -> dict:
    row = _edition(user["id"], body.date)
    paper = row["data"]
    stories = paper["stories"]
    focus, route_info = await route(body.question, stories, body.story_id)

    with db() as conn:
        prof = conn.execute("select topics from profiles where user_id=%s", (user["id"],)).fetchone()
    interests = [TOPICS[t]["label"] for t, _ in sorted(((prof or {}).get("topics") or {}).items(), key=lambda kv: -kv[1])[:5] if t in TOPICS]
    system = (
        f"You answer questions about {paper['reader']['name']}'s ParhLo newspaper for {row['edition_date']:%A %d %B %Y}. "
        f"The reader lives in {paper['reader']['city']} and is interested in {', '.join(interests) or 'general news'}.\n"
        "Rules: use ONLY the stories below. Never invent facts, numbers, names or quotes, and never expand an "
        "abbreviation unless the story spells it out. Plain, simple English. "
        "Refer to stories by what they are about, never by their [id] or the labels in brackets. If the paper doesn't cover the question, say so "
        "in one sentence, set in_paper=false, and point to the closest stories it does have. Never end with an offer or a "
        "question to the reader. For 'why does this matter "
        "to me' questions, connect the story to the reader's city and interests only where the story supports it.\n\n"
        f"TODAY'S PAPER ({len(stories)} stories; the most relevant ones include full article text):\n\n"
        + _context(stories, focus, paper["lead_id"]))
    opened = next((s for s in stories if s["id"] == body.story_id), None)
    if opened:  # asked from a story card: "this"/"it" means that story
        system += (f"\n\nThe reader is asking from the story “{opened['headline']}” [{opened['id']}]. Words like "
                   "'this' or 'it' refer to that story: answer about it alone and cite it, unless they clearly ask "
                   "about something else.")
    messages = [{"role": "system", "content": system}]
    messages += [{"role": t.role, "content": t.content} for t in body.history[-6:]]
    messages.append({"role": "user", "content": body.question})

    t0 = time.perf_counter()
    out: AnswerOut = await get_llm().json(messages, schema=AnswerOut, reasoning_effort="minimal")
    by_id = {s["id"]: s for s in stories}
    used = [i for i in dict.fromkeys(out.story_ids) if i in by_id][: 4 if out.in_paper else 2]
    if out.in_paper and not used:
        used = focus[:2]
    if not user.get("persona"):  # asking about a story is a reading signal (sample readers stay unchanged)
        learn.record_events(user, [learn.EventIn(type="ask", article_id=i, edition_id=row["id"]) for i in used[:2]])
    return {
        "answer": out.answer.strip(),
        "in_paper": out.in_paper,
        "sources": [{"id": i, "headline": by_id[i]["headline"], "source": by_id[i]["source"], "url": by_id[i]["url"]} for i in used],
        "follow_ups": [f.strip() for f in out.follow_ups if f.strip() and not OFFER.match(f.strip())][:3],
        "route": {**route_info, "focus": focus, "answer_ms": round((time.perf_counter() - t0) * 1000)},
    }



# ---------- "Search the web" (SWS): when the paper doesn't cover the question ----------

class WebAnswerOut(BaseModel):
    answer: str = Field(description="Plain-English answer using only the numbered web results. Short paragraphs, or "
                                    "'- ' bullets on their own lines; **bold** allowed. Max ~150 words.")
    result_ids: list[int] = Field(description="numbers of the results the answer actually uses")
    found: bool = Field(description="false when the results don't answer the question")


async def ask_web(user: dict, body: AskIn) -> dict:
    """Answer from a fresh news search (Tavily; Google News when Tavily is off or over budget), labelled as web."""
    from app.parhlo.ingest import fetch_all
    from app.parhlo.sws import gnews, instant, tavily

    use_tavily = instant.check(user)
    results = await tavily.search(body.question, max_results=6, days=7) if use_tavily else []
    via = "web search"
    if not results:
        items, _ = await fetch_all([gnews.search_feed(body.question, days=7)])
        results, via = items[:6], "Google News"
    instant.record(user, "ask", body.question[:200], use_tavily, len(results), 0)
    if not results:
        return {"answer": "I couldn't find recent news about this on the web.", "in_paper": False, "found": False,
                "sources": [], "follow_ups": [], "from_web": True, "via": via}
    context = "\n\n".join(
        f"[{n}] {r['title']} ({r['source']}"
        f"{', ' + r['published'].strftime('%d %b %Y') if r.get('published') else ''})\n{r.get('summary') or ''}"
        for n, r in enumerate(results, 1))
    system = (
        "You answer a reader's news question using ONLY the numbered web search results below. Never invent facts, "
        "numbers, names or quotes, and never expand an abbreviation the results don't spell out. Plain, simple "
        "English. If the results don't answer the question, say so in one sentence and set found=false. Never end "
        "with an offer or a question.\n\nRESULTS:\n\n" + context)
    out: WebAnswerOut = await get_llm().json(
        [{"role": "system", "content": system}, {"role": "user", "content": body.question}],
        schema=WebAnswerOut, reasoning_effort="minimal")
    used = [n for n in dict.fromkeys(out.result_ids) if 1 <= n <= len(results)][:4]
    return {
        "answer": out.answer.strip(), "in_paper": False, "found": out.found, "from_web": True, "via": via,
        "sources": [{"id": n, "headline": results[n - 1]["title"], "source": results[n - 1]["source"],
                     "url": results[n - 1]["url"]} for n in used],
        "follow_ups": [],
    }
