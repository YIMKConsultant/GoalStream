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
import contextlib
from urllib.parse import urlparse

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

# Bound concurrent liveness probes: firing 100+ TLS handshakes at once thrashes
# sockets and makes everything slower. ~48 in flight keeps it fast and stable.
_probe_sem = asyncio.Semaphore(48)


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
    # Confirmed present + carrying live football in the free catalog.
    "sport tv", "setanta", "goltv", "match!", "okko futbol",
    "tyc sports", "sport1", "sport 1",
    # Carriers for the Saudi / MLS / African competitions.
    "canal+ sport", "espn deportes", "arryadia",
]

# Sports channels that are emphatically NOT going to show a football match.
# The country fallback below sweeps in every sports channel from a competition's
# country, which is how "Where to watch Eredivisie" ended up offering FightBox
# and Fast&FunBox. Verified against the live catalog: these 28 substrings remove
# only golf/tennis/cricket/darts/poker/combat feeds, and leave football's
# "Sportitalia" while dropping "Sportitalia Motori".
_NON_FOOTBALL = [
    "fight", "funbox", "wwe", "ufc", "mma", "boxing", "combate", "poker",
    "motor", "golf", "tennis", "darts", "snooker", "fishing", "wrestl",
    "nascar", "billiard", "cricket", "rugby", "introuble", "chess",
]


def _is_football(name: str) -> bool:
    lowered = name.lower()
    return not any(k in lowered for k in _NON_FOOTBALL)


# ── Geo-block memory ────────────────────────────────────────────────────────
#
# A liveness check fetches the master playlist, which many broadcasters serve
# worldwide even when the video itself is territorially licensed. Esport3 (the
# Catalan public broadcaster) is the clean example: master.m3u8 returns 200
# everywhere, but during rights-restricted programming the playlist switches to
# `geo-*.ts` segments that 403 outside Spain. The channel looks alive, then dies
# the moment you press play.
#
# We can't afford to walk master -> variant -> segment for every channel on
# every sweep. Instead the proxy tells us when a host actually refused a
# segment, and we drop that host from listings for a while.
_blocked_hosts: TTLCache = TTLCache(maxsize=256, ttl=1800)   # 30 min


def note_blocked_host(url: str) -> None:
    """Called by the proxy when upstream refuses us (403/451)."""
    with contextlib.suppress(Exception):
        _blocked_hosts[urlparse(url).hostname or ""] = True


def is_blocked_host(url: str) -> bool:
    with contextlib.suppress(Exception):
        return (urlparse(url).hostname or "") in _blocked_hosts
    return False


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
    # Added competitions. Some names below match nothing in today's catalog
    # (SSC, SuperSport, TUDN are paywalled) — they cost nothing and start
    # working the day iptv-org picks those broadcasters up. Substrings must stay
    # distinctive: "on sport" was dropped because it also matches
    # "Cytavis-ion Sport-s" and "Multivis-ion Sport-s".
    "SPL":  {"countries": {"SA"},    "names": ["ssc", "saudi", "thmanyah", "bein"]},
    "MLS":  {"countries": {"US", "CA"}, "names": ["mls", "tudn", "espn deportes", "fox sports"]},
    "CAFP": {"countries": {"EG", "MA", "DZ", "TN", "NG", "ZA", "SN", "CM"},
             "names": ["canal+ sport", "supersport", "bein", "arryadia", "on time sport"]},
    "CAFW": {"countries": {"EG", "MA", "DZ", "TN", "NG", "ZA", "SN", "CM"},
             "names": ["canal+ sport", "supersport", "arryadia"]},
    "WWC":  {"countries": set(),     "names": []},                      # broadly carried
    # Brasileirão shows up in the free-tier fixture feed most days, so it needs
    # carriers too. Premiere FC / SporTV are the pay broadcasters (present but
    # offline in the free catalog); CazeTV and ESPN Brasil actually serve.
    # "n sports" is deliberately absent: it also matches "Bahrai-n Sports",
    # "Multivisio-n Sports" and "More Tha-n Sports". Keep substrings distinctive.
    "BSA":  {"countries": {"BR"},    "names": ["cazetv", "premiere fc", "sportv",
                                               "band sports", "ge fast"]},
}


_featured_cache: TTLCache = TTLCache(maxsize=1, ttl=900)  # 15 min


async def get_playing_channels() -> list[dict]:
    """
    Sports channels that are actually serving a stream right now — bounded to
    the known football broadcasters (so we don't liveness-check all ~450) and
    liveness-checked concurrently. Cached 5 min. Powers the "Featured" page.
    """
    cached = _featured_cache.get("playing")
    if cached is not None:
        return cached

    chans = [
        c for c in await get_sports_channels()
        if any(k in c["name"].lower() for k in _GLOBAL_FOOTBALL) and _is_football(c["name"])
    ]
    statuses = await asyncio.gather(*[
        check_stream_alive(c["url"], c.get("referrer"), c.get("user_agent"))
        for c in chans
    ])
    alive = [
        {**c, "alive": True, "status": s["status"]}
        for c, s in zip(chans, statuses) if s["alive"]
    ]
    alive.sort(key=lambda c: c["name"])
    _featured_cache["playing"] = alive
    return alive


