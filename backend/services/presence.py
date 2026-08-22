"""
Live viewer presence — how many people are on GoalStream right now, and which
country they are watching from, printed straight to the backend terminal.

Every HTTP request and WebSocket connect stamps the caller's IP into an
in-memory table. An IP counts as "online" while it has been seen within
ACTIVE_WINDOW seconds, and as "watching" while its recent requests hit a
stream/video path. Country is resolved once per IP and cached for the process
lifetime:

  1. CF-IPCountry header — instant and free when the app sits behind Cloudflare
  2. ip-api.com/json    — free, no key, 45 req/min, resolved in the background

Private / loopback addresses are reported as "Local network" and are never sent
to the geo service.

Telemetry only: the proxy headers below are attacker-controllable unless the app
really is behind a trusted proxy, so never use any of this for access control.
"""
import asyncio
import contextlib
import ipaddress
import time

import httpx

ACTIVE_WINDOW = 120        # seconds an IP stays "online" after its last request
REPORT_EVERY = 30          # seconds between terminal reports
GEO_TIMEOUT = 4
MAX_TRACKED = 5000         # hard cap so a scan can't grow the table without bound

# Hitting any of these means the visitor is pulling video, not just browsing.
WATCH_PREFIXES = ("/api/proxy/", "/api/iptv", "/api/video", "/api/streams", "/ws/")

# ip -> {"last_seen", "first_seen", "last_watch", "hits", "path", "agent"}
_visitors: dict[str, dict] = {}
# ip -> (country_name, country_code)
_geo: dict[str, tuple[str, str]] = {}
_geo_inflight: set[str] = set()
_geo_tried: set[str] = set()      # one lookup per IP, success or not

_last_printed: str = ""


# ── IP helpers ───────────────────────────────────────────────────────────────

def client_ip(headers, fallback: str | None) -> str:
    """Best-effort real client IP, honouring the usual proxy headers."""
    for name in ("cf-connecting-ip", "x-real-ip"):
        value = headers.get(name)
        if value:
            return value.strip()
    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return fallback or "unknown"


def _is_local(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True                      # "unknown" / malformed — don't geo-lookup it
    return addr.is_private or addr.is_loopback or addr.is_link_local


def country_of(ip: str) -> tuple[str, str]:
    if _is_local(ip):
        return ("Local network", "--")
    return _geo.get(ip, ("Resolving", "??"))


# ── Geo lookup ───────────────────────────────────────────────────────────────

async def _resolve_country(ip: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=GEO_TIMEOUT) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,country,countryCode"},
            )
            data = resp.json()
        if data.get("status") == "success":
            _geo[ip] = (data.get("country") or "Unknown", data.get("countryCode") or "??")
        else:
            _geo.setdefault(ip, ("Unknown", "??"))
    except Exception:
        # Never clobber a Cloudflare hint we already have with "Unknown".
        _geo.setdefault(ip, ("Unknown", "??"))
    finally:
        _geo_inflight.discard(ip)


def _schedule_geo(ip: str) -> None:
    """At most one geo lookup per IP, ever — even a Cloudflare-hinted one, so the
    bare country code becomes a readable country name."""
    if ip in _geo_tried or _is_local(ip):
        return
    _geo_tried.add(ip)
    _geo_inflight.add(ip)
    try:
        asyncio.get_running_loop().create_task(_resolve_country(ip))
    except RuntimeError:                 # no loop (shouldn't happen in ASGI) — skip
        _geo_tried.discard(ip)
        _geo_inflight.discard(ip)


# ── Recording ────────────────────────────────────────────────────────────────

def touch(ip: str, path: str = "", country_hint: str | None = None,
          user_agent: str = "") -> None:
    """Record one request from `ip`. Cheap and non-blocking."""
    now = time.time()

    if country_hint and ip not in _geo and not _is_local(ip):
        code = country_hint.strip().upper()
        if code and code != "XX":
            _geo[ip] = (code, code)      # Cloudflare gives the code only
    _schedule_geo(ip)

    entry = _visitors.get(ip)
    if entry is None:
        if len(_visitors) >= MAX_TRACKED:
            _prune(now)
        if len(_visitors) >= MAX_TRACKED:
            return
        entry = _visitors[ip] = {"first_seen": now, "last_watch": 0.0, "hits": 0}

    entry["last_seen"] = now
    entry["hits"] += 1
    entry["path"] = path
    entry["agent"] = user_agent[:80]
    if path.startswith(WATCH_PREFIXES):
        entry["last_watch"] = now


