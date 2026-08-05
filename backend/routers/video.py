"""
Match videos sourced from the free Scorebat Video API.

These are embeddable Scorebat player iframes (highlights + some live), NOT HLS
streams — the frontend renders `embed` in an <iframe>, not the HlsPlayer.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.scorebat import get_match_videos

router = APIRouter(prefix="/api/video", tags=["Video"])


class VideoClip(BaseModel):
    id: str | None = None
    title: str | None = None
    embed: str | None = None
    embed_url: str | None = None


class MatchVideo(BaseModel):
    title: str | None = None
    competition: str | None = None
    date: str | None = None
    thumbnail: str | None = None
    matchview_url: str | None = None
    embed: str | None = None        # first clip's iframe HTML
    embed_url: str | None = None    # first clip's player src (for a clean <iframe>)
    clips: list[VideoClip] = []


@router.get("/feed", response_model=list[MatchVideo])
async def video_feed(competition: str | None = None, limit: int = 50):
    """
    Recent match videos. Optional `competition` substring filter, e.g.
    /api/video/feed?competition=Champions%20League
    """
    try:
        return await get_match_videos(competition=competition, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scorebat API unavailable: {e}")