async def get_channels_for_league_ids(
    channel_ids: list[str], only_alive: bool = True
) -> list[dict]:
    """
    Resolve an explicit, ordered list of channel ids (an AI-built league map)
    to live channels. Order is preserved — the map is already ranked — so this
    skips the keyword heuristic entirely.
    """
    catalog = {c["id"]: c for c in await get_sports_channels()}
    candidates = [catalog[cid] for cid in channel_ids if cid in catalog]
    if not candidates:
        return []

    statuses = await asyncio.gather(*[
        check_stream_alive(c["url"], c.get("referrer"), c.get("user_agent"))
        for c in candidates
    ])
    tagged = [
        {**c, "alive": s["alive"], "status": s["status"], "match_reason": "ai_match"}
        for c, s in zip(candidates, statuses)
    ]
    tagged.sort(key=lambda c: not c["alive"])   # working ones first, rank preserved within
    return [c for c in tagged if c["alive"]] if only_alive else tagged


async def get_channels_for_league(
    league_code: str, limit: int = 32, only_alive: bool = True
) -> list[dict]:
    """
    Best-effort list of channels that may be broadcasting the given league,
    league-specific broadcasters first, then that country, then global feeds.

    Each candidate is liveness-checked (concurrently, cached 2 min) and tagged
    with an `alive` flag — most premium sports feeds in the free catalog are
    geo-locked or offline (403), so by default only channels that are actually
    serving right now are returned.
    """
    hints = _LEAGUE_HINTS.get(league_code.upper(), {})
    league_names = hints.get("names", [])
    countries = hints.get("countries", set())

    scored = []
    for ch in await get_sports_channels():
        name = ch["name"].lower()
        if not _is_football(ch["name"]):
            continue                                       # golf/darts/combat — never football

        named = bool(league_names) and any(k in name for k in league_names)
        in_country = bool(countries) and ch.get("country") in countries

        # Name AND country beats name alone: "sport tv" matches both Portugal's
        # Sport TV (who actually hold Primeira Liga) and Moldova's "We Sport TV".
        # Without the country tiebreak the wrong one can end up first and be
        # what auto-plays.
        if named and in_country:
            priority = 0                                   # the league's own broadcaster
        elif named:
            priority = 1                                   # right name, wrong country
        elif in_country:
            priority = 2                                   # other sports channel from there
        elif any(k in name for k in _GLOBAL_FOOTBALL):
            priority = 3                                   # generic football broadcaster
        else:
            continue
        scored.append((priority, ch["name"], ch))

    # Surface WHY each channel is here. Without this the UI can't distinguish
    # Portugal's Sport TV (the actual Primeira Liga rights holder) from Arena
    # Sport Slovakia, which is only here because it shows football in general —
    # and presenting the second as if it were the first is misleading.
    _reason = {
        0: "league_broadcaster",
        1: "broadcaster_elsewhere",
        2: "same_country",
        3: "general_football",
    }

    scored.sort(key=lambda t: (t[0], t[1]))
    candidates = [(prio, ch) for prio, _, ch in scored[:limit]]

    # Verify each candidate is actually serving before offering it to the player.
    statuses = await asyncio.gather(*[
        check_stream_alive(c["url"], c.get("referrer"), c.get("user_agent"))
        for _, c in candidates
    ])
    tagged = [
        {**c, "alive": s["alive"], "status": s["status"], "match_reason": _reason[prio]}
        for (prio, c), s in zip(candidates, statuses)
    ]
    # Keep broadcaster priority, but float the ones that actually work to the top.
    tagged.sort(key=lambda c: not c["alive"])
    return [c for c in tagged if c["alive"]] if only_alive else tagged


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

    async def _probe() -> dict:
        # Stream the response so we can validate an HLS playlist by its first
        # bytes WITHOUT downloading a whole (endless) live segment — reading
        # resp.text on a raw stream would block until the read timeout.
        async with httpx.AsyncClient(timeout=4, follow_redirects=True) as client:
            async with client.stream("GET", url, headers=headers) as resp:
                status = resp.status_code
                is_m3u8 = ("mpegurl" in resp.headers.get("content-type", "")
                           or url.split("?")[0].endswith(".m3u8"))
                is_hls = True
                if status == 200 and is_m3u8:
                    head = b""
                    async for chunk in resp.aiter_bytes():
                        head += chunk
                        if len(head) >= 300:
                            break
                    is_hls = b"#EXTM3U" in head[:300]
        return {
            "alive": status == 200 and (is_hls or not is_m3u8),
            "status": status,
            "error": None,
        }

    try:
        # Hard ceiling per check: a bad host can chain several redirect hops,
        # each with its own timeout, so bound the whole probe — otherwise
        # gather() over many channels waits on the single slowest one.
        async with _probe_sem:
            result = await asyncio.wait_for(_probe(), timeout=4)
    except Exception as e:
        result = {"alive": False, "status": 0,
                  "error": "Timeout" if isinstance(e, asyncio.TimeoutError) else type(e).__name__}

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
