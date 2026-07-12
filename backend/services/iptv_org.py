"""
Wrapper around the iptv-org public API (https://github.com/iptv-org/api).

These are free, key-less, CORS-open static JSON files published on GitHub
Pages and refreshed daily. We join streams.json -> channels.json and expose
the live *sports TV channels* (beIN, ESPN, Sport TV, ...) as a browse catalog.

NOTE: iptv-org provides live TV channels, not per-match streams. Many channels
are geo-blocked or intermittently offline, and most require the exact
referrer / user_agent carried in streams.json — which is why the playable URL
is served through /api/proxy/stream (see routers/proxy.py).
"""
import asyncio
import httpx
from cachetools import TTLCache

API = "https://iptv-org.github.io/api"

# Channels/streams change slowly (daily rebuild) — cache for an hour.
_cache: TTLCache = TTLCache(maxsize=8, ttl=3600)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GoalStream/1.0)"}

# Browser-like UA for liveness checks (some CDNs 403 non-browser agents).
_CHECK_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

# Stream liveness is volatile — cache results for 2 minutes.
_status_cache: TTLCache = TTLCache(maxsize=512, ttl=120)


async def _get_json(name: str) -> list:
    """Fetch and cache one of the iptv-org JSON files (e.g. 'streams')."""
    cached = _cache.get(name)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get(f"{API}/{name}.json", headers=_HEADERS)
        resp.raise_for_status()
        data = resp.json()

    _cache[name] = data
    return data


async def get_sports_channels() -> list[dict]:
    """
    Return live sports channels that have at least one playable stream.

    Each item: id, name, country, website, url, referrer, user_agent, quality.
    """
    channels, streams = await _get_json("channels"), await _get_json("streams")

    # First stream per channel (streams.json can list several per channel).
    stream_by_channel: dict[str, dict] = {}
    for s in streams:
        cid = s.get("channel")
        if cid and cid not in stream_by_channel and s.get("url"):
            stream_by_channel[cid] = s

    results = []
    for ch in channels:
        if "sports" not in (ch.get("categories") or []):
            continue
        if ch.get("is_nsfw"):
            continue
        stream = stream_by_channel.get(ch["id"])
        if not stream:
            continue  # no playable URL -> skip
        results.append(
            {
                "id": ch["id"],
                "name": ch["name"],
                "country": ch.get("country"),
                "website": ch.get("website"),
                "url": stream["url"],
                "referrer": stream.get("referrer"),
                "user_agent": stream.get("user_agent"),
                "quality": stream.get("quality"),
            }
        )

    results.sort(key=lambda c: c["name"])
    return results


async def get_channel_stream(channel_id: str) -> dict | None:
    """Return the playable stream record for a single channel id, or None."""
    for ch in await get_sports_channels():
        if ch["id"] == channel_id:
            return ch
    return None


# ── League → broadcaster heuristic ──────────────────────────────────────────
#
# iptv-org has NO schedule, so we cannot know which channel is airing a given
# match. Instead we map each competition to the football broadcasters that
# commonly carry it AND actually exist in the free catalog (calibrated against
# the live data — Sky/TNT/SuperSport are paywalled and absent). Results are
# "channels that MAY be showing this league", never a guarantee.

# Broadcaster name-substrings confirmed present in the catalog.
_GLOBAL_FOOTBALL = [
    "bein", "espn", "fox soccer", "fox sports", "premier sports",
    "ziggo sport", "dazn", "star sports", "movistar", "premiere fc",
    "golazo", "arena sport", "digi sport", "sportitalia",
]

# Per-competition: country codes + extra broadcaster name-substrings.
_LEAGUE_HINTS: dict[str, dict] = {
    "WC":  {"countries": set(),      "names": []},                       # World Cup — broadly carried
    "CL":  {"countries": set(),      "names": []},                       # UEFA — broadly carried
    "EL":  {"countries": set(),      "names": []},
    "ECL": {"countries": set(),      "names": []},
    "PL":  {"countries": {"GB", "US"}, "names": ["premier sports", "peacock", "usa network"]},
    "PD":  {"countries": {"ES"},     "names": ["movistar"]},
    "SA":  {"countries": {"IT"},     "names": ["sportitalia", "sport tv"]},
    "BL1": {"countries": {"DE"},     "names": ["sport1"]},
    "FL1": {"countries": {"FR"},     "names": []},
    "DED": {"countries": {"NL"},     "names": ["ziggo sport"]},
    "PPL": {"countries": {"PT"},     "names": ["sport tv"]},
}


