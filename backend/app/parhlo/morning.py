"""Morning box: weather + air quality (smog alert) for the reader's city, PKR rates, cricket headline.

All sources are free and keyless (Open-Meteo, open.er-api.com). Each part fails independently.
"""

import asyncio
import time

import httpx

from app.core.database import db

WMO = {0: "Clear sky", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog / smog", 48: "Freezing fog",
       51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
       71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers", 81: "Rain showers", 82: "Violent showers",
       95: "Thunderstorm", 96: "Thunderstorm, hail", 99: "Thunderstorm, hail"}


def aqi_band(aqi: float | None) -> dict:
    if aqi is None:
        return {"label": "Unknown", "level": 0, "advice": None}
    bands = [(50, "Good", None), (100, "Moderate", "Fine for most people."),
             (150, "Unhealthy for sensitive groups", "Sensitive groups should limit time outdoors."),
             (200, "Unhealthy", "Smog alert: wear a mask outdoors and keep windows closed."),
             (300, "Very unhealthy", "Smog alert: avoid outdoor activity."),
             (10_000, "Hazardous", "Hazardous smog: stay indoors.")]
    for level, (limit, label, advice) in enumerate(bands):
        if aqi <= limit:
            return {"label": label, "level": level, "advice": advice}
    return {"label": "Hazardous", "level": 5, "advice": "Stay indoors."}


async def weather(client: httpx.AsyncClient, lat: float, lon: float) -> dict | None:
    r = await client.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 1,
        "current": "temperature_2m,weather_code,relative_humidity_2m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max"})
    d = r.json()
    cur, day = d["current"], d["daily"]
    return {"temp": round(cur["temperature_2m"]), "condition": WMO.get(cur["weather_code"], "—"),
            "humidity": cur["relative_humidity_2m"], "high": round(day["temperature_2m_max"][0]),
            "low": round(day["temperature_2m_min"][0]), "rain_chance": day["precipitation_probability_max"][0]}


async def air(client: httpx.AsyncClient, lat: float, lon: float) -> dict | None:
    r = await client.get("https://air-quality-api.open-meteo.com/v1/air-quality",
                         params={"latitude": lat, "longitude": lon, "current": "us_aqi,pm2_5"})
    cur = r.json()["current"]
    return {"aqi": round(cur["us_aqi"]) if cur.get("us_aqi") is not None else None,
            "pm2_5": cur.get("pm2_5"), **aqi_band(cur.get("us_aqi"))}


async def rates(client: httpx.AsyncClient) -> dict | None:
    d = (await client.get("https://open.er-api.com/v6/latest/USD")).json()
    pkr = d["rates"]["PKR"]
    out = {"USD": round(pkr, 2)}
    for cur in ("EUR", "GBP", "SAR", "AED"):  # remittance currencies
        out[cur] = round(pkr / d["rates"][cur], 2)
    return {"pkr": out, "updated": d.get("time_last_update_utc")}


def cricket_headline() -> dict | None:
    with db() as conn:
        return conn.execute(
            """select id, title, source, url from articles where 'cricket' = any(topics)
               and published_at > now() - interval '24 hours' order by published_at desc limit 1""").fetchone()


async def _retry(make, attempts: int = 3):
    """Open-Meteo fails intermittently (about 1 call in 2 at times): retry with a short backoff."""
    for i in range(attempts):
        try:
            return await make()
        except Exception:
            if i == attempts - 1:
                return None
            await asyncio.sleep(0.4 * (i + 1))


_CACHE: dict[str, tuple[float, dict]] = {}
CACHE_S = 20 * 60  # weather, air and rates are the same for everyone in a city


async def morning_box(city: str, lat: float, lon: float) -> dict:
    key = f"{city}:{round(lat, 2)}:{round(lon, 2)}"
    hit = _CACHE.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_S:
        return hit[1]
    box = await _morning_box(city, lat, lon)
    if box["weather"] and box["rates"]:  # don't cache a partial box
        _CACHE[key] = (time.monotonic(), box)
    return box


async def _morning_box(city: str, lat: float, lon: float) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        w, a, r = await asyncio.gather(_retry(lambda: weather(client, lat, lon)), _retry(lambda: air(client, lat, lon)),
                                       _retry(lambda: rates(client)))
    try:
        cricket = cricket_headline()
    except Exception:
        cricket = None
    return {"city": city, "weather": w, "air": a, "rates": r, "cricket": cricket,
            "smog_alert": bool(a and a.get("level", 0) >= 3)}
