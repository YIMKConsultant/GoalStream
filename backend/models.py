from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
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
