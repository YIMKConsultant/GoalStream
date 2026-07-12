from fastapi import APIRouter, HTTPException
from typing import List, Optional
from config import LEAGUES
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


@router.get("/{league_code}/matches", response_model=List[MatchOut])
async def league_matches(league_code: str, matchday: Optional[int] = None):
    code = league_code.upper()
    if code not in LEAGUES:
        raise HTTPException(status_code=404, detail=f"League '{code}' not supported")
    try:
        return await get_matches_by_league(code, matchday)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Football API error: {exc}")


@router.get("/{league_code}/standings", response_model=StandingsOut)
async def league_standings(league_code: str):
    code = league_code.upper()
    if code not in LEAGUES:
        raise HTTPException(status_code=404, detail=f"League '{code}' not supported")
    try:
        return await get_standings(code)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Football API error: {exc}")
