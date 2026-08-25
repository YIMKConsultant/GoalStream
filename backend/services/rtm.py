"""
RTM (Radio Televisyen Malaysia) free-to-air channels.

RTM is Malaysia's public broadcaster and the one source in this app that is both
free and licensed: it holds Malaysian free-to-air rights and carries all 104
FIFA World Cup 2026 matches. Everything else in the catalog is either a paid
broadcaster we cannot legally relay, or a restream we will not.

Streams come from RTM's own CloudFront distribution, the same origin RTM Klik
plays. Two properties of that origin drive the whole design here:

  1. `?id=` is REQUIRED. Without it a CloudFront Function answers
     `403 Not Available in your region`, which is a misleading message — the
     same request WITH the parameter returns 200 from the same edge POP. Only
     the parameter's presence is checked, never its value.

  2. The master playlist is a CANNED response. Any path under `smil:*/` returns
     an identical #EXT-X-STREAM-INF ladder, including paths that do not exist —
     `smil:tv2/chunklist_w123456789.m3u8` returns 200 just like a real one. A
     master fetch therefore proves NOTHING about whether a channel is on air.
     Only fetching a variant and finding real segments does, which is why every
     channel here is variant-verified rather than trusted at the master.

RTM Klik itself is a Next.js SPA whose HTML contains no stream URLs, so the
regex scraper in services/stream_scraper.py cannot work against it. Its content
API (https://rtm.glueapi.io/v1/content) serves VOD only — no live-channel
schema, and no documented live endpoint — so this registry is explicit rather
than discovered.
"""
import asyncio

from cachetools import TTLCache

CDN = "https://d25tgymtnqzu8s.cloudfront.net"
REFERRER = "https://rtmklik.rtm.gov.my/"

# RTM rejects UAs that look like a desktop browser or a media player: anything
# carrying "(KHTML, like Gecko) ... Chrome/... Safari/..." gets 403, as does
# VLC's. The short AppleWebKit string below is accepted, and is the SAME one
# routers/proxy.py sends — so what we probe is what playback fetches.
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# `football` marks the channels RTM actually puts matches on — TV1 and TV2 carry
# the national team and World Cup, Sukan RTM is the dedicated sports channel.
# The rest are listed so the catalog is complete and so an admin can see them,
# but they are not offered as football carriers.
CHANNELS = [
    {"slug": "tv1",    "name": "TV1 (RTM)",        "football": True},
    {"slug": "tv2",    "name": "TV2 (RTM)",        "football": True},
    {"slug": "sukan",  "name": "Sukan RTM",        "football": True},
    {"slug": "tv6",    "name": "TV6 (RTM)",        "football": False},
    {"slug": "okey",   "name": "Okey (RTM)",       "football": False},
    {"slug": "berita", "name": "Berita RTM",       "football": False},
    {"slug": "rakyat", "name": "RTM Dewan Rakyat", "football": False},
    {"slug": "negara", "name": "RTM Dewan Negara", "football": False},
]

# Channel ids are namespaced so they cannot collide with an iptv-org id.
def channel_id(slug: str) -> str:
    return f"rtm:{slug}"


def stream_url(slug: str) -> str:
    # The `?id=1` is load-bearing — see the module docstring. Do not strip it.
    return f"{CDN}/smil:{slug}/playlist.m3u8?id=1"


def _record(ch: dict) -> dict:
    return {
        "id": channel_id(ch["slug"]),
        "name": ch["name"],
        "country": "MY",
        "languages": ["msa"],
        "website": "https://rtmklik.rtm.gov.my/",
        "url": stream_url(ch["slug"]),
        "referrer": REFERRER,
        "user_agent": USER_AGENT,
        "quality": None,
        # RTM's own CloudFront distribution — broadcaster-operated, so this is
        # `official` under services/stream_origin.py.
        "origin": "official",
        "rtm_football": ch["football"],
    }


def catalog() -> list[dict]:
    """Every RTM channel, without touching the network."""
    return [_record(c) for c in CHANNELS]


def football_channel_ids() -> list[str]:
    """RTM channels that carry football, for the league mapping."""
    return [channel_id(c["slug"]) for c in CHANNELS if c["football"]]


_live_cache: TTLCache = TTLCache(maxsize=1, ttl=120)


async def live_channels(check) -> list[dict]:
    """
    RTM channels that are genuinely producing video right now.

    `check` is the liveness probe (services.iptv_org.check_stream_alive), passed
    in rather than imported so this module stays free of a circular import.
    Because the master is canned, `check` MUST be the variant-verifying form —
    see verify_variant in iptv_org.
    """
    cached = _live_cache.get("live")
    if cached is not None:
        return cached

    channels = catalog()
    statuses = await asyncio.gather(*[
        check(c["url"], c.get("referrer"), c.get("user_agent")) for c in channels
    ])
    result = [
        {**c, "alive": s["alive"], "status": s["status"]}
        for c, s in zip(channels, statuses)
    ]
    _live_cache["live"] = result
    return result
