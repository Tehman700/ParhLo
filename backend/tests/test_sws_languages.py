"""SWS languages: GDELT translated files, native Google News editions, English headlines for kept stories."""

from app.parhlo.sws import gdelt, gnews, planner, translate
from app.parhlo.sws.languages import name, to2


def translated_line(title="Путин предложил провести саммит с Трампом и Си", srclc="rus"):
    cols = [""] * 27
    cols[gdelt.DATE], cols[gdelt.COLLECTION], cols[gdelt.SOURCE] = "20261019081500", "1", "ria.ru"
    cols[gdelt.URL] = "https://ria.ru/20261019/x.html"
    cols[gdelt.LOCATIONS] = "1#Russia#RS#RS##60#100#RS#5"
    cols[gdelt.TRANSLATION] = f"srclc:{srclc};eng:GT-{srclc.upper()} 1.0"
    cols[gdelt.EXTRAS] = f"<PAGE_TITLE>{title}</PAGE_TITLE>"
    return "\t".join(cols)


def test_translated_gkg_reads_each_articles_language():
    [item] = gdelt.parse_gkg(translated_line(), language=None)
    assert item["language"] == "ru" and item["country"] == "Russia"
    assert item["title"].startswith("Путин")                    # kept in the original; translated only if kept
    assert gdelt.parse_gkg(translated_line(title="Короткий"), language=None) == []   # too short to be a headline


def test_language_codes():
    assert to2("zho") == "zh" and to2("xyz") == "xyz" and to2(None) is None
    assert name("ru") == "Russian" and name("xx") is None


def test_native_edition_feed_and_planner_kind():
    feed = gnews.native_edition_feed("FR")
    assert feed["url"] == "https://news.google.com/rss?hl=fr&gl=FR&ceid=FR:fr"
    assert feed["language"] == "fr" and feed["country"] == "France"
    assert planner.feed_for({"id": 9, "kind": "native", "query": "BR"})["url"].endswith("ceid=BR:pt-419")
    assert planner.adapt("native", 120, new=0) == 240


class FakeLLM:
    def __init__(self, titles):
        self.titles, self.prompts = titles, []

    async def json(self, messages, schema=None, **kw):
        self.prompts.append(messages[0]["content"])
        return schema.model_validate({"titles": self.titles})


async def test_kept_foreign_headlines_become_english(monkeypatch):
    items = [{"title": "Путин предложил саммит", "language": "ru"}, {"title": "Already English", "language": "en"},
             {"title": "Le gouvernement annonce un budget", "language": "fr"}]
    llm = FakeLLM(["Putin proposes a summit", "The government announces a budget"])
    monkeypatch.setattr(translate, "get_llm", lambda: llm)
    assert await translate.english_titles(items) == 2
    assert [i["title"] for i in items] == ["Putin proposes a summit", "Already English", "The government announces a budget"]
    assert "1. [Russian] Путин" in llm.prompts[0] and "2. [French]" in llm.prompts[0]


async def test_translation_keeps_originals_when_the_count_is_wrong(monkeypatch):
    items = [{"title": "Путин", "language": "ru"}, {"title": "Le budget", "language": "fr"}]
    monkeypatch.setattr(translate, "get_llm", lambda: FakeLLM(["only one"]))
    assert await translate.english_titles(items) == 0 and items[0]["title"] == "Путин"
