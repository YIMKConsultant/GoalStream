"""
Probes common master playlist paths on RTM's CloudFront CDN.
Run: python probe_stream.py
"""
import asyncio
import httpx

BASE = "https://d30aylox5wvifh.cloudfront.net/live/media0/wc2/HLS"

CANDIDATES = [
    f"{BASE}/master.m3u8",
    f"{BASE}/index.m3u8",
    f"{BASE}/wc2.m3u8",
    f"{BASE}/playlist.m3u8",
    f"{BASE}/live.m3u8",
    f"{BASE}/stream.m3u8",
    "https://d30aylox5wvifh.cloudfront.net/live/media0/wc2/master.m3u8",
    "https://d30aylox5wvifh.cloudfront.net/live/media0/wc2/index.m3u8",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://rtmklik.rtm.gov.my/",
    "Origin": "https://rtmklik.rtm.gov.my",
}

async def main():
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for url in CANDIDATES:
            try:
                r = await client.get(url, headers=HEADERS)
                ct = r.headers.get("content-type", "")
                preview = r.text[:120].replace("\n", " ") if r.status_code == 200 else ""
                if r.status_code == 200:
                    is_m3u8 = "#EXTM3U" in r.text or "m3u8" in ct
                    mark = "✅" if is_m3u8 else "⚠️ "
                    print(f"{mark} {r.status_code} [{ct}]: {url}")
                    print(f"   Preview: {preview}")
                else:
                    print(f"❌ {r.status_code}: {url}")
            except Exception as e:
                print(f"❌ ERROR: {url} — {e}")

if __name__ == "__main__":
    asyncio.run(main())
