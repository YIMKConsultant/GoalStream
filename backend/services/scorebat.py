"""
Wrapper around the Scorebat Video API (https://www.scorebat.com/video-api/).

Scorebat returns recent match videos — highlights and, for some fixtures,
full/live coverage — as ready-to-embed iframes. These are NOT raw HLS: each
video is a Scorebat player iframe, so the frontend embeds it directly rather
than routing through /api/proxy/stream.

Two feeds:
  * Token-less v3 feed — key-less and CORS-open, but a frozen/legacy sample
    whose embeds often render "video unavailable".
  * Tokened v3 feed — set SCOREBAT_TOKEN (free at scorebat.com/video-api) for a
    fresh feed whose embeds are authorised for your domain. Strongly preferred.
"""
import re
import httpx
from cachetools import TTLCache
from config import settings

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GoalStream/1.0)"}

# Scorebat refreshes continuously; a short cache keeps us well under any limits.
_cache: TTLCache = TTLCache(maxsize=1, ttl=300)  # 5 min

_IFRAME_SRC = re.compile(r"""<iframe[^>]*\ssrc=['"]([^'"]+)['"]""", re.I)


def _feed_url() -> str:
    token = (settings.scorebat_token or "").strip()
    if token:
        return f"https://www.scorebat.com/video-api/v3/feed/?token={token}"
    return "https://www.scorebat.com/video-api/v3/"


async def _get_feed() -> list[dict]:
    cached = _cache.get("feed")
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(_feed_url(), headers=_HEADERS)
        resp.raise_for_status()
        data = resp.json()

    # v3 wraps the list in {"response": [...]}; be tolerant of a bare list too.
    items = data.get("response", data) if isinstance(data, dict) else data
    _cache["feed"] = items or []
    return _cache["feed"]


def _iframe_src(embed: str | None) -> str | None:
    """Pull the bare player URL out of an <iframe> embed blob."""
    if not embed:
        return None
    m = _IFRAME_SRC.search(embed)
    return m.group(1) if m else None


def _to_video(m: dict) -> dict:
    videos = m.get("videos") or []
    first_embed = videos[0].get("embed") if videos else None
    return {
        "title": m.get("title"),
        "competition": m.get("competition"),
        "date": m.get("date"),
        "thumbnail": m.get("thumbnail"),
        "matchview_url": m.get("matchviewUrl"),
        "embed": first_embed,                       # raw iframe HTML
        "embed_url": _iframe_src(first_embed),      # just the player src
        "clips": [
            {
                "id": v.get("id"),
                "title": v.get("title"),
                "embed": v.get("embed"),
                "embed_url": _iframe_src(v.get("embed")),
            }
            for v in videos
        ],
    }


async def get_match_videos(competition: str | None = None, limit: int = 50) -> list[dict]:
    """
    Recent match videos from Scorebat. If `competition` is given, keep only
    matches whose competition name contains it (case-insensitive substring,
    e.g. "Premier League", "Ligue 1", "Champions League").
    """
    feed = await _get_feed()
    out = []
    for m in feed:
        if not (m.get("videos")):
            continue
        if competition and competition.lower() not in (m.get("competition") or "").lower():
            continue
        out.append(_to_video(m))
    return out[:limit]
