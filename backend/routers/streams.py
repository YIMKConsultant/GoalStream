from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Stream, User
from schemas import StreamCreate, StreamOut
from auth import require_admin

router = APIRouter(prefix="/api/streams", tags=["Streams"])


@router.post("", response_model=StreamOut, status_code=201)
async def add_stream(
    body: StreamCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin-only: attach a stream URL to a match."""
    stream = Stream(**body.model_dump(), added_by=admin.id)
    db.add(stream)
    await db.commit()
    await db.refresh(stream)
    return stream


@router.get("/match/{match_id}", response_model=list[StreamOut])
async def streams_for_match(match_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Stream).where(Stream.match_id == match_id, Stream.is_active.is_(True))
    )
    return result.scalars().all()


@router.delete("/{stream_id}", status_code=204)
async def delete_stream(
    stream_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(Stream).where(Stream.id == stream_id))
    stream = result.scalar_one_or_none()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    stream.is_active = False
    await db.commit()


@router.put("/{stream_id}", response_model=StreamOut)
async def update_stream(
    stream_id: int,
    body: StreamCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(Stream).where(Stream.id == stream_id))
    stream = result.scalar_one_or_none()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    for field, value in body.model_dump().items():
        setattr(stream, field, value)
    await db.commit()
    await db.refresh(stream)
    return stream