def _prune(now: float) -> None:
    stale = [ip for ip, e in _visitors.items() if now - e["last_seen"] > ACTIVE_WINDOW * 4]
    for ip in stale:
        _visitors.pop(ip, None)

    # The geo cache outlives visitors on purpose (returning users resolve for
    # free), but not forever — drop it wholesale once it dwarfs the live table.
    if len(_geo_tried) > MAX_TRACKED * 2:
        keep = set(_visitors)
        _geo_tried.intersection_update(keep)
        for ip in [ip for ip in _geo if ip not in keep]:
            _geo.pop(ip, None)


# ── Reporting ────────────────────────────────────────────────────────────────

def _active(now: float) -> list[tuple[str, dict]]:
    return [(ip, e) for ip, e in _visitors.items() if now - e["last_seen"] <= ACTIVE_WINDOW]


def snapshot() -> dict:
    """Public summary — counts only, no IP addresses."""
    now = time.time()
    active = _active(now)

    by_country: dict[tuple[str, str], int] = {}
    for ip, _ in active:
        key = country_of(ip)
        by_country[key] = by_country.get(key, 0) + 1

    return {
        "online": len(active),
        "watching": sum(1 for _, e in active if now - e["last_watch"] <= ACTIVE_WINDOW),
        "countries": [
            {"country": name, "code": code, "viewers": n}
            for (name, code), n in sorted(by_country.items(), key=lambda kv: -kv[1])
        ],
        "window_seconds": ACTIVE_WINDOW,
    }


def detail() -> dict:
    """Full per-visitor detail, including IPs — admin only."""
    now = time.time()
    visitors = []
    for ip, e in sorted(_active(now), key=lambda kv: kv[1]["last_seen"], reverse=True):
        name, code = country_of(ip)
        visitors.append({
            "ip": ip,
            "country": name,
            "country_code": code,
            "hits": e["hits"],
            "last_path": e.get("path", ""),
            "watching": now - e["last_watch"] <= ACTIVE_WINDOW,
            "seconds_since_seen": round(now - e["last_seen"], 1),
            "session_seconds": round(now - e["first_seen"], 1),
            "user_agent": e.get("agent", ""),
        })
    return {**snapshot(), "visitors": visitors}


WIDTH = 58


def _render(snap: dict) -> str:
    head = f" GoalStream network | online: {snap['online']}  watching: {snap['watching']}"
    lines = ["-" * WIDTH, head.ljust(WIDTH - 9) + time.strftime("%H:%M:%S"), "-" * WIDTH]
    if not snap["countries"]:
        lines.append("  (nobody connected)")
    for c in snap["countries"]:
        label = f"{c['country']} ({c['code']})"
        lines.append(f"  {label:<34}{c['viewers']:>3}  " + "#" * min(c["viewers"], 16))
    lines.append("-" * WIDTH)
    return "\n".join(lines)


def _signature(snap: dict) -> str:
    """Everything about a report except the clock — used to suppress idle spam."""
    return f"{snap['online']}/{snap['watching']}/" + ",".join(
        f"{c['code']}:{c['viewers']}" for c in snap["countries"]
    )


async def report_loop(interval: int = REPORT_EVERY) -> None:
    """Print a live viewer summary to the backend terminal, forever."""
    global _last_printed
    while True:
        with contextlib.suppress(Exception):
            snap = snapshot()
            sig = _signature(snap)
            # Keep ticking while anyone is on the site; once it empties out, print
            # the drop to zero once and then stay quiet until someone returns.
            if snap["online"] or sig != _last_printed:
                print(_render(snap), flush=True)
                _last_printed = sig
            _prune(time.time())
        await asyncio.sleep(interval)