async def get_channels_for_league(league_code: str, limit: int = 20) -> list[dict]:
    """
    Best-effort list of channels that may be broadcasting the given league,
    league-specific broadcasters first, then that country, then global feeds.
    """
    hints = _LEAGUE_HINTS.get(league_code.upper(), {})
    league_names = hints.get("names", [])
    countries = hints.get("countries", set())

    scored = []
    for ch in await get_sports_channels():
        name = ch["name"].lower()
        if league_names and any(k in name for k in league_names):
            priority = 0                                   # league-specific broadcaster
        elif countries and ch.get("country") in countries:
            priority = 1                                   # right country
        elif any(k in name for k in _GLOBAL_FOOTBALL):
            priority = 2                                   # generic football broadcaster
        else:
            continue
        scored.append((priority, ch["name"], ch))

    scored.sort(key=lambda t: (t[0], t[1]))
    return [ch for _, _, ch in scored[:limit]]


# ── Stream liveness check ───────────────────────────────────────────────────

async def check_stream_alive(url: str, referrer: str | None = None,
                             user_agent: str | None = None) -> dict:
    """
    Verify a stream is actually serving right now: fetch the URL and confirm a
    200 plus a valid HLS body. Cached 2 min so repeated checks are cheap.
    Returns {"alive": bool, "status": int, "error": str | None}.
    """
    cached = _status_cache.get(url)
    if cached is not None:
        return cached

    headers = {"User-Agent": user_agent or _CHECK_UA}
    if referrer:
        headers["Referer"] = referrer

    result: dict = {"alive": False, "status": 0, "error": None}
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
        is_m3u8 = ("mpegurl" in resp.headers.get("content-type", "")
                   or url.split("?")[0].endswith(".m3u8"))
        is_hls = "#EXTM3U" in resp.text[:300] if is_m3u8 else False
        result = {
            "alive": resp.status_code == 200 and (is_hls or not is_m3u8),
            "status": resp.status_code,
            "error": None,
        }
    except Exception as e:
        result = {"alive": False, "status": 0, "error": type(e).__name__}

    _status_cache[url] = result
    return result


# ── Replays / classic-match channels ────────────────────────────────────────
#
# iptv-org has no on-demand VOD — every stream is a 24/7 linear feed. But some
# channels air classic games, club archives and full-match replays around the
# clock. FIFA+ in particular carries a large archive of past World Cup matches.
_REPLAY_NAME_HINTS = [
    "fifa+", "classic", "goltv", "real madrid tv", "barca tv",
    "premiere clubes", "mutv", "lfc", "chelsea tv", "inter tv",
    "milan tv", "juventus", "legends", "retro",
]

_replay_cache: TTLCache = TTLCache(maxsize=1, ttl=300)


async def get_replay_channels(only_alive: bool = True) -> list[dict]:
    """
    Curated football channels that broadcast replays / classic matches, each
    tagged with a live `alive` flag (checked concurrently, cached 5 min).
    """
    cached = _replay_cache.get("replays")
    if cached is None:
        chans = [
            c for c in await get_sports_channels()
            if any(k in c["name"].lower() for k in _REPLAY_NAME_HINTS)
        ]
        statuses = await asyncio.gather(*[
            check_stream_alive(c["url"], c.get("referrer"), c.get("user_agent"))
            for c in chans
        ])
        cached = [
            {**c, "alive": s["alive"], "status": s["status"]}
            for c, s in zip(chans, statuses)
        ]
        # Alive first, then by name.
        cached.sort(key=lambda c: (not c["alive"], c["name"]))
        _replay_cache["replays"] = cached

    return [c for c in cached if c["alive"]] if only_alive else cached
