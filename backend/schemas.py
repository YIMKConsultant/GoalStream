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
