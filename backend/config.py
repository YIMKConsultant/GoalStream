from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    football_api_key: str = ""
    football_api_base_url: str = "https://api.football-data.org/v4"

    # Free token from https://www.scorebat.com/video-api/ — unlocks a fresh,
    # domain-authorised video feed. Empty falls back to the frozen legacy feed.
    scorebat_token: str = ""

    secret_key: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 10080  # 7 days

    database_url: str = "sqlite+aiosqlite:///./football_watch.db"

    app_env: str = "development"
    cors_origins: str = "http://localhost:8081,http://localhost:19006,exp://localhost:8081"

    # Live viewer tracking printed to the backend terminal (services/presence.py).
    presence_tracking: bool = True
    presence_report_seconds: int = 30

    # Signs /api/proxy/stream URLs so the proxy can't be used to fetch arbitrary
    # URLs (which would bypass every channel restriction). Falls back to
    # secret_key when unset.
    proxy_signing_key: str = ""
    proxy_signature_ttl_hours: int = 12

    @property
    def signing_key(self) -> str:
        return self.proxy_signing_key or self.secret_key

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()

# Access tiers, lowest privilege first. A channel's tier is the minimum a viewer
# needs; a user's tier is what they hold. "public" is the only tier a visitor who
# has not signed in can reach — so marking a channel "free" or above is what
# keeps it off the no-sign-in watching page.
TIERS = ("public", "free", "member", "premium")
ANONYMOUS_TIER = "public"
DEFAULT_USER_TIER = "free"


def tier_rank(tier: str) -> int:
    """Rank of a tier; unknown values sort as the most restrictive."""
    try:
        return TIERS.index(tier)
    except ValueError:
        return len(TIERS)

# Supported leagues — code maps to football-data.org competition codes.
#
# `fixtures` says whether football-data.org serves this competition on our plan.
# The ones marked False are still browsable (channels, "who's airing it") but
# football-data.org has no feed for them, so fixtures/standings come back empty
# instead of a 502. Flip one to True the moment a provider that carries it is
# wired up — nothing else needs to change.
LEAGUES = {
    "PL":   {"name": "Premier League",        "country": "England",     "emblem": "", "fixtures": True},
    # Every competition football-data.org returns from /matches must be listed
    # here, or it renders on the Live page with a code nothing else can resolve:
    # `_parse_matches` falls back to the provider's own name, but
    # /iptv/for-league/{code} then finds no hints and /leagues/{code}/matches
    # 404s. That is what made every Championship fixture unwatchable.
    "ELC":  {"name": "Championship",          "country": "England",     "emblem": "", "fixtures": True},
    "CL":   {"name": "UEFA Champions League", "country": "Europe",      "emblem": "", "fixtures": True},
    "EC":   {"name": "European Championship", "country": "Europe",      "emblem": "", "fixtures": True},
    "EL":   {"name": "UEFA Europa League",    "country": "Europe",      "emblem": "", "fixtures": True},
    "ECL":  {"name": "UEFA Conference League","country": "Europe",      "emblem": "", "fixtures": True},
    "PD":   {"name": "La Liga",               "country": "Spain",       "emblem": "", "fixtures": True},
    "BL1":  {"name": "Bundesliga",            "country": "Germany",     "emblem": "", "fixtures": True},
    "SA":   {"name": "Serie A",               "country": "Italy",       "emblem": "", "fixtures": True},
    "FL1":  {"name": "Ligue 1",               "country": "France",      "emblem": "", "fixtures": True},
    "DED":  {"name": "Eredivisie",            "country": "Netherlands", "emblem": "", "fixtures": True},
    "PPL":  {"name": "Primeira Liga",         "country": "Portugal",    "emblem": "", "fixtures": True},
    "BSA":  {"name": "Brasileirão Série A",   "country": "Brazil",      "emblem": "", "fixtures": True},
    "WC":   {"name": "FIFA World Cup",        "country": "World",       "emblem": "", "fixtures": True},
    # Added competitions — football-data.org does not carry these.
    "SPL":  {"name": "Saudi Pro League",      "country": "Saudi Arabia","emblem": "", "fixtures": False},
    "MLS":  {"name": "Major League Soccer",   "country": "USA & Canada","emblem": "", "fixtures": False},
    "CAFP": {"name": "CAF Premier League",    "country": "Africa",      "emblem": "", "fixtures": False},
    "CAFW": {"name": "CAF Women's Champions League", "country": "Africa", "emblem": "", "fixtures": False},
    "WWC":  {"name": "FIFA Women's World Cup","country": "World",       "emblem": "", "fixtures": False},
}


