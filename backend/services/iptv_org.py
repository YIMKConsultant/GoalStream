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
import re
from urllib.parse import urlparse

import httpx
from cachetools import TTLCache

from services import rtm, stream_origin

API = "https://iptv-org.github.io/api"

# Channels/streams change slowly (daily rebuild) — cache for an hour.
_cache: TTLCache = TTLCache(maxsize=8, ttl=3600)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GoalStream/1.0)"}

# Browser-like UA for liveness checks (some CDNs 403 non-browser agents).
_CHECK_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

# Stream liveness is volatile — cache results for 2 minutes.
_status_cache: TTLCache = TTLCache(maxsize=512, ttl=120)

# Streams whose master playlist keeps serving while the channel is off air, so a
# master-only check cannot be trusted.
#
# Every RTM stream is in here. RTM's CloudFront distribution returns an
# IDENTICAL canned master for any path under smil:*/ — including paths that do
# not exist — so a 200 on the master says nothing at all about whether the
# channel is on air. Only fetching a variant and finding real segments does.
# Without this the app lists all eight RTM channels as live and hands the viewer
# a black player on six of them.
_VERIFY_VARIANT: set[str] = {c["url"] for c in rtm.catalog()}

# Bound concurrent liveness probes. This number decides how ACCURATE the sweep
# is, not just how fast — and the two are not in tension, which is why it is far
# lower than it looks like it should be.
#
# Each probe is a TLS handshake to a different host, which is CPU work on the
# event loop thread. Past ~16 in flight the loop is saturated, its timers fire
# late, and the per-probe deadline expires on channels that were answering
# perfectly well — they get recorded as offline. Measured over the same 64
# candidates, back to back:
#
#     concurrency  6 -> 32 alive, 23.5s      concurrency 16 -> 30 alive, 17.9s
#     concurrency 12 -> 32 alive, 17.8s      concurrency 24 -> 10 alive, 17.4s
#     concurrency 48 -> 13 alive, 13.0s
#
# The old value of 48 was not buying speed; it was manufacturing false
# "offline" results and hiding two thirds of the working channels.
_probe_sem = asyncio.Semaphore(12)


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


async def _languages_by_channel() -> dict[str, list[str]]:
    """
    Commentary language(s) per channel, as ISO 639-3 codes, from feeds.json.

    A channel can publish several feeds (the same broadcaster in different
    languages); `is_main` marks the one the catalog treats as canonical, so we
    prefer it and fall back to whichever feed we saw first. Coverage is complete
    for the sports catalog — all 414 channels resolve to at least one language.
    """
    feeds = await _get_json("feeds")
    best: dict[str, dict] = {}
    for f in feeds:
        cid = f.get("channel")
        if not cid:
            continue
        if cid not in best or (f.get("is_main") and not best[cid].get("is_main")):
            best[cid] = f
    return {cid: f.get("languages") or [] for cid, f in best.items()}


async def get_sports_channels(playable_only: bool = True) -> list[dict]:
    """
    Return live sports channels that have at least one playable stream.

    Each item: id, name, country, languages, origin, website, url, referrer,
    user_agent, quality.

    By default only streams served from a broadcaster-owned or licensed origin
    are returned — see services/stream_origin.py. Pass playable_only=False to
    see the whole catalog including restreams, which the proxy will still
    refuse; that is for admin review, not for listings.
    """
    channels, streams = await _get_json("channels"), await _get_json("streams")
    languages = await _languages_by_channel()

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
                "languages": languages.get(ch["id"], []),
                "website": ch.get("website"),
                "url": stream["url"],
                "referrer": stream.get("referrer"),
                "user_agent": stream.get("user_agent"),
                "quality": stream.get("quality"),
            }
        )
        # Where this stream is served FROM decides whether it may be played at
        # all — see services/stream_origin.py.
        results[-1]["origin"] = stream_origin.classify(results[-1]["url"])

    # RTM's own channels, which iptv-org either lists with an unusable URL
    # (SukanRTM.my points at a 404ing .mpd) or omits entirely because they are
    # categorised as general rather than sports. Ours win on id collision.
    rtm_ids = {c["id"] for c in rtm.catalog()}
    results = [c for c in results if c["id"] not in rtm_ids and c["id"] != "SukanRTM.my"]
    results += rtm.catalog()

    if playable_only:
        results = [c for c in results if stream_origin.is_playable(c["origin"])]
    results.sort(key=lambda c: c["name"])
    return results


