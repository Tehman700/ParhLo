"""③ EDIT — the AI editor lays out one reader's paper (JSON), with a deterministic fallback."""

import logging

from pydantic import BaseModel, Field

from app.parhlo.topics import TOPICS
from app.services.llm import get_llm

log = logging.getLogger("parhlo.editor")


class StoryEdit(BaseModel):
    id: int
    headline: str = Field(description="Clear, plain headline, max 12 words, faithful to the summary. No clickbait.")
    why: str = Field(description="Max 14 words, plain English: why this story matches the reader's interests")


class Section(BaseModel):
    name: str = Field(description="Short newspaper section name, e.g. 'Pakistan', 'Tech & AI', 'Sport'")
    story_ids: list[int]


class Thing(BaseModel):
    text: str = Field(description="One key fact from today's paper in plain English, max 20 words")
    story_id: int


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=3, max_length=4)
    answer: int = Field(description="index of the correct option")
    story_id: int


class EditorOut(BaseModel):
    editor_note: str = Field(description="2 short sentences in plain, simple English summarizing today's main stories. "
                                         "No greeting, no 'Good morning', no flowery or dramatic language, no facts not in the input.")
    lead_id: int
    sections: list[Section]
    stories: list[StoryEdit]
    three_things: list[Thing] = Field(min_length=3, max_length=3)
    quiz: list[QuizQuestion] = Field(description="3 questions testing the three things, for tomorrow's recall quiz")


def _story_brief(s: dict) -> str:
    tags = ", ".join(TOPICS[t]["label"] for t in s["topics"] if t in TOPICS)
    reason = "DISCOVERY (outside usual interests)" if s.get("discovery") else f"matches interest: {s.get('match')}"
    return (f"[{s['id']}] {s['title']} — {s['source']} | topics: {tags} | {reason}\n"
            f"    summary: {s['summary']}")


async def edit_paper(user: dict, stories: list[dict], top_topics: list[str], morning: dict) -> dict:
    ids = {s["id"] for s in stories}
    weather = morning.get("weather") or {}
    air = morning.get("air") or {}
    prompt = (
        f"You are the editor of ParhLo, {user['name']}'s personal morning newspaper ({user['city']}).\n"
        f"Reader's strongest interests: {', '.join(top_topics)}.\n"
        f"Today in {user['city']}: {weather.get('temp', '?')}°C, {weather.get('condition', '')}; "
        f"air quality {air.get('aqi', '?')} ({air.get('label', '')}).\n\n"
        "Lay out today's paper from these stories. Rules: pick the most important + most relevant story as lead; "
        "group the rest into 2-5 sections ordered by the reader's interests; every story id appears exactly once "
        "(lead included in a section); headlines and facts must come only from the summaries.\n\n"
        + "\n".join(_story_brief(s) for s in stories))
    try:
        out: EditorOut = await get_llm().json([{"role": "user", "content": prompt}], schema=EditorOut)
        return _validate(out, stories, ids)
    except Exception as e:
        log.warning("editor fell back to deterministic layout: %s", e)
        return fallback_layout(user, stories)


def _validate(out: EditorOut, stories: list[dict], ids: set[int]) -> dict:
    placed: list[int] = []
    sections = []
    for sec in out.sections:
        sids = [i for i in sec.story_ids if i in ids and i not in placed]
        placed += sids
        if sids:
            sections.append({"name": sec.name, "story_ids": sids})
    missing = [s["id"] for s in stories if s["id"] not in placed]
    if missing:
        sections.append({"name": "Also today", "story_ids": missing})
    lead = out.lead_id if out.lead_id in ids else stories[0]["id"]
    edits = {e.id: {"headline": e.headline, "why": e.why} for e in out.stories if e.id in ids}
    return {
        "editor_note": out.editor_note, "lead_id": lead, "sections": sections, "edits": edits,
        "three_things": [t.model_dump() for t in out.three_things if t.story_id in ids],
        "quiz": [q.model_dump() for q in out.quiz if q.story_id in ids and 0 <= q.answer < len(q.options)],
    }


def fallback_layout(user: dict, stories: list[dict]) -> dict:
    by_topic: dict[str, list[int]] = {}
    for s in stories:
        name = TOPICS[s["topics"][0]]["group"] if s["topics"] and s["topics"][0] in TOPICS else "Also today"
        by_topic.setdefault(name, []).append(s["id"])
    return {
        "editor_note": "Here are today's stories, chosen for your interests.",
        "lead_id": stories[0]["id"],
        "sections": [{"name": k, "story_ids": v} for k, v in by_topic.items()],
        "edits": {s["id"]: {"headline": s["title"],
                            "why": "Something new, outside your usual topics" if s.get("discovery") else f"Matches your interest in {s.get('match')}"}
                  for s in stories},
        "three_things": [{"text": s["summary"].split(". ")[0][:160], "story_id": s["id"]} for s in stories[:3]],
        "quiz": [],
    }
