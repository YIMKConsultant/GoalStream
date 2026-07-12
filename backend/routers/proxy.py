"""
HLS stream proxy — fetches m3u8/ts segments server-side so the browser
never hits CORS restrictions from the original broadcaster.
"""
import re
import httpx
from fastapi import APIRouter, HTTPException, Response, Query
from fastapi.responses import StreamingResponse
from services.stream_scraper import get_rtm_stream_url

router = APIRouter(prefix="/api/proxy", tags=["Proxy"])

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://rtmklik.rtm.gov.my/",
    "Origin": "https://rtmklik.rtm.gov.my",
}


def _abs(url: str, base: str) -> str:
    if url.startswith("http"):
        return url
    if url.startswith("/"):
        root = "/".join(base.split("/")[:3])
        return f"{root}{url}"
    return f"{base}/{url}"


def _proxy(url: str) -> str:
    return f"/api/proxy/stream?url={url}"


def rewrite_m3u8(text: str, base: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()

        # Encryption key: #EXT-X-KEY:METHOD=AES-128,URI="https://key-server/key"
        if stripped.startswith("#EXT-X-KEY") and "URI=" in stripped:
            def replace_key(m):
                return f'URI="{_proxy(_abs(m.group(1), base))}"'
            line = re.sub(r'URI="([^"]+)"', replace_key, line)

        # Initialization segment: #EXT-X-MAP:URI="file.m4s"
        elif stripped.startswith("#EXT-X-MAP"):
            def replace_map(m):
                return f'URI="{_proxy(_abs(m.group(1), base))}"'
            line = re.sub(r'URI="([^"]+)"', replace_map, line)

        # Audio / subtitle rendition: #EXT-X-MEDIA:URI="audio.m3u8"
        elif stripped.startswith("#EXT-X-MEDIA") and "URI=" in stripped:
            def replace_media(m):
                return f'URI="{_proxy(_abs(m.group(1), base))}"'
            line = re.sub(r'URI="([^"]+)"', replace_media, line)

        # Bare segment line (.ts / .m4s / sub-playlist .m3u8)
        elif stripped and not stripped.startswith("#"):
            line = _proxy(_abs(stripped, base))

        lines.append(line)
    return "\n".join(lines)


@router.get("/stream")
async def proxy_stream(url: str = Query(...)):
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS, cookies={"rtmklik": "1"})
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Upstream error")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch stream: {e}")

    content_type = resp.headers.get("content-type", "application/octet-stream")
    base = url.rsplit("/", 1)[0]

    if "mpegurl" in content_type or url.split("?")[0].endswith(".m3u8"):
        rewritten = rewrite_m3u8(resp.text, base)
        return Response(
            content=rewritten,
            media_type="application/vnd.apple.mpegurl",
            headers={"Access-Control-Allow-Origin": "*"},
        )

    return StreamingResponse(
        resp.aiter_bytes(),
        media_type=content_type,
        headers={"Access-Control-Allow-Origin": "*"},
    )


@router.get("/extract")
async def extract_stream(page_url: str = Query(...)):
    url = await get_rtm_stream_url(page_url)
    if not url:
        raise HTTPException(status_code=404, detail="Could not find stream URL on that page")
    return {"stream_url": url, "proxied_url": _proxy(url)}