async def get_channel_stream(channel_id: str) -> dict | None:
    """
    Return the stream record for a single channel id, or None.

    Deliberately searches the UNFILTERED catalog: the proxy needs to tell "no
    such channel" apart from "that channel is a restream", and can only do that
    if it can see the second case.
    """
    for ch in await get_sports_channels(playable_only=False):
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
    "^sport tv", "setanta", "goltv", "match!", "okko futbol",
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
    # US/AU sports networks, which the `same_country` fallback pulls in wholesale
    # for the Premier League. These used to be filtered by accident — the probe
    # sweep was so over-concurrent that it reported them offline (see _probe_sem)
    # and they never reached the UI. With liveness measured correctly they are
    # up, and "Monster Jam" under a Premier League heading is exactly the kind of
    # wrong answer the reason-tagging exists to prevent.
    # Verified against the live catalog: these 21 remove 29 channels, all of them
    # gridiron/hockey/baseball/basketball/motorsport/combat feeds.
    "nfl", "nhl", "mlb", "nba", "hockey", "basketball", "baseball", "lacrosse",
    "racing", "racer", "nhra", "slopes", "ski tv", "strongman", "xfc",
    "pac-12", "acc network", "acc digital", "swerve", "monster jam",
    # " f1" with the leading space, never bare "f1": it must strike Sky Sport(s)
    # F1 — which the ELC/PL "sky sports" hint drags in — without matching inside
    # any other name. Catches exactly 3 channels, all Formula 1.
    " f1",
    # The free catalog holds seven "ESPN*" channels and only these two are in
    # English — ESPNU (US college sports) and ESPN8: The Ocho (novelty sports).
    # Neither has ever shown European league football. The "espn" entry in
    # _GLOBAL_FOOTBALL was written for ESPN Brasil and ESPN Deportes, which do
    # carry football but in Portuguese and Spanish; ranking English first
    # therefore promoted exactly the two ESPN channels that never show it, and
    # put US college football on screen under a Championship heading.
    "espnu", "the ocho",
    # "e-sport" only, never "esport": that would also strike Esport3 (Catalonia's
    # public broadcaster, which shows football and is named in the geo-block note
    # below), Pluto TV Esportes, and World of Freesports.
    "e-sport",
]


def _name_matches(name: str, keywords) -> bool:
    """
    Match a channel name against broadcaster keywords.

    A keyword prefixed with "^" must match at the START of the name. Plain
    substring matching is right for most ("movistar" has to find
    "Deportes por Movistar Plus+"), but it is actively wrong for names that are
    common words: "sport tv" was meant for Portugal's Sport TV1-7 and instead
    also matched ACI Sport TV — Italy's motorsport channel, which then played Le
    Mans Cup qualifying under a Championship fixture — plus AS3 Sport TV and
    We Sport TV. Anchoring keeps the Portuguese feeds and drops the rest.
    """
    lowered = name.lower()
    return any(
        lowered.startswith(k[1:]) if k.startswith("^") else k in lowered
        for k in keywords
    )


def _is_football(name: str) -> bool:
    lowered = name.lower()
    return not any(k in lowered for k in _NON_FOOTBALL)


# ── Broadcaster families ────────────────────────────────────────────────────
#
# The catalog is dense with numbered variants of one broadcaster: "Arena Sport"
# alone appears 21 times across BA/HR/RS/SK. Ordered by name, those 21 rows sat
# at the front of the alphabet and consumed an entire probe budget on their own,
# so the channels that were actually serving — beIN SPORTS XTRA, Ziggo Sport 5,
# Zona DAZN — were cut before anything checked whether they were up. Collapsing
# the variants into a family and taking one from each in turn is what stops a
# single broadcaster from crowding out every other one.
_FAMILY_QUALIFIERS = {"hd", "uhd", "fhd", "sd", "4k", "premium", "plus", "live"}


