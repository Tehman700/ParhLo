"""Topic taxonomy shown in onboarding and used to tag articles (by embedding similarity)."""

TOPICS: dict[str, dict] = {
    "pakistan":      {"label": "Pakistan",          "group": "News",     "desc": "Pakistan national news, government, provinces, Islamabad Lahore Karachi"},
    "politics":      {"label": "Politics",          "group": "News",     "desc": "politics, elections, parliament, political parties, policy and government decisions"},
    "world":         {"label": "World",             "group": "News",     "desc": "international affairs, foreign policy, diplomacy, conflicts and global events"},
    "business":      {"label": "Business",          "group": "Money",    "desc": "companies, corporate news, industry, trade, deals and earnings"},
    "economy":       {"label": "Economy & Markets", "group": "Money",    "desc": "economy, inflation, interest rates, IMF, rupee, stock market, PSX, budget, taxes"},
    "technology":    {"label": "Technology",        "group": "Tech",     "desc": "technology, gadgets, smartphones, software, internet, cybersecurity, big tech"},
    "ai":            {"label": "Artificial Intelligence", "group": "Tech", "desc": "artificial intelligence, machine learning, LLMs, OpenAI, chatbots, AI regulation and research"},
    "startups":      {"label": "Startups",          "group": "Tech",     "desc": "startups, venture capital, funding rounds, founders, entrepreneurship"},
    "science":       {"label": "Science & Space",   "group": "Ideas",    "desc": "science research, space exploration, physics, biology, discoveries"},
    "health":        {"label": "Health",            "group": "Life",     "desc": "health, medicine, diseases, hospitals, fitness, mental health, nutrition"},
    "climate":       {"label": "Climate & Environment", "group": "Life",  "desc": "climate change, environment, smog, air pollution, floods, weather, energy transition"},
    "cricket":       {"label": "Cricket",           "group": "Sports",   "desc": "cricket matches, PCB, Pakistan cricket team, PSL, ICC, test ODI T20"},
    "football":      {"label": "Football",          "group": "Sports",   "desc": "football soccer, Premier League, Champions League, FIFA, transfers"},
    "motorsport":    {"label": "Formula 1 & Motorsport", "group": "Sports", "desc": "Formula 1 F1 grand prix racing, drivers, teams, motorsport"},
    "entertainment": {"label": "Entertainment",     "group": "Culture",  "desc": "movies, films, TV dramas, music, celebrities, streaming, showbiz"},
    "culture":       {"label": "Culture & Books",   "group": "Culture",  "desc": "arts, books, literature, culture, history, food and travel"},
    "education":     {"label": "Education & Careers", "group": "Life",   "desc": "education, universities, students, exams, jobs, careers, skills"},
}


def topic_text(slug: str) -> str:
    t = TOPICS[slug]
    return f"{t['label']}: {t['desc']}"
