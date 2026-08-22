from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from config import DEFAULT_USER_TIER


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    # Above admin: only a superuser may edit API credentials or change who is an
    # admin. See auth.require_superuser.
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    # Which channel tier this account holds — see config.TIERS.
    tier: Mapped[str] = mapped_column(String(20), default=DEFAULT_USER_TIER)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    favorites: Mapped[list["FavoriteTeam"]] = relationship(back_populates="user", cascade="all, delete")


class FavoriteTeam(Base):
    __tablename__ = "favorite_teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    team_name: Mapped[str] = mapped_column(String(100), nullable=False)

    user: Mapped["User"] = relationship(back_populates="favorites")


class Stream(Base):
    """Admin-managed stream links attached to a specific match."""
    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    league_code: Mapped[str] = mapped_column(String(10), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)       # e.g. "HD Stream 1"
    stream_url: Mapped[str] = mapped_column(Text, nullable=False)          # m3u8 / embed URL
    stream_type: Mapped[str] = mapped_column(String(20), default="m3u8")   # m3u8 | embed | youtube
    language: Mapped[str] = mapped_column(String(30), default="English")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChannelPolicy(Base):
    """
    Admin-set access rules for one iptv-org channel.

    Channels live in the upstream catalog, not in our DB — a row here exists only
    for channels an admin has actually touched. Anything without a row falls back
    to the `default_channel_tier` setting, so the site keeps working unchanged
    until someone starts restricting things.
    """
    __tablename__ = "channel_policy"

    channel_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    tier: Mapped[str] = mapped_column(String(20), default="public")   # see config.TIERS
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)      # hide from every listing
    note: Mapped[str] = mapped_column(String(255), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)


class UserChannelGrant(Base):
    """
    Per-user override sitting on top of the tier rules: `block` denies a channel
    the user's tier would otherwise reach, `allow` opens one it wouldn't.
    """
    __tablename__ = "user_channel_grants"
    __table_args__ = (UniqueConstraint("user_id", "channel_id", name="uq_user_channel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    channel_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(10), default="allow")    # allow | block
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)


class LeagueChannelMap(Base):
    """
    Which channels carry which competition — the AI-built replacement for the
    hand-maintained substring lists in services/iptv_org.py. `source` is "ai"
    (from a discovery run, replaced wholesale on re-run) or "manual" (an admin
    pinned it; discovery never touches those rows).
    """
    __tablename__ = "league_channel_map"
    __table_args__ = (UniqueConstraint("league_code", "channel_id", name="uq_league_channel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    league_code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    channel_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(10), default="ai")     # ai | manual
    confidence: Mapped[str] = mapped_column(String(10), default="medium")
    rank: Mapped[int] = mapped_column(Integer, default=0)             # 0 = best match
    note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppSetting(Base):
    """
    Runtime-editable settings that override backend/.env. Superuser only —
    these hold API credentials. See services/settings_store.py.
    """
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
