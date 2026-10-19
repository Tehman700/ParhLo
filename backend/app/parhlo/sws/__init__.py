"""SWS (Smart Web Search): worldwide news, all day, from free sources, through the same pipeline as RSS.

Sources (each returns items in the parse_feed() shape, so ingest.store_items() stores them like any other story):
  gdelt   — GDELT's 15-minute files: every article GDELT saw worldwide (title, outlet, image, places mentioned)
  gnews   — Google News: top stories of every English country edition + English searches for other countries
  tavily  — Tavily web search, on demand (a reader follows something new, or Ask needs news that isn't in the paper)
"""