def _family(name: str) -> str:
    """Broadcaster identity with the variant markers stripped off."""
    words = [w for w in re.split(r"[^a-z0-9+]+", name.lower()) if w]
    kept = [w for w in words if not w.isdigit() and w not in _FAMILY_QUALIFIERS]
    return " ".join(kept) or name.lower()


def speaks_english(channel: dict) -> bool:
    """Whether this channel's commentary is in English (ISO 639-3 'eng')."""
    return "eng" in (channel.get("languages") or [])


def _round_robin(channels: list[dict]) -> list[dict]:
    """Re-order so every family contributes its first entry before any second."""
    families: dict[str, list[dict]] = {}
    for ch in channels:
        families.setdefault(_family(ch["name"]), []).append(ch)
    if not families:
        return []
    ordered = list(families.values())
    return [fam[depth] for depth in range(max(len(f) for f in ordered))
            for fam in ordered if depth < len(fam)]


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
    # RTM holds Malaysian free-to-air rights to the World Cup — all 104 matches
    # of 2026 — so its channels are genuine rights holders here, not a guess.
    # This is the one competition in the whole config where a FREE and LICENSED
    # carrier actually exists.
    "WC":  {"countries": {"MY"},     "names": ["tv1 (rtm)", "tv2 (rtm)", "sukan rtm"]},
    "CL":  {"countries": set(),      "names": []},                       # UEFA — broadly carried
    "EL":  {"countries": set(),      "names": []},
    "ECL": {"countries": set(),      "names": []},
    "EC":  {"countries": set(),      "names": []},                       # Euros — broadly carried
    "PL":  {"countries": {"GB", "US"}, "names": ["premier sports", "peacock", "usa network"]},
    # The Championship's rights sit with Sky (UK) and ESPN+ (US), both paywalled
    # and absent from the free catalog — and iptv-org currently carries NO GB
    # sports channel at all, so the country hint matches nothing either. Listed
    # anyway for the same reason as SSC/SuperSport below: it costs nothing and
    # starts working the day either appears. Until then ELC falls through to the
    # generic football pool, which is exactly what it should do.
    "ELC": {"countries": {"GB"},     "names": ["sky sports", "premier sports"]},
    "PD":  {"countries": {"ES"},     "names": ["movistar"]},
    "SA":  {"countries": {"IT"},     "names": ["sportitalia", "^sport tv"]},
    "BL1": {"countries": {"DE"},     "names": ["sport1"]},
    "FL1": {"countries": {"FR"},     "names": []},
    "DED": {"countries": {"NL"},     "names": ["ziggo sport"]},
    "PPL": {"countries": {"PT"},     "names": ["^sport tv"]},
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
    "WWC":  {"countries": {"MY"},    "names": ["tv1 (rtm)", "tv2 (rtm)", "sukan rtm"]},
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
        if _name_matches(c["name"], _GLOBAL_FOOTBALL) and _is_football(c["name"])
    ]
    statuses = await asyncio.gather(*[
        check_stream_alive(c["url"], c.get("referrer"), c.get("user_agent"))
        for c in chans
    ])
    alive = [
        {**c, "alive": True, "status": s["status"]}
        for c, s in zip(chans, statuses) if s["alive"]
    ]
    # English commentary first — same preference the league listings apply.
    alive.sort(key=lambda c: (not speaks_english(c), c["name"]))
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


# Surface WHY each channel is here. Without this the UI can't distinguish
# Portugal's Sport TV (the actual Primeira Liga rights holder) from Arena
# Sport Slovakia, which is only here because it shows football in general —
# and presenting the second as if it were the first is misleading.
_MATCH_REASON = {
    0: "league_broadcaster",
    1: "broadcaster_elsewhere",
    2: "same_country",
    3: "general_football",
}


