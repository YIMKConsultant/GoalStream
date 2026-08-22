"""
Admin + superuser control plane.

Admins manage people and channels. Superusers additionally hold the API
credentials and decide who is an admin — see auth.require_superuser.
"""
import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_admin, require_superuser
from config import LEAGUES, TIERS
from database import get_db
from models import ChannelPolicy, FavoriteTeam, LeagueChannelMap, User, UserChannelGrant
from schemas import (
    AdminChannelOut,
    AdminUserOut,
    ChannelPolicyIn,
    GrantIn,
    GrantOut,
    SettingsIn,
    SettingsOut,
    SettingValueOut,
    UserUpdate,
)
from services import access, ai_client, ai_discovery, football_api, presence, settings_store
from services.iptv_org import get_sports_channels

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ── Overview ────────────────────────────────────────────────────────────────

@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    """Headline numbers for the dashboard landing page."""
    async def count(model) -> int:
        return (await db.execute(select(func.count()).select_from(model))).scalar_one()

    by_tier = await db.execute(select(User.tier, func.count()).group_by(User.tier))
    try:
        channel_total = len(await get_sports_channels())
    except Exception:
        channel_total = 0

    return {
        "users": await count(User),
        "users_by_tier": {tier: n for tier, n in by_tier.all()},
        "admins": (await db.execute(
            select(func.count()).select_from(User).where(User.is_admin.is_(True))
        )).scalar_one(),
        "restricted_channels": await count(ChannelPolicy),
        "grants": await count(UserChannelGrant),
        "favorites": await count(FavoriteTeam),
        "catalog_channels": channel_total,
        "leagues": len(LEAGUES),
        "presence": presence.snapshot(),
        "tiers": list(TIERS),
    }


# ── Users ───────────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    q: str | None = Query(None, description="Filter by username or email"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(User).order_by(User.id)
    if q:
        needle = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(User.username).like(needle) | func.lower(User.email).like(needle)
        )
    return (await db.execute(stmt)).scalars().all()


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
):
    """
    Change a user's tier or status. Promoting to admin/superuser is superuser
    territory, and nobody may strip their own privileges — that's the classic way
    to lock everyone out of the dashboard.
    """
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    changes = body.model_dump(exclude_unset=True)

    if ("is_admin" in changes or "is_superuser" in changes) and not actor.is_superuser:
        raise HTTPException(status_code=403, detail="Only a superuser can change admin rights")

    if user.id == actor.id:
        for field in ("is_admin", "is_superuser", "is_active"):
            if field in changes and not changes[field]:
                raise HTTPException(
                    status_code=400,
                    detail=f"You can't remove your own {field.replace('_', ' ')}",
                )

    if changes.get("is_superuser") is False:
        remaining = (await db.execute(
            select(func.count()).select_from(User).where(
                User.is_superuser.is_(True), User.id != user_id
            )
        )).scalar_one()
        if remaining == 0:
            raise HTTPException(status_code=400, detail="That's the last superuser")

    if "tier" in changes and changes["tier"] not in TIERS:
        raise HTTPException(status_code=400, detail=f"tier must be one of {list(TIERS)}")

    for field, value in changes.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_superuser),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == actor.id:
        raise HTTPException(status_code=400, detail="You can't delete your own account")

    await db.execute(delete(UserChannelGrant).where(UserChannelGrant.user_id == user_id))
    await db.execute(delete(FavoriteTeam).where(FavoriteTeam.user_id == user_id))
    await db.delete(user)
    await db.commit()


# ── Channels ────────────────────────────────────────────────────────────────

