"""
HLS stream proxy — fetches m3u8/ts segments server-side so the browser
never hits CORS restrictions from the original broadcaster.

Access control lives here, because this is the only endpoint that actually moves
video. Two ways in:

  /api/proxy/channel/{id}  the player's entry point. Checks the caller against
                           the channel's tier and their per-user grants, then
                           resolves the real URL server-side — it never reaches
                           the browser at all.
  /api/proxy/stream?url=   for the segment and key URLs inside a playlist, which
                           the browser must fetch itself. Requires a signature
                           issued by the channel endpoint above, so it can no
                           longer be used to fetch arbitrary URLs.
"""
import re
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_optional_user
from database import get_db
from models import User
from services import access, stream_token
from services.iptv_org import get_channel_stream
from services.stream_scraper import get_rtm_stream_url

router = APIRouter(prefix="/api/proxy", tags=["Proxy"])

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://rtmklik.rtm.gov.my/",
    "Origin": "https://rtmklik.rtm.gov.my",
}


def _headers_for(referrer: str | None, ua: str | None) -> dict:
    """
    Build upstream request headers. When the caller supplies a referrer/UA
    (e.g. iptv-org streams carry their own), use those; otherwise fall back
    to the RTM Klik defaults.
    """
    if not referrer and not ua:
        return HEADERS
    headers = {"User-Agent": ua or HEADERS["User-Agent"]}
    if referrer:
        headers["Referer"] = referrer
        headers["Origin"] = "/".join(referrer.split("/")[:3])
    return headers


def _abs(url: str, base: str) -> str:
    if url.startswith("http"):
        return url
    if url.startswith("/"):
        root = "/".join(base.split("/")[:3])
        return f"{root}{url}"
    return f"{base}/{url}"


def signed_proxy_url(url: str, referrer: str | None = None, ua: str | None = None) -> str:
    """
    A /api/proxy/stream link the browser can actually use.

    Only call this once the caller has been cleared for the channel — the
    signature is what authorises the fetch.
    """
    exp, sig = stream_token.sign(url, referrer, ua)
    params = {"url": url}
    if referrer:
        params["referrer"] = referrer
    if ua:
        params["ua"] = ua
    params["exp"] = str(exp)
    params["sig"] = sig
    return f"/api/proxy/stream?{urlencode(params)}"


def channel_proxy_url(channel_id: str) -> str:
    """
    The player-facing URL for a channel — no upstream URL in it, and carrying a
    ticket that proves the caller already passed the access check.

    Only build this after checking access: the ticket is what the video player
    presents instead of the Authorization header it cannot send.
    """
    exp, sig = stream_token.sign_channel(channel_id)
    return f"/api/proxy/channel/{channel_id}?{urlencode({'exp': exp, 'sig': sig})}"


def rewrite_m3u8(text: str, base: str, referrer: str | None = None, ua: str | None = None) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()

        # Encryption key: #EXT-X-KEY:METHOD=AES-128,URI="https://key-server/key"
        if stripped.startswith("#EXT-X-KEY") and "URI=" in stripped:
            def replace_key(m):
                return f'URI="{signed_proxy_url(_abs(m.group(1), base), referrer, ua)}"'
            line = re.sub(r'URI="([^"]+)"', replace_key, line)

        # Initialization segment: #EXT-X-MAP:URI="file.m4s"
        elif stripped.startswith("#EXT-X-MAP"):
            def replace_map(m):
                return f'URI="{signed_proxy_url(_abs(m.group(1), base), referrer, ua)}"'
            line = re.sub(r'URI="([^"]+)"', replace_map, line)

        # Audio / subtitle rendition: #EXT-X-MEDIA:URI="audio.m3u8"
        elif stripped.startswith("#EXT-X-MEDIA") and "URI=" in stripped:
            def replace_media(m):
                return f'URI="{signed_proxy_url(_abs(m.group(1), base), referrer, ua)}"'
            line = re.sub(r'URI="([^"]+)"', replace_media, line)

        # Bare segment line (.ts / .m4s / sub-playlist .m3u8)
        elif stripped and not stripped.startswith("#"):
            line = signed_proxy_url(_abs(stripped, base), referrer, ua)

        lines.append(line)
    return "\n".join(lines)


async def _fetch_and_serve(url: str, referrer: str | None, ua: str | None):
    """Fetch an upstream URL and hand it back, rewriting playlists as we go."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=_headers_for(referrer, ua), cookies={"rtmklik": "1"})
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Upstream error")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch stream: {e}")

    content_type = resp.headers.get("content-type", "application/octet-stream")
    # Resolve relative segment/variant URLs against the FINAL url after any
    # redirects (e.g. jmp2.uk -> pluto.tv), not the original short link.
    final_url = str(resp.url)
    base = final_url.rsplit("/", 1)[0]

    if "mpegurl" in content_type or final_url.split("?")[0].endswith(".m3u8"):
        rewritten = rewrite_m3u8(resp.text, base, referrer, ua)
        return Response(
            content=rewritten,
            media_type="application/vnd.apple.mpegurl",
            headers={
                "Access-Control-Allow-Origin": "*",
                # A LIVE playlist is rewritten every few seconds as segments roll
                # off the end. Without this the browser serves its cached copy
                # back to hls.js, which then sees no new segments, drains its
                # buffer and stalls — playback stops a few seconds in.
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    # Segments are immutable and content-addressed — caching them is free speed
    # and cuts repeat load on the upstream CDN.
    return StreamingResponse(
        resp.aiter_bytes(),
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/channel/{channel_id}")
async def proxy_channel(
    channel_id: str,
    exp: int | None = Query(None),
    sig: str | None = Query(None),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream a catalog channel, if this caller is allowed to. The upstream URL is
    looked up here and never sent to the browser.

    Two ways to prove access: a ticket minted by a listing endpoint (what the
    video player uses, since it can't send an auth header), or a bearer token
    (for direct API callers). Either is enough; both are re-checked here rather
    than trusted from the listing alone.
    """
    ticketed = stream_token.verify_channel(channel_id, exp, sig)
    if not ticketed:
        policies, grants = await access.viewer_context(db, user)
        if not access.can_watch(channel_id, user, policies, grants):
            raise HTTPException(
                status_code=401 if user is None else 403,
                detail="Sign in to watch this channel" if user is None
                else "Your account doesn't have access to this channel",
            )

    try:
        channel = await get_channel_stream(channel_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"iptv-org API unavailable: {e}")
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found or has no stream")

    return await _fetch_and_serve(
        channel["url"], channel.get("referrer"), channel.get("user_agent")
    )


@router.get("/stream")
async def proxy_stream(
    url: str = Query(...),
    referrer: str | None = Query(None),
    ua: str | None = Query(None),
    exp: int | None = Query(None),
    sig: str | None = Query(None),
):
    """
    Fetch one signed URL — the segments and keys inside a playlist we served.

    An unsigned or expired request is refused: without that, anyone could point
    this at any channel's URL and bypass the access rules entirely.
    """
    if not stream_token.verify(url, referrer, ua, exp, sig):
        raise HTTPException(
            status_code=403,
            detail="Missing or expired stream signature — start playback from the channel again",
        )
    return await _fetch_and_serve(url, referrer, ua)


@router.get("/extract")
async def extract_stream(page_url: str = Query(...)):
    url = await get_rtm_stream_url(page_url)
    if not url:
        raise HTTPException(status_code=404, detail="Could not find stream URL on that page")
    return {"stream_url": url, "proxied_url": signed_proxy_url(url)}
