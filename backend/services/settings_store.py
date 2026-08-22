"""
Runtime-editable settings, layered over backend/.env.

pydantic-settings reads .env once at import, so a value changed there needs a
restart. This store keeps a DB-backed override in memory: readers call the
accessors below on every use (never capture them at import time), and a
superuser edit refreshes the cache immediately — no restart, no redeploy.

Only the keys in EDITABLE are settable. `secret` keys are never returned in
full by the admin API; it sends a masked preview instead.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import AppSetting

# key -> (label, is_secret, default taken from .env)
EDITABLE: dict[str, tuple[str, bool]] = {
    "football_api_key":      ("Football API key", True),
    "football_api_base_url": ("Football API base URL", False),
    "default_channel_tier":  ("Default tier for unlisted channels", False),
    "anthropic_api_key":     ("Anthropic (Claude) API key", True),
    "ai_model":              ("Claude model", False),
}

_cache: dict[str, str] = {}


# Keys with no .env counterpart — their default lives here.
_DEFAULTS = {
    "default_channel_tier": "public",
    "ai_model": "claude-opus-5",
    "anthropic_api_key": "",
}


def _env_default(key: str) -> str:
    if key in _DEFAULTS:
        return _DEFAULTS[key]
    return getattr(settings, key, "") or ""


def get(key: str) -> str:
    """Current effective value: DB override if set, else the .env value."""
    value = _cache.get(key)
    return value if value not in (None, "") else _env_default(key)


def is_overridden(key: str) -> bool:
    return bool(_cache.get(key))


async def load(db: AsyncSession) -> None:
    """Warm the cache from the DB. Called at startup and after every edit."""
    result = await db.execute(select(AppSetting))
    _cache.clear()
    _cache.update({row.key: row.value for row in result.scalars() if row.key in EDITABLE})


async def set_many(db: AsyncSession, values: dict[str, str], user_id: int) -> None:
    """Persist overrides then refresh the cache. Unknown keys are ignored."""
    for key, value in values.items():
        if key not in EDITABLE:
            continue
        existing = await db.get(AppSetting, key)
        if existing is None:
            db.add(AppSetting(key=key, value=value, updated_by=user_id))
        else:
            existing.value = value
            existing.updated_by = user_id
    await db.commit()
    await load(db)


def mask(value: str) -> str:
    """Show enough of a secret to recognise it, never enough to use it."""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * 12}{value[-4:]}"


# ── Typed accessors used by the rest of the app ─────────────────────────────

def football_api_key() -> str:
    return get("football_api_key")


def football_api_base_url() -> str:
    return get("football_api_base_url")


def default_channel_tier() -> str:
    return get("default_channel_tier")
