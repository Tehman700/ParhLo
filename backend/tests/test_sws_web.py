"""Interest-change web search: images, publisher links, Tavily results, rich summaries, the per-interest cap."""

import json

import numpy as np

from app.parhlo.rank import mmr
from app.parhlo.sws import enrich, tavily, write


def test_share_image_prefers_og_and_skips_logos():
    html = ('<meta name="twitter:image" content="https://cdn.x/tw.jpg">'
            '<meta content="https://cdn.x/og.jpg" property="og:image">')
    assert enrich.share_image(html) == "https://cdn.x/og.jpg"
    assert enrich.share_image('<meta property="og:image" content="https://x/site-logo.png">'
                              '<meta name="twitter:image" content="/img/story.jpg">', "https://news.example/a/b") \
        == "https://news.example/img/story.jpg"                      # logo skipped, relative made absolute
    assert enrich.share_image("<html>no meta</html>") is None


def test_google_news_ids_and_decoder_response():
    assert enrich.gn_id("https://news.google.com/rss/articles/CBMiabc?oc=5") == "CBMiabc"
    assert enrich.gn_id("https://www.dawn.com/news/1") is None
    row = ["wrb.fr", "Fbv4je", json.dumps(["garturlres", "https://www.monitor.co.ug/story", 1]), None, None, "0"]
    text = ")]}'\n\n" + json.dumps([row, ["di", 42]])
    assert enrich.parse_batchexecute(text) == [("0", "https://www.monitor.co.ug/story")]


def test_tavily_news_results_carry_text_and_image():
    data = {"results": [
        {"url": "https://www.monitor.co.ug/x", "title": "Opposition rally in Kampala draws thousands",
         "content": "Short.", "raw_content": "Full article. " * 60, "images": ["https://img.x/1.jpg"]},
        {"url": "https://ntv.co.ug/y", "title": "Former minister says transition already happened",
         "content": "Short.", "raw_content": "", "images": []},
    ]}
    a, b = tavily.news_items(data, "Uganda Politics")
    assert a["term"] == "Uganda Politics" and a["link"] == a["url"] and a["image"] == "https://img.x/1.jpg"
    assert len(a["content"]) > 400 and a["origin"] == "web"
    assert b["content"] is None and b["image"] is None              # left for Extract / the page fetch
    assert tavily.NEWS_QUERY.format(term="Cat News") == "I want news related to Cat News"


def test_one_interest_cannot_flood_personal_picks():
    def story(i, match):
        v = np.zeros(4, np.float32)
        v[i % 4] = 1.0
        return {"id": i, "score": 1 - i / 100, "match": match, "embedding": v}
    pool = [story(i, "Cat News") for i in range(6)] + [story(10 + i, "Uganda") for i in range(3)]
    picks = mmr(pool, 6, cap=3)
    assert sum(p["match"] == "Cat News" for p in picks) == 3 and len(picks) == 6


class FakeLLM:
    def __init__(self):
        self.models = []

    async def json(self, messages, schema=None, model=None, **kw):
        self.models.append(model)
        return schema.model_validate({"summary": "Uganda's opposition held a large rally. " * 3,
                                      "points": ["Thousands attended", "Police were present", ""]})


async def test_rich_summaries_use_the_stronger_model_and_skip_items_without_text(monkeypatch):
    llm = FakeLLM()
    monkeypatch.setattr(write, "get_llm", lambda: llm)
    items = [{"url": "a", "title": "Rally", "content": "Full text " * 100}, {"url": "b", "title": "No text", "content": None}]
    assert await write.write_rich(items) == 1
    assert items[0]["ai_points"]["points"] == ["Thousands attended", "Police were present"]
    assert items[0]["ai_points"]["grounded_in"] == "full article" and items[0]["ai_points"]["check"] is None
    assert llm.models == ["openai/gpt-5-mini"] and "ai_summary" not in items[1]
