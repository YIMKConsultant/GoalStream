"""
Whether a stream URL comes from somewhere allowed to be serving it.

iptv-org's catalog is community-submitted and unmoderated on this axis: anyone
can add a working URL, and a large share of what comes back are unauthorized
restreams of subscription channels. Measured over the 414-channel sports
catalog, only ~17% of stream URLs resolve to a broadcaster-owned host or a
licensed FAST platform. The rest are bare IPs on odd ports, throwaway TLDs and
link shorteners serving Fox Sports, Star Sports, Sky Sports and Polsat Sport
Premium — none of which any licensee distributes that way.

The app cannot tell rights-holder from pirate by channel NAME (the pirate uses
the real name, that is the point). It can tell by ORIGIN, so that is what this
does, and it is deliberately default-deny:

    official     host is on the allowlist below — broadcaster-owned, a public
                 broadcaster, or a licensed FAST/CDN platform. Playable.
    restream     positively bad signals — bare IP, non-standard port, throwaway
                 TLD, URL shortener. Never playable.
    unverified   everything else. Not playable by default, but visible to an
                 admin, who can allow a specific channel once they have checked
                 it. This is where a legitimate broadcaster we have not listed
                 yet lands, so it is a queue, not a verdict.

Enforcement lives in routers/proxy.py, because that is the only endpoint that
actually moves video. Filtering a listing alone would leave the stream reachable
by anyone who guessed the channel id.
"""
import re
from urllib.parse import urlparse

# Broadcaster-owned domains, public broadcasters, and licensed FAST/OTT
# platforms. Suffix match against the hostname.
_OFFICIAL_HOSTS = (
    # Licensed FAST / OTT distribution platforms
    "pluto.tv", "jmp2.uk", "amagi.tv", "wurl.com", "wurl.tv", "getpublica.com",
    "sofast.tv", "zype.com", "otteravision.com", "klowdtv.com", "mjh.nz",
    "samsungcloudsolution.com", "rakuten.tv", "brightcove.net", "dailymotion.com",
    "youtube.com", "ott.mangomolo.com", "mangomolo.com",
    # Public / state broadcasters serving their own streams
    "rtve.es", "3catdirectes.cat", "ert.gr", "rtm.gov.my", "gov.my",
    "telewebion.ir", "vtvdigital.vn", "tjk.org", "alkassdigital.net",
    "rtp.pt", "rai.it", "zdf.de", "ard.de", "svt.se", "nrk.no", "yle.fi",
    "abc.net.au", "cbc.ca", "france.tv", "bbc.co.uk",
    # Broadcaster-operated CDNs and their contracted delivery networks
    "akamaized.net", "akamaihd.net", "cloudfront.net", "cdn77.org",
    "mncdn.com", "daioncdn.net", "ercdn.net", "lswcdn.net", "multistream.it",
    "streamakaci.tv", "infomaniak.com", "streamlock.net", "wowza.com",
    "cbsivideo.com", "30a-tv.com", "rocketcdn.com",
)

# Hosts that positively indicate a restream rather than merely being unlisted.
_RESTREAM_HOSTS = (
    "nghk.ai", "mcquack.net", "bozztv.com", "damitv.st", "aynascope.net",
    "kazmazpaz.ru", "workers.dev", "streamhostingcdn.top", "cinerama.uz",
    "pdtvhd.com", "tvabierta.net", "esite-lab.com",
)

# URL shorteners: a licensee never fronts its own stream with one, and it hides
# the real origin from this check. "Sky Sports Football" behind short.gy is not
# Sky.
_SHORTENERS = ("short.gy", "s.gy", "bit.ly", "tinyurl.com", "cutt.ly", "t.co")

_THROWAWAY_TLDS = (".top", ".xyz", ".cc", ".club", ".live", ".stream", ".buzz", ".icu")

_IPV4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

OFFICIAL = "official"
RESTREAM = "restream"
UNVERIFIED = "unverified"


def _suffix_match(host: str, suffixes: tuple[str, ...]) -> bool:
    return any(host == s or host.endswith("." + s) for s in suffixes)


def classify(url: str | None) -> str:
    """Classify one stream URL. Unparseable input is treated as unverified."""
    if not url:
        return UNVERIFIED
    try:
        parsed = urlparse(url)
    except Exception:
        return UNVERIFIED

    host = (parsed.hostname or "").lower()
    if not host:
        return UNVERIFIED

    # Bad signals first: a bare IP on a high port is never a licensee, even if
    # some suffix below would otherwise match.
    if _IPV4.match(host):
        return RESTREAM
    if _suffix_match(host, _SHORTENERS) or _suffix_match(host, _RESTREAM_HOSTS):
        return RESTREAM
    if host.endswith(_THROWAWAY_TLDS):
        return RESTREAM
    if parsed.port and parsed.port not in (80, 443):
        return RESTREAM

    if _suffix_match(host, _OFFICIAL_HOSTS):
        return OFFICIAL
    return UNVERIFIED


def is_playable(origin: str) -> bool:
    """Only broadcaster-owned / licensed origins may be streamed."""
    return origin == OFFICIAL
