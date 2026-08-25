from fastapi import APIRouter, HTTPException
from typing import List, Optional
from config import LEAGUES, official_watch
from schemas import LeagueOut, MatchOut, StandingsOut
from services.football_api import (
    get_matches_by_league,
    get_standings,
    get_todays_matches,
    get_live_matches,
    search_teams,
)

router = APIRouter(prefix="/api/leagues", tags=["Leagues"])


@router.get("", response_model=List[LeagueOut])
async def list_leagues():
    return [{"code": code, **meta} for code, meta in LEAGUES.items()]


@router.get("/live", response_model=List[MatchOut])
async def live_matches():
    """All live / in-play matches across every league."""
    return await get_live_matches()


@router.get("/today", response_model=List[MatchOut])
async def todays_matches():
    """All matches scheduled for today."""
    return await get_todays_matches()


@router.get("/teams/search")
async def search(q: str):
    """Search for teams by name across all supported leagues."""
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    return await search_teams(q)


def _league(league_code: str) -> tuple[str, dict]:
    code = league_code.upper()
    meta = LEAGUES.get(code)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"League '{code}' not supported")
    return code, meta


@router.get("/{league_code}/watch")
async def league_watch(league_code: str):
    """
    Where this competition can legitimately be watched.

    The free catalog holds no rights holder for any competition, so when a
    league has nothing playable this is the app's real answer rather than a
    guessed channel. Malaysian providers lead — see config.OFFICIAL_WATCH.
    """
    code = league_code.upper()
    return {"league_code": code,
            "league_name": LEAGUES.get(code, {}).get("name", code),
            "providers": official_watch(code)}


@router.get("/{league_code}/matches", response_model=List[MatchOut])
async def league_matches(league_code: str, matchday: Optional[int] = None):
    code, meta = _league(league_code)
    if not meta.get("fixtures", True):
        return []          # browsable competition, no fixture feed behind it
    try:
        return await get_matches_by_league(code, matchday)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Football API error: {exc}")


@router.get("/{league_code}/standings", response_model=StandingsOut)
async def league_standings(league_code: str):
    code, meta = _league(league_code)
    if not meta.get("fixtures", True):
        return {"league_code": code, "league_name": meta["name"], "season": "", "table": []}
    try:
        return await get_standings(code)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Football API error: {exc}")