# Where a competition is LEGITIMATELY watchable, since the free catalog carries
# no rights holder for any of them (measured: 0 across all 19 leagues).
#
# This is the app's actual answer to "where can I watch this". Ordered with the
# viewer's own region first — GoalStream is used from Malaysia, so sooka/Astro
# and RTM lead, with the origin-country broadcaster after them for reference.
# `free` marks the ones that cost nothing, which is what most viewers want to
# see first.
OFFICIAL_WATCH = {
    "_default": [
        {"name": "sooka", "region": "MY", "url": "https://sooka.my/", "free": False},
        {"name": "Astro GO", "region": "MY", "url": "https://astrogo.astro.com.my/", "free": False},
    ],
    "PL": [
        {"name": "Astro / sooka VIP+Sports", "region": "MY", "url": "https://sooka.my/", "free": False},
        {"name": "Sky Sports", "region": "UK", "url": "https://www.skysports.com/", "free": False},
        {"name": "USA Network / Peacock", "region": "US", "url": "https://www.peacocktv.com/sports/premier-league", "free": False},
    ],
    "ELC": [
        {"name": "Sky Sports", "region": "UK", "url": "https://www.skysports.com/", "free": False},
        {"name": "ESPN+", "region": "US", "url": "https://plus.espn.com/", "free": False},
    ],
    "CL": [
        {"name": "sooka VIP+Sports", "region": "MY", "url": "https://sooka.my/", "free": False},
        {"name": "Paramount+", "region": "US", "url": "https://www.paramountplus.com/", "free": False},
    ],
    "EL":  [{"name": "sooka VIP+Sports", "region": "MY", "url": "https://sooka.my/", "free": False}],
    "ECL": [{"name": "sooka VIP+Sports", "region": "MY", "url": "https://sooka.my/", "free": False}],
    "PD":  [
        {"name": "Real Madrid TV", "region": "Worldwide", "url": "https://www.realmadrid.com/en/tv", "free": True},
        {"name": "LaLiga TV / Astro", "region": "MY", "url": "https://sooka.my/", "free": False},
    ],
    "BL1": [{"name": "Bundesliga on Astro", "region": "MY", "url": "https://sooka.my/", "free": False}],
    "SA":  [{"name": "Serie A on Astro", "region": "MY", "url": "https://sooka.my/", "free": False}],
    "FL1": [{"name": "Ligue 1 on beIN", "region": "MY", "url": "https://sooka.my/", "free": False}],
    # RTM holds Malaysian free-to-air rights: every World Cup 2026 match, free.
    "WC":  [{"name": "RTM Klik", "region": "MY", "url": "https://rtmklik.rtm.gov.my/", "free": True},
            {"name": "Unifi TV", "region": "MY", "url": "https://unifi.com.my/unifi-tv", "free": False}],
    "WWC": [{"name": "RTM Klik", "region": "MY", "url": "https://rtmklik.rtm.gov.my/", "free": True}],
    "BSA": [{"name": "CazeTV (YouTube)", "region": "Worldwide", "url": "https://www.youtube.com/@CazeTV", "free": True}],
    "MLS": [{"name": "MLS Season Pass", "region": "Worldwide", "url": "https://www.apple.com/apple-tv-plus/mls-season-pass/", "free": False}],
}


def official_watch(league_code: str) -> list[dict]:
    """Legitimate places to watch a competition, region-preferred."""
    return OFFICIAL_WATCH.get(league_code.upper(), OFFICIAL_WATCH["_default"])
