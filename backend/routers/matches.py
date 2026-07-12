from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Stream
from schemas import MatchDetail, StreamOut
from services.football_api import get_match_detail, get_team_matches

router = APIRouter(prefix="/api/matches", tags=["Matches"])


@router.get("/{match_id}", response_model=MatchDetail)
async def match_detail(match_id: int, db: AsyncSession = Depends(get_db)):
    try:
        match = await get_match_detail(match_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Football API error: {exc}")
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Check if we have streams stored for this match
    result = await db.execute(
        select(Stream).where(Stream.match_id == match_id, Stream.is_active.is_(True))
    )
    match["has_stream"] = result.first() is not None
    return match


@router.get("/{match_id}/streams", response_model=list[StreamOut])
async def match_streams(match_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Stream).where(Stream.match_id == match_id, Stream.is_active.is_(True))
    )
    return result.scalars().all()


@router.get("/team/{team_id}", response_model=list)
async def team_matches(team_id: int, status: str = ""):
    """
    Fetch upcoming or recent matches for a team.
    status: SCHEDULED | FINISHED | IN_PLAY (empty = all)
    """
    try:
        return await get_team_matches(team_id, status.upper())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Football API error: {exc}")
