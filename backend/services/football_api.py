"""
Wrapper around football-data.org v4 REST API.
Free tier: 10 req/min, covers PL, CL, EL, and more.
Sign up at https://www.football-data.org/ to get your free API key.
"""
import httpx
from typing import Optional
from cachetools import TTLCache
from config import settings, LEAGUES

_cache: TTLCache = TTLCache(maxsize=256, ttl=60)   # 60-second cache to respect rate limits
_headers = {"X-Auth-Token": settings.football_api_key}
BASE = settings.football_api_base_url


def _cached(key: str):
    return _cache.get(key)


def _store(key: str, value):
    _cache[key] = value
    return value


async def _get(path: str) -> dict:
    key = path
    cached = _cached(key)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BASE}{path}", headers=_headers)
        resp.raise_for_status()
        data = resp.json()
        return _store(key, data)


# ── Public helpers ────────────────────────────────────────────────────────────

async def get_matches_by_league(league_code: str, matchday: Optional[int] = None) -> list:
    path = f"/competitions/{league_code}/matches"
    if matchday:
        path += f"?matchday={matchday}"
    data = await _get(path)
    return _parse_matches(data.get("matches", []), league_code)


async def get_live_matches() -> list:
    """Fetch all currently live matches across all supported leagues."""
    data = await _get("/matches?status=IN_PLAY,PAUSED")
    return _parse_matches(data.get("matches", []))


async def get_todays_matches() -> list:
    data = await _get("/matches")        # defaults to today at football-data.org
    return _parse_matches(data.get("matches", []))


async def get_match_detail(match_id: int) -> dict:
    data = await _get(f"/matches/{match_id}")
    matches = _parse_matches([data], data.get("competition", {}).get("code", ""))
    return matches[0] if matches else {}


async def get_standings(league_code: str) -> dict:
    data = await _get(f"/competitions/{league_code}/standings")
    season = data.get("season", {})
    standings_raw = data.get("standings", [])

    total_table = next(
        (s for s in standings_raw if s.get("type") == "TOTAL"), {}
    )
    table = []
    for row in total_table.get("table", []):
        team = row.get("team", {})
        table.append({
            "position": row.get("position"),
            "team": {
                "id": team.get("id"),
                "name": team.get("name"),
                "shortName": team.get("shortName"),
                "crest": team.get("crest"),
            },
            "playedGames": row.get("playedGames"),
            "won": row.get("won"),
            "draw": row.get("draw"),
            "lost": row.get("lost"),
            "points": row.get("points"),
            "goalDifference": row.get("goalDifference"),
            "goalsFor": row.get("goalsFor"),
            "goalsAgainst": row.get("goalsAgainst"),
        })

    league_meta = LEAGUES.get(league_code, {})
    return {
        "league_code": league_code,
        "league_name": league_meta.get("name", league_code),
        "season": f"{season.get('startDate', '')[:4]}/{season.get('endDate', '')[:4]}",
        "table": table,
    }


async def get_team_matches(team_id: int, status: str = "") -> list:
    path = f"/teams/{team_id}/matches"
    if status:
        path += f"?status={status}"
    data = await _get(path)
    return _parse_matches(data.get("matches", []))


async def search_teams(name: str) -> list:
    """Search across all supported leagues for teams matching name."""
    results = []
    for code in LEAGUES:
        try:
            data = await _get(f"/competitions/{code}/teams")
            for team in data.get("teams", []):
                if name.lower() in team.get("name", "").lower():
                    results.append({
                        "id": team["id"],
                        "name": team["name"],
                        "shortName": team.get("shortName"),
                        "crest": team.get("crest"),
                        "league": code,
                    })
        except Exception:
            continue
    return results


# ── Internal parser ───────────────────────────────────────────────────────────

def _parse_matches(raw: list, default_league: str = "") -> list:
    matches = []
    for m in raw:
        competition = m.get("competition", {})
        league_code = competition.get("code", default_league)
        league_meta = LEAGUES.get(league_code, {})

        home = m.get("homeTeam", {})
        away = m.get("awayTeam", {})
        score = m.get("score", {})
        ft = score.get("fullTime", {})
        ht = score.get("halfTime", {})

        matches.append({
            "id": m.get("id"),
            "league_code": league_code,
            "league_name": league_meta.get("name", competition.get("name", league_code)),
            "matchday": m.get("matchday"),
            "stage": m.get("stage"),
            "status": m.get("status"),
            "utcDate": m.get("utcDate", ""),
            "homeTeam": {
                "id": home.get("id") or 0,
                "name": home.get("name") or "TBD",
                "shortName": home.get("shortName"),
                "crest": home.get("crest"),
            },
            "awayTeam": {
                "id": away.get("id") or 0,
                "name": away.get("name") or "TBD",
                "shortName": away.get("shortName"),
                "crest": away.get("crest"),
            },
            "score": {
                "winner": score.get("winner"),
                "duration": score.get("duration"),
                "fullTime": {"home": ft.get("home"), "away": ft.get("away")},
                "halfTime": {"home": ht.get("home"), "away": ht.get("away")},
            },
            "venue": m.get("venue"),
            "referees": [r.get("name", "") for r in m.get("referees", [])],
            "has_stream": False,   # populated by stream service
        })
    return matches
