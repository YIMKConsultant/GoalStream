"""
Public browse of live sports TV channels sourced from the free iptv-org API.
Playable URLs are wrapped through /api/proxy/stream so the browser avoids
CORS / referrer restrictions from the original broadcaster.
"""
from urllib.parse import urlencode
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.iptv_org import (
    get_sports_channels,
    get_channel_stream,
    get_channels_for_league,
    get_replay_channels,
    get_playing_channels,
    check_stream_alive,
)

router = APIRouter(prefix="/api/iptv", tags=["IPTV"])


class IptvChannel(BaseModel):
    id: str
    name: str
    country: str | None = None
    website: str | None = None
    quality: str | None = None
    proxied_url: str            # ready to feed an HLS player
    alive: bool | None = None   # populated by replay/status endpoints


class StreamStatus(BaseModel):
    alive: bool
    status: int
    error: str | None = None


def _proxied(stream: dict) -> str:
    """Build a /api/proxy/stream URL carrying the channel's required headers."""
    params = {"url": stream["url"]}
    if stream.get("referrer"):
        params["referrer"] = stream["referrer"]
    if stream.get("user_agent"):
        params["ua"] = stream["user_agent"]
    return f"/api/proxy/stream?{urlencode(params)}"


def _to_model(ch: dict) -> IptvChannel:
    return IptvChannel(
        id=ch["id"],
        name=ch["name"],
        country=ch.get("country"),
        website=ch.get("website"),
        quality=ch.get("quality"),
        proxied_url=_proxied(ch),
        alive=ch.get("alive"),
    )


@router.get("/channels", response_model=list[IptvChannel])
async def list_sports_channels():
    """List live sports channels (with playable streams) from iptv-org."""
    try:
        channels = await get_sports_channels()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"iptv-org API unavailable: {e}")
    return [_to_model(c) for c in channels]


@router.get("/featured", response_model=list[IptvChannel])
async def featured_channels():
    """Sports channels that are actually playing right now (liveness-checked)."""
    try:
        channels = await get_playing_channels()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"iptv-org API unavailable: {e}")
    return [_to_model(c) for c in channels]


@router.get("/for-league/{league_code}", response_model=list[IptvChannel])
async def channels_for_league(league_code: str, include_offline: bool = False):
    """
    Candidate channels that MAY be broadcasting a league right now.
    iptv-org has no schedule, so this is a broadcaster heuristic, not a guarantee.
    Each candidate is liveness-checked; offline/geo-locked ones are hidden unless
    include_offline=true (then they come back tagged alive=false).
    """
    try:
        channels = await get_channels_for_league(
            league_code, only_alive=not include_offline
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"iptv-org API unavailable: {e}")
    return [_to_model(c) for c in channels]


@router.get("/replays", response_model=list[IptvChannel])
async def replay_channels(include_offline: bool = False):
    """
    Free channels that air replays / classic matches (FIFA+ World Cup archive,
    club TV, Classics). Each is liveness-checked; offline ones are hidden
    unless include_offline=true.
    """
    try:
        channels = await get_replay_channels(only_alive=not include_offline)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"iptv-org API unavailable: {e}")
    return [_to_model(c) for c in channels]


@router.get("/channels/{channel_id}", response_model=IptvChannel)
async def get_channel(channel_id: str):
    """Get one sports channel's playable (proxied) stream by iptv-org id."""
    try:
        ch = await get_channel_stream(channel_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"iptv-org API unavailable: {e}")
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found or has no stream")
    return _to_model(ch)


@router.get("/channels/{channel_id}/status", response_model=StreamStatus)
async def channel_status(channel_id: str):
    """Check whether a channel's stream is actually serving right now."""
    ch = await get_channel_stream(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found or has no stream")
    return await check_stream_alive(ch["url"], ch.get("referrer"), ch.get("user_agent"))
