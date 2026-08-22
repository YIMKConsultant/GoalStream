from fastapi import APIRouter, Depends

from auth import require_admin
from models import User
from services import presence

router = APIRouter(prefix="/api/presence", tags=["Presence"])


@router.get("")
async def live_presence():
    """How many people are on the site right now, broken down by country."""
    return presence.snapshot()


@router.get("/detail")
async def presence_detail(_: User = Depends(require_admin)):
    """Per-visitor detail including IP addresses — admins only."""
    return presence.detail()
