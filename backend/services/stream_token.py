"""
Short-lived signatures for proxied stream URLs.

The stream proxy used to accept any URL from anyone, which meant every channel
restriction could be sidestepped by reading a URL out of the page and calling
the proxy directly. Now a URL only passes if it carries a signature this server
issued, and it issues one only after an access check.

Channel entry points don't need this — /api/proxy/channel/{id} resolves the URL
server-side. Signatures exist for the URLs we cannot hide: the segment and key
URLs inside an HLS playlist, which the browser has to fetch itself.
"""
import base64
import hashlib
import hmac
import time

from config import settings


def _digest(url: str, referrer: str | None, ua: str | None, exp: int) -> str:
    payload = f"{url}|{referrer or ''}|{ua or ''}|{exp}".encode()
    mac = hmac.new(settings.signing_key.encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).decode().rstrip("=")[:32]


def sign(url: str, referrer: str | None = None, ua: str | None = None) -> tuple[int, str]:
    """Return (expiry_unix, signature) for a URL this caller is allowed to fetch."""
    exp = int(time.time()) + settings.proxy_signature_ttl_hours * 3600
    return exp, _digest(url, referrer, ua, exp)


def verify(url: str, referrer: str | None, ua: str | None, exp: int | None, sig: str | None) -> bool:
    """True only for an unexpired signature this server issued for this exact URL."""
    if not sig or not exp:
        return False
    if exp < int(time.time()):
        return False
    return hmac.compare_digest(_digest(url, referrer, ua, exp), sig)


# ── Channel tickets ─────────────────────────────────────────────────────────
#
# The player loads a channel through hls.js (or Safari's native HLS), and
# neither can attach an Authorization header — so a signed-in viewer would
# arrive at the proxy looking anonymous. Instead, the listing endpoints run the
# access check while they still have the caller's token, then hand back a URL
# carrying this ticket as proof that the check passed.
#
# The "channel:" prefix keeps these in their own namespace, so a segment
# signature can never be replayed as a channel ticket.

def sign_channel(channel_id: str) -> tuple[int, str]:
    exp = int(time.time()) + settings.proxy_signature_ttl_hours * 3600
    return exp, _digest(f"channel:{channel_id}", None, None, exp)


def verify_channel(channel_id: str, exp: int | None, sig: str | None) -> bool:
    if not sig or not exp or exp < int(time.time()):
        return False
    return hmac.compare_digest(_digest(f"channel:{channel_id}", None, None, exp), sig)
