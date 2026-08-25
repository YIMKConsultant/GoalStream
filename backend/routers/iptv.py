"""
Public browse of live sports TV channels sourced from the free iptv-org API.

Every listing here is filtered against the caller: anonymous visitors see only
"public" channels, signed-in users see whatever their tier and per-user grants
reach, and staff see everything. Playable URLs point at /api/proxy/channel/{id},
which re-checks access and resolves the real stream server-side — so a channel
hidden from a listing cannot be watched by guessing its URL either.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_optional_user
from database import get_db
from models import User
from routers.proxy import channel_proxy_url
from services import access, ai_discovery
from services.iptv_org import (
    get_sports_channels,
    get_channel_stream,
    get_channels_for_league,
    get_channels_for_league_ids,
    get_replay_channels,
    get_playing_channels,
    check_stream_alive,
)

router = APIRouter(prefix="/api/iptv", tags=["IPTV"])


class IptvChannel(BaseModel):
    id: str
    name: str
    country: str | None = None
    languages: list[str] = []   # ISO 639-3 commentary languages, e.g. ["eng"]
    origin: str = "unverified"  # official | restream | unverified — see stream_origin
    website: str | None = None
    quality: str | None = None
    proxied_url: str            # ready to feed an HLS player
    alive: bool | None = None   # populated by replay/status endpoints
    tier: str = "public"        # minimum tier needed to watch this
    # Why this channel was offered for a league — league_broadcaster |
    # broadcaster_elsewhere | same_country | general_football | ai_match.
    # The UI must show this: a general_football channel is NOT carrying the match.
    match_reason: str | None = None


class StreamStatus(BaseModel):
    alive: bool
    status: int
    error: str | None = None


def _to_model(ch: dict, tier: str = "public") -> IptvChannel:
    return IptvChannel(
        id=ch["id"],
        name=ch["name"],
        country=ch.get("country"),
        languages=ch.get("languages") or [],
        origin=ch.get("origin") or "unverified",
        website=ch.get("website"),
        quality=ch.get("quality"),
        proxied_url=channel_proxy_url(ch["id"]),
        alive=ch.get("alive"),
        tier=tier,
        match_reason=ch.get("match_reason"),
    )


async def _visible(channels: list[dict], user: User | None, db: AsyncSession) -> list[IptvChannel]:
    """Drop everything this caller may not watch, and tag what's left."""
    policies, grants = await access.viewer_context(db, user)
    return [
        _to_model(c, access.required_tier(c["id"], policies))
        for c in channels
        if access.can_watch(c["id"], user, policies, grants)
    ]


@router.get("/channels", response_model=list[IptvChannel])
async def list_sports_channels(
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """List live sports channels (with playable streams) from iptv-org."""
    try:
        channels = await get_sports_channels()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"iptv-org API unavailable: {e}")
    return await _visible(channels, user, db)


@router.get("/featured", response_model=list[IptvChannel])
async def featured_channels(
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Sports channels that are actually playing right now (liveness-checked)."""
    try:
        channels = await get_playing_channels()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"iptv-org API unavailable: {e}")
    return await _visible(channels, user, db)


@router.get("/for-league/{league_code}", response_model=list[IptvChannel])
async def channels_for_league(
    league_code: str,
    include_offline: bool = False,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Candidate channels that MAY be broadcasting a league right now.
    iptv-org has no schedule, so this is a broadcaster heuristic, not a guarantee.
    Each candidate is liveness-checked; offline/geo-locked ones are hidden unless
    include_offline=true (then they come back tagged alive=false).
    """
    try:
        # An AI-built map for this league wins over the keyword heuristic —
        # it's ranked, verified against the real catalog, and free of the
        # substring false positives the keyword lists keep producing.
        mapped = await ai_discovery.mapped_channel_ids(db, league_code)
        channels = (
            await get_channels_for_league_ids(mapped, only_alive=not include_offline)
            if mapped else
            await get_channels_for_league(league_code, only_alive=not include_offline)
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"iptv-org API unavailable: {e}")
    return await _visible(channels, user, db)


@router.get("/replays", response_model=list[IptvChannel])
async def replay_channels(
    include_offline: bool = False,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Free channels that air replays / classic matches (FIFA+ World Cup archive,
    club TV, Classics). Each is liveness-checked; offline ones are hidden
    unless include_offline=true.
    """
    try:
        channels = await get_replay_channels(only_alive=not include_offline)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"iptv-org API unavailable: {e}")
    return await _visible(channels, user, db)


@router.get("/channels/{channel_id}", response_model=IptvChannel)
async def get_channel(
    channel_id: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get one sports channel's playable (proxied) stream by iptv-org id."""
    try:
        ch = await get_channel_stream(channel_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"iptv-org API unavailable: {e}")
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found or has no stream")

    policies, grants = await access.viewer_context(db, user)
    if not access.can_watch(channel_id, user, policies, grants):
        raise HTTPException(
            status_code=401 if user is None else 403,
            detail="Sign in to watch this channel" if user is None
            else "Your account doesn't have access to this channel",
        )
    return _to_model(ch, access.required_tier(channel_id, policies))


@router.get("/channels/{channel_id}/status", response_model=StreamStatus)
async def channel_status(
    channel_id: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Check whether a channel's stream is actually serving right now."""
    ch = await get_channel_stream(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found or has no stream")

    policies, grants = await access.viewer_context(db, user)
    if not access.can_watch(channel_id, user, policies, grants):
        raise HTTPException(status_code=403, detail="No access to this channel")
    return await check_stream_alive(ch["url"], ch.get("referrer"), ch.get("user_agent"))