async def get_channels_for_league(
    league_code: str, limit: int = 32, probe_limit: int = 64, only_alive: bool = True
) -> list[dict]:
    """
    Best-effort list of channels that may be broadcasting the given league,
    league-specific broadcasters first, then that country, then global feeds.

    Candidates are liveness-checked (concurrently, cached 2 min) and tagged with
    an `alive` flag; `limit` bounds what comes back. Most premium sports feeds in
    the free catalog are geo-locked or offline (403), so by default only channels
    actually serving right now are returned.

    `limit` applies to the SURVIVORS, never to the candidates — cutting the pool
    before probing it is what made whole competitions look unwatchable. A league
    with no hints (say the Championship, whose rights holders are all paywalled)
    matches only the generic football pool, which is ~113 channels ordered by
    name; slicing 32 off the front of that handed the entire budget to
    "Arena Sport 1..10" and every channel that was up got discarded unprobed.
    `probe_limit` still bounds the work, but it is spent across broadcasters
    rather than down one of them.
    """
    hints = _LEAGUE_HINTS.get(league_code.upper(), {})
    league_names = hints.get("names", [])
    countries = hints.get("countries", set())

    bands: dict[int, list[dict]] = {p: [] for p in _MATCH_REASON}
    for ch in await get_sports_channels():
        name = ch["name"].lower()
        if not _is_football(ch["name"]):
            continue                                       # golf/darts/combat — never football

        named = bool(league_names) and _name_matches(ch["name"], league_names)
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
        elif _name_matches(ch["name"], _GLOBAL_FOOTBALL):
            priority = 3                                   # generic football broadcaster
        else:
            continue
        bands[priority].append(ch)

    # Rights holders are probed before generic feeds; within a band, English
    # commentary before other languages; within each of those, one channel per
    # broadcaster before any broadcaster's second.
    #
    # Priority stays above language deliberately. A rights holder broadcasting in
    # Malay is genuinely showing the match; an English channel tagged
    # `general_football` is only showing football in general. Demoting the former
    # under the latter would trade a real answer for a comprehensible one.
    candidates: list[tuple[int, dict]] = []
    for priority in sorted(bands):
        band = sorted(bands[priority], key=lambda c: c["name"])
        english = [c for c in band if speaks_english(c)]
        other = [c for c in band if not speaks_english(c)]
        candidates += [(priority, ch) for ch in _round_robin(english) + _round_robin(other)]
    candidates = candidates[:probe_limit]

    # Verify each candidate is actually serving before offering it to the player.
    statuses = await asyncio.gather(*[
        check_stream_alive(c["url"], c.get("referrer"), c.get("user_agent"))
        for _, c in candidates
    ])
    tagged = [
        {**c, "alive": s["alive"], "status": s["status"], "match_reason": _MATCH_REASON[prio]}
        for (prio, c), s in zip(candidates, statuses)
    ]

    alive = [c for c in tagged if c["alive"]][:limit]
    if only_alive:
        return alive
    # An offline rights holder is the one absence worth naming — "Ziggo Sport
    # holds this and is down" is an answer. An offline generic football channel
    # explains nothing, so it stays out of the payload.
    offline_holders = [
        c for c in tagged
        if not c["alive"] and c["match_reason"] == "league_broadcaster"
    ][:8]
    return alive + offline_holders


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

    async def _variant_serving() -> bool:
        """Follow master -> first variant and confirm the variant really exists."""
        async with httpx.AsyncClient(timeout=4, follow_redirects=True) as client:
            master = await client.get(url, headers=headers)
            if master.status_code != 200:
                return False
            rel = next((ln.strip() for ln in master.text.splitlines()
                        if ln.strip() and not ln.startswith("#")), None)
            if rel is None:
                return False                       # a ladder with no variants at all
            if not rel.startswith("#EXT") and rel.split("?")[0].endswith((".ts", ".m4s")):
                return True                        # already a media playlist, not a master
            base = str(master.url).rsplit("/", 1)[0]
            target = rel if rel.startswith("http") else f"{base}/{rel}"
            return (await client.get(target, headers=headers)).status_code == 200

    try:
        # Hard ceiling per check: a bad host can chain several redirect hops,
        # each with its own timeout, so bound the whole probe — otherwise
        # gather() over many channels waits on the single slowest one.
        async with _probe_sem:
            result = await asyncio.wait_for(_probe(), timeout=4)
            if result["alive"] and url in _VERIFY_VARIANT:
                if not await asyncio.wait_for(_variant_serving(), timeout=6):
                    result = {"alive": False, "status": result["status"],
                              "error": "Off air (no variant being produced)"}
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
