"""
Dynamically extracts the live HLS stream URL from RTM Klik pages.
Called each time a user opens the watch page so the URL is always fresh.
"""
import re
import httpx
from cachetools import TTLCache

_cache: TTLCache = TTLCache(maxsize=32, ttl=50)  # cache 50s (URL valid ~60s)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "Chrome/125.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


async def get_rtm_stream_url(page_url: str) -> str | None:
    """Fetch the RTM Klik page and extract the live m3u8 URL."""
    cached = _cache.get(page_url)
    if cached:
        return cached

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.get(page_url, headers=HEADERS)
            resp.raise_for_status()
            html = resp.text
        except Exception:
            return None

    # RTM Klik embeds the stream URL in a JS variable or data attribute
    patterns = [
        r'["\'](https://[^"\']+cloudfront\.net[^"\']+\.m3u8[^"\']*)["\']',
        r'["\'](https://[^"\']+akamaihd\.net[^"\']+\.m3u8[^"\']*)["\']',
        r'["\'](https://[^"\']+rtm\.gov\.my[^"\']+\.m3u8[^"\']*)["\']',
        r'src=["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
    ]

    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            url = match.group(1)
            _cache[page_url] = url
            return url

    return None
