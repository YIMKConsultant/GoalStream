"""
Who may watch which channel.

Two layers, checked in this order:

  1. Per-user grant  — an explicit `block` or `allow` row for (user, channel).
                       Always wins, so an admin can make a one-off exception
                       without disturbing anyone else.
  2. Tier            — the channel's required tier vs the tier the viewer holds.
                       A viewer who has not signed in holds "public", which is
                       what keeps higher-tier channels off the free page.

Admins and superusers bypass both.

Channels live in the upstream iptv-org catalog, not in our database, so a
channel with no policy row falls back to `default_channel_tier` (itself
"public" out of the box). That means nothing changes for an existing install
until an admin actually restricts something.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import ANONYMOUS_TIER, tier_rank
from models import ChannelPolicy, User, UserChannelGrant
from services import settings_store


def viewer_tier(user: User | None) -> str:
    """The tier a caller holds — anonymous visitors hold the lowest one."""
    if user is None:
        return ANONYMOUS_TIER
    return user.tier or ANONYMOUS_TIER


def is_staff(user: User | None) -> bool:
    return bool(user and (user.is_admin or user.is_superuser))


async def load_policies(db: AsyncSession) -> dict[str, ChannelPolicy]:
    """Every policy row, keyed by channel id. Only touched channels have one."""
    result = await db.execute(select(ChannelPolicy))
    return {p.channel_id: p for p in result.scalars()}


async def load_grants(db: AsyncSession, user: User | None) -> dict[str, str]:
    """This user's per-channel overrides: channel_id -> "allow" | "block"."""
    if user is None:
        return {}
    result = await db.execute(
        select(UserChannelGrant).where(UserChannelGrant.user_id == user.id)
    )
    return {g.channel_id: g.mode for g in result.scalars()}


def required_tier(channel_id: str, policies: dict[str, ChannelPolicy]) -> str:
    policy = policies.get(channel_id)
    return policy.tier if policy else settings_store.default_channel_tier()


def is_hidden(channel_id: str, policies: dict[str, ChannelPolicy]) -> bool:
    policy = policies.get(channel_id)
    return bool(policy and policy.hidden)


def can_watch(
    channel_id: str,
    user: User | None,
    policies: dict[str, ChannelPolicy],
    grants: dict[str, str],
) -> bool:
    """Decide access for one channel. Pure — load the inputs once, reuse them."""
    if is_staff(user):
        return True

    grant = grants.get(channel_id)
    if grant == "block":
        return False
    if grant == "allow":
        return True

    if is_hidden(channel_id, policies):
        return False
    return tier_rank(viewer_tier(user)) >= tier_rank(required_tier(channel_id, policies))


def visible_in_listing(
    channel_id: str,
    user: User | None,
    policies: dict[str, ChannelPolicy],
    grants: dict[str, str],
) -> bool:
    """
    Whether a channel belongs in a browse listing at all.

    Same rule as can_watch, except staff still see hidden channels flagged rather
    than silently dropped — that happens in the admin API, not here.
    """
    return can_watch(channel_id, user, policies, grants)


async def viewer_context(db: AsyncSession, user: User | None):
    """Load both lookup tables in one go — call once per request, not per channel."""
    return await load_policies(db), await load_grants(db, user)
