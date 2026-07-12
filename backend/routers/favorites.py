from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import FavoriteTeam, User
from schemas import FavoriteCreate, FavoriteOut
from auth import get_current_user

router = APIRouter(prefix="/api/favorites", tags=["Favorites"])


@router.get("", response_model=list[FavoriteOut])
async def list_favorites(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(FavoriteTeam).where(FavoriteTeam.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=FavoriteOut, status_code=201)
async def add_favorite(
    body: FavoriteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = await db.execute(
        select(FavoriteTeam).where(
            FavoriteTeam.user_id == user.id,
            FavoriteTeam.team_id == body.team_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Team already in favorites")

    fav = FavoriteTeam(user_id=user.id, **body.model_dump())
    db.add(fav)
    await db.commit()
    await db.refresh(fav)
    return fav


@router.delete("/{team_id}", status_code=204)
async def remove_favorite(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FavoriteTeam).where(
            FavoriteTeam.user_id == user.id,
            FavoriteTeam.team_id == team_id,
        )
    )
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    await db.delete(fav)
    await db.commit()
