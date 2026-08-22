from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    is_superuser: bool = False
    tier: str = "free"
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Leagues ───────────────────────────────────────────────────────────────────

class LeagueOut(BaseModel):
    code: str
    name: str
    country: str
    emblem: str
    fixtures: bool = True    # False -> browsable, but the data provider has no feed


# ── Matches ───────────────────────────────────────────────────────────────────

class TeamInfo(BaseModel):
    id: int = 0
    name: str = "TBD"
    shortName: Optional[str] = None
    crest: Optional[str] = None


class ScoreHalf(BaseModel):
    home: Optional[int] = None
    away: Optional[int] = None


class MatchScore(BaseModel):
    winner: Optional[str] = None
    duration: Optional[str] = None
    fullTime: ScoreHalf
    halfTime: ScoreHalf


class MatchOut(BaseModel):
    id: int
    league_code: str
    league_name: str
    matchday: Optional[int] = None
    stage: Optional[str] = None
    status: str           # SCHEDULED | LIVE | IN_PLAY | PAUSED | FINISHED | POSTPONED
    utcDate: str
    homeTeam: TeamInfo
    awayTeam: TeamInfo
    score: MatchScore
    venue: Optional[str] = None
    has_stream: bool = False


class MatchDetail(MatchOut):
    referees: List[str] = []


# ── Streams ───────────────────────────────────────────────────────────────────

class StreamCreate(BaseModel):
    match_id: int
    league_code: str
    label: str
    stream_url: str
    stream_type: str = "m3u8"   # m3u8 | embed | youtube
    language: str = "English"


class StreamOut(BaseModel):
    id: int
    match_id: int
    league_code: str
    label: str
    stream_url: str
    stream_type: str
    language: str
    is_active: bool

    class Config:
        from_attributes = True


# ── Favorites ─────────────────────────────────────────────────────────────────

class FavoriteCreate(BaseModel):
    team_id: int
    team_name: str


class FavoriteOut(BaseModel):
    id: int
    team_id: int
    team_name: str

    class Config:
        from_attributes = True


# ── Standings ─────────────────────────────────────────────────────────────────

class StandingTeam(BaseModel):
    position: int
    team: TeamInfo
    playedGames: int
    won: int
    draw: int
    lost: int
    points: int
    goalDifference: int
    goalsFor: int
    goalsAgainst: int


class StandingsOut(BaseModel):
    league_code: str
    league_name: str
    season: str
    table: List[StandingTeam]


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    is_superuser: bool
    tier: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Every field optional — only what's sent gets changed."""
    tier: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_superuser: Optional[bool] = None


class AdminChannelOut(BaseModel):
    id: str
    name: str
    country: Optional[str] = None
    tier: str
    hidden: bool = False
    note: str = ""
    customised: bool = False    # False -> inheriting the default, no policy row


class ChannelPolicyIn(BaseModel):
    tier: str = "public"
    hidden: bool = False
    note: str = ""


class GrantIn(BaseModel):
    mode: str = "allow"         # allow | block


class GrantOut(BaseModel):
    id: int
    user_id: int
    channel_id: str
    mode: str

    class Config:
        from_attributes = True


class SettingValueOut(BaseModel):
    key: str
    label: str
    secret: bool
    value: str                  # masked when secret is True
    overridden: bool            # True -> a DB override is shadowing .env


class SettingsOut(BaseModel):
    settings: List[SettingValueOut]


class SettingsIn(BaseModel):
    values: dict[str, str]