@router.get("/channels", response_model=list[AdminChannelOut])
async def list_channels(
    q: str | None = Query(None, description="Filter by channel name or country"),
    tier: str | None = Query(None, description="Only channels at this tier"),
    limit: int = Query(200, le=1000),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    The full upstream catalog joined with our policy rows. Channels an admin
    hasn't touched come back at the default tier with no row behind them.
    """
    try:
        channels = await get_sports_channels()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"iptv-org API unavailable: {e}")

    policies = await access.load_policies(db)
    default_tier = settings_store.default_channel_tier()

    rows = []
    for ch in channels:
        policy = policies.get(ch["id"])
        row = AdminChannelOut(
            id=ch["id"],
            name=ch["name"],
            country=ch.get("country"),
            tier=policy.tier if policy else default_tier,
            hidden=bool(policy and policy.hidden),
            note=policy.note if policy else "",
            customised=policy is not None,
        )
        if q:
            needle = q.lower()
            if needle not in row.name.lower() and needle not in (row.country or "").lower():
                continue
        if tier and row.tier != tier:
            continue
        rows.append(row)

    return rows[offset:offset + limit]


@router.put("/channels/{channel_id}/policy", response_model=AdminChannelOut)
async def set_channel_policy(
    channel_id: str,
    body: ChannelPolicyIn,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
):
    """Set the tier a channel needs, or hide it from every listing."""
    if body.tier not in TIERS:
        raise HTTPException(status_code=400, detail=f"tier must be one of {list(TIERS)}")

    policy = await db.get(ChannelPolicy, channel_id)
    if policy is None:
        policy = ChannelPolicy(channel_id=channel_id)
        db.add(policy)
    policy.tier = body.tier
    policy.hidden = body.hidden
    policy.note = body.note
    policy.updated_by = actor.id
    await db.commit()

    name, country = channel_id, None
    try:
        for ch in await get_sports_channels():
            if ch["id"] == channel_id:
                name, country = ch["name"], ch.get("country")
                break
    except Exception:
        pass

    return AdminChannelOut(
        id=channel_id, name=name, country=country, tier=policy.tier,
        hidden=policy.hidden, note=policy.note, customised=True,
    )


@router.delete("/channels/{channel_id}/policy", status_code=204)
async def clear_channel_policy(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Drop the override so the channel falls back to the default tier."""
    policy = await db.get(ChannelPolicy, channel_id)
    if policy is not None:
        await db.delete(policy)
        await db.commit()


# ── Per-user grants ─────────────────────────────────────────────────────────

@router.get("/users/{user_id}/grants", response_model=list[GrantOut])
async def list_grants(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(
        select(UserChannelGrant).where(UserChannelGrant.user_id == user_id)
    )
    return result.scalars().all()


@router.put("/users/{user_id}/grants/{channel_id}", response_model=GrantOut)
async def set_grant(
    user_id: int,
    channel_id: str,
    body: GrantIn,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
):
    """Allow or block one channel for one user, overriding their tier."""
    if body.mode not in ("allow", "block"):
        raise HTTPException(status_code=400, detail="mode must be 'allow' or 'block'")
    if await db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (await db.execute(
        select(UserChannelGrant).where(
            UserChannelGrant.user_id == user_id,
            UserChannelGrant.channel_id == channel_id,
        )
    )).scalar_one_or_none()

    if existing is None:
        existing = UserChannelGrant(
            user_id=user_id, channel_id=channel_id, mode=body.mode, created_by=actor.id
        )
        db.add(existing)
    else:
        existing.mode = body.mode
    await db.commit()
    await db.refresh(existing)
    return existing


@router.delete("/users/{user_id}/grants/{channel_id}", status_code=204)
async def clear_grant(
    user_id: int,
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await db.execute(
        delete(UserChannelGrant).where(
            UserChannelGrant.user_id == user_id,
            UserChannelGrant.channel_id == channel_id,
        )
    )
    await db.commit()


# ── Settings (superuser only) ───────────────────────────────────────────────

@router.get("/settings", response_model=SettingsOut)
async def read_settings(_: User = Depends(require_superuser)):
    """Current effective settings. Secrets come back masked, never in full."""
    return SettingsOut(settings=[
        SettingValueOut(
            key=key,
            label=label,
            secret=secret,
            value=settings_store.mask(settings_store.get(key)) if secret
            else settings_store.get(key),
            overridden=settings_store.is_overridden(key),
        )
        for key, (label, secret) in settings_store.EDITABLE.items()
    ])


@router.put("/settings", response_model=SettingsOut)
async def write_settings(
    body: SettingsIn,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_superuser),
):
    """
    Save API credential overrides. Takes effect immediately — readers pull these
    per request rather than caching them at import.
    """
    unknown = set(body.values) - set(settings_store.EDITABLE)
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown settings: {sorted(unknown)}")

    tier = body.values.get("default_channel_tier")
    if tier is not None and tier not in TIERS:
        raise HTTPException(status_code=400, detail=f"tier must be one of {list(TIERS)}")

    await settings_store.set_many(db, body.values, actor.id)
    football_api.clear_cache()   # stale responses were fetched with the old key
    return await read_settings(actor)


# ── AI (superuser only) ─────────────────────────────────────────────────────

@router.get("/ai/status")
async def ai_status(_: User = Depends(require_superuser)):
    """Whether a Claude key is configured, and which model it will use."""
    return {
        "configured": ai_client.is_configured(),
        "model": ai_client.model(),
        "key_preview": settings_store.mask(ai_client.api_key()),
    }


@router.post("/ai/test")
async def ai_test(_: User = Depends(require_superuser)):
    """Round-trip the configured key so a bad paste fails here, not mid-run."""
    try:
        return await ai_client.check_connection()
    except ai_client.AINotConfigured as e:
        raise HTTPException(status_code=400, detail=str(e))
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=400, detail="Anthropic rejected that API key.")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Anthropic rate limit — try again shortly.")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {e}")


@router.post("/ai/discover/{league_code}")
async def ai_discover(
    league_code: str,
    persist: bool = Query(True, description="Save the result as this league's channel map"),
    min_confidence: str = Query("low", pattern="^(low|medium|high)$"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superuser),
):
    """
    Have Claude read the free catalog and pick the channels that carry this
    competition. Replaces the hand-maintained keyword lists for this league.
    """
    try:
        return await ai_discovery.discover_for_league(
            db, league_code, min_confidence=min_confidence, persist=persist
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ai_client.AINotConfigured as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ai_client.AIRefused as e:
        raise HTTPException(status_code=422, detail=f"Claude declined: {e}")
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=400, detail="Anthropic rejected the configured API key.")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {e}")


@router.get("/ai/map/{league_code}")
async def ai_map(
    league_code: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """The stored channel map for a league — empty means keyword fallback."""
    result = await db.execute(
        select(LeagueChannelMap)
        .where(LeagueChannelMap.league_code == league_code.upper())
        .order_by(LeagueChannelMap.rank)
    )
    rows = result.scalars().all()
    try:
        names = {c["id"]: c for c in await get_sports_channels()}
    except Exception:
        names = {}
    return {
        "league_code": league_code.upper(),
        "using_ai_map": bool(rows),
        "channels": [{
            "channel_id": r.channel_id,
            "name": names.get(r.channel_id, {}).get("name", r.channel_id),
            "country": names.get(r.channel_id, {}).get("country"),
            "source": r.source,
            "confidence": r.confidence,
            "note": r.note,
        } for r in rows],
    }


@router.delete("/ai/map/{league_code}", status_code=204)
async def clear_ai_map(
    league_code: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superuser),
):
    """Drop the map so the league falls back to the keyword heuristic."""
    await db.execute(
        delete(LeagueChannelMap).where(LeagueChannelMap.league_code == league_code.upper())
    )
    await db.commit()
