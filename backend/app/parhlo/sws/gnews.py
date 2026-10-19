"""SWS source: Google News — top stories of every English country edition, and English searches for the rest.

Feeds come back in the same RSS shape as our curated feeds, so ingest.fetch_all() / parse_feed() read them as is;
the feed dict carries origin="gnews" and the country, which parse_feed copies onto every item.
"""

from app.parhlo.sources import google_news_feed

# English country editions (hl=en-XX). Verified live on 2026-10-19: each returned ~38 top stories (ID: 22).
# Other countries only have native-language editions (switched on later, with English summaries).
EDITIONS: dict[str, str] = {
    "US": "United States", "GB": "United Kingdom", "IN": "India", "PK": "Pakistan", "AU": "Australia",
    "CA": "Canada", "NZ": "New Zealand", "IE": "Ireland", "ZA": "South Africa", "NG": "Nigeria", "KE": "Kenya",
    "UG": "Uganda", "TZ": "Tanzania", "GH": "Ghana", "ZW": "Zimbabwe", "NA": "Namibia", "BW": "Botswana",
    "ET": "Ethiopia", "SG": "Singapore", "MY": "Malaysia", "PH": "Philippines", "IL": "Israel", "ID": "Indonesia",
}

# Native-language editions (country code → hl, ceid, language, country). Verified live on 2026-10-19 (26–38
# top stories each; ur-PK and fa-IR don't exist). Their headlines are translated to English when kept.
NATIVE_EDITIONS: dict[str, tuple[str, str, str, str]] = {
    "FR": ("fr", "FR:fr", "fr", "France"), "DE": ("de", "DE:de", "de", "Germany"), "ES": ("es", "ES:es", "es", "Spain"),
    "IT": ("it", "IT:it", "it", "Italy"), "BR": ("pt-BR", "BR:pt-419", "pt", "Brazil"),
    "JP": ("ja", "JP:ja", "ja", "Japan"), "KR": ("ko", "KR:ko", "ko", "South Korea"),
    "CN": ("zh-CN", "CN:zh-Hans", "zh", "China"), "TW": ("zh-TW", "TW:zh-Hant", "zh", "Taiwan"),
    "RU": ("ru", "RU:ru", "ru", "Russia"), "TR": ("tr", "TR:tr", "tr", "Turkey"),
    "SA": ("ar", "SA:ar", "ar", "Saudi Arabia"), "EG": ("ar", "EG:ar", "ar", "Egypt"),
    "AE": ("ar", "AE:ar", "ar", "United Arab Emirates"), "MX": ("es-419", "MX:es-419", "es", "Mexico"),
    "AR": ("es-419", "AR:es-419", "es", "Argentina"), "ID": ("id", "ID:id", "id", "Indonesia"),
    "TH": ("th", "TH:th", "th", "Thailand"), "VN": ("vi", "VN:vi", "vi", "Vietnam"),
    "NL": ("nl", "NL:nl", "nl", "Netherlands"), "PL": ("pl", "PL:pl", "pl", "Poland"),
    "UA": ("uk", "UA:uk", "uk", "Ukraine"), "IL": ("he", "IL:he", "he", "Israel"),
    "BD": ("bn", "BD:bn", "bn", "Bangladesh"), "IN": ("hi", "IN:hi", "hi", "India"),
}

# Countries without an English edition: covered by an English Google News search for the country's name.
COUNTRIES: list[str] = [
    # Asia
    "Afghanistan", "Bangladesh", "Bhutan", "Brunei", "Cambodia", "China", "Hong Kong", "Japan", "Kazakhstan",
    "Kyrgyzstan", "Laos", "Maldives", "Mongolia", "Myanmar", "Nepal", "North Korea", "South Korea", "Sri Lanka",
    "Taiwan", "Tajikistan", "Thailand", "Timor-Leste", "Turkmenistan", "Uzbekistan", "Vietnam",
    # Middle East
    "Bahrain", "Iran", "Iraq", "Jordan", "Kuwait", "Lebanon", "Oman", "Palestine", "Qatar", "Saudi Arabia",
    "Syria", "Turkey", "United Arab Emirates", "Yemen",
    # Africa
    "Algeria", "Angola", "Benin", "Burkina Faso", "Burundi", "Cameroon", "Cape Verde", "Central African Republic",
    "Chad", "Comoros", "Democratic Republic of the Congo", "Republic of the Congo", "Djibouti", "Egypt",
    "Equatorial Guinea", "Eritrea", "Eswatini", "Gabon", "Gambia", "Guinea", "Guinea-Bissau", "Ivory Coast",
    "Lesotho", "Liberia", "Libya", "Madagascar", "Malawi", "Mali", "Mauritania", "Mauritius", "Morocco",
    "Mozambique", "Niger", "Rwanda", "Senegal", "Seychelles", "Sierra Leone", "Somalia", "South Sudan", "Sudan",
    "Togo", "Tunisia", "Zambia",
    # Europe
    "Albania", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium", "Bosnia and Herzegovina", "Bulgaria",
    "Croatia", "Cyprus", "Czech Republic", "Denmark", "Estonia", "Finland", "France", "Georgia", "Germany",
    "Greece", "Hungary", "Iceland", "Italy", "Kosovo", "Latvia", "Lithuania", "Luxembourg", "Malta", "Moldova",
    "Montenegro", "Netherlands", "North Macedonia", "Norway", "Poland", "Portugal", "Romania", "Russia",
    "Serbia", "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland", "Ukraine",
    # Americas
    "Argentina", "Bahamas", "Barbados", "Belize", "Bolivia", "Brazil", "Chile", "Colombia", "Costa Rica", "Cuba",
    "Dominican Republic", "Ecuador", "El Salvador", "Guatemala", "Guyana", "Haiti", "Honduras", "Jamaica",
    "Mexico", "Nicaragua", "Panama", "Paraguay", "Peru", "Puerto Rico", "Suriname", "Trinidad and Tobago",
    "Uruguay", "Venezuela",
    # Oceania
    "Fiji", "Papua New Guinea", "Samoa", "Solomon Islands", "Tonga", "Vanuatu",
]


def _region(country: str) -> str:
    return "pakistan" if country == "Pakistan" else "global"


def edition_feed(cc: str) -> dict:
    """Top stories of one English country edition, e.g. edition_feed("UG") → Uganda's top stories."""
    country = EDITIONS[cc]
    return {"name": "Google News", "url": f"https://news.google.com/rss?hl=en-{cc}&gl={cc}&ceid={cc}:en",
            "region": _region(country), "topics": [], "origin": "gnews", "country": country, "language": "en"}


def native_edition_feed(cc: str) -> dict:
    """Top stories of a native-language edition, e.g. native_edition_feed("FR") → France's top stories (French)."""
    hl, ceid, lang, country = NATIVE_EDITIONS[cc]
    return {"name": "Google News", "url": f"https://news.google.com/rss?hl={hl}&gl={cc}&ceid={ceid}",
            "region": _region(country), "topics": [], "origin": "gnews", "country": country, "language": lang}


def country_search_feed(country: str) -> dict:
    """English news about a country without its own English edition (searched in the US English edition)."""
    feed = google_news_feed(f'"{country}"', edition="US")
    return {**feed, "region": _region(country), "country": country, "language": "en"}


def search_feed(query: str, days: int = 1) -> dict:
    """English news for any query (a name a reader follows, a question in Ask…), worldwide English edition."""
    return {**google_news_feed(query, edition="US", days=days), "language": "en"}
