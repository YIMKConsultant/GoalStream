"""
AI-assisted channel discovery.

`services/iptv_org.py` maps competitions to channels with hand-maintained
substring lists. That approach has now produced three separate false-positive
bugs — "on sport" matched "Cytavision Sports", "n sports" matched "Bahrain
Sports", and the country fallback offered FightBox for the Eredivisie. Claude
reads the actual channel names instead of pattern-matching them, so it can tell
a football broadcaster from a kickboxing channel and knows which broadcaster
holds which league.

What it searches: the free, legal iptv-org catalog that the app already carries
(~460 free-to-air sports channels). Subscription broadcasters — sooka, Astro GO,
unifi TV, beIN, ESPN+ — are licensed services with no lawful free stream, so
there is nothing for this to find and it does not look; the app keeps deep-
linking viewers to those providers instead (see components/WatchOfficial.jsx).
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import LEAGUES
from models import LeagueChannelMap
from services import ai_client
from services.iptv_org import get_sports_channels

# One competition's worth of catalog is small enough to send whole; sending the
# full list (rather than a keyword-prefiltered slice) is the entire point —
# prefiltering would reintroduce the substring bug we're removing.
MAX_CHANNELS_PER_CALL = 500

SYSTEM = """You classify free-to-air TV channels for a football streaming app.

You are given a football competition and a list of channel names from the
iptv-org free catalog (free-to-air channels only — no subscription services).
Identify which channels plausibly broadcast that competition.

Judge by what you know about broadcast rights and about each channel:
- The competition's own national/regional rights holders rank highest.
- Pan-regional sports networks that carry the competition rank next.
- General sports channels from the competition's country rank last.
- Exclude channels for other sports entirely (golf, tennis, cricket, darts,
  motorsport, combat sports, poker, fishing, snooker, billiards).
- Exclude channels whose name merely contains a matching substring but which
  are unrelated — e.g. "Cytavision Sports" (Cyprus) is not an Egyptian
  "ON Sport", and "Bahrain Sports" is not Brazil's "N Sports".

Be honest about uncertainty. It is better to return five channels you are
confident about than thirty you are guessing at. If no channel in the list
plausibly carries the competition, return an empty list — that is a valid and
useful answer.

You are never asked to locate unauthorized restreams of subscription
broadcasters, and must not suggest any channel on that basis."""


class ChannelMatch(BaseModel):
    channel_id: str = Field(description="The exact id from the supplied catalog")
    confidence: Literal["high", "medium", "low"] = Field(
        description="high = known rights holder; medium = plausible carrier; low = general sports channel from the right country"
    )
    reason: str = Field(description="One short sentence on why this channel carries the competition")


class LeagueMatches(BaseModel):
    matches: List[ChannelMatch] = Field(description="Channels that plausibly broadcast this competition, best first")
    notes: str = Field(description="One sentence on overall coverage, or why nothing matched")


async def discover_for_league(
    db: AsyncSession,
    league_code: str,
    min_confidence: str = "low",
    persist: bool = True,
) -> dict:
    """Ask Claude which catalog channels carry a competition, then store the map."""
    code = league_code.upper()
    meta = LEAGUES.get(code)
    if meta is None:
        raise ValueError(f"Unknown league '{code}'")

    channels = await get_sports_channels()
    catalog = channels[:MAX_CHANNELS_PER_CALL]
    by_id = {c["id"]: c for c in catalog}

    listing = "\n".join(
        f"{c['id']} | {c['name']} | {c.get('country') or '??'}" for c in catalog
    )
    prompt = (
        f"Competition: {meta['name']} ({code})\n"
        f"Region: {meta['country']}\n\n"
        f"Catalog ({len(catalog)} channels, one per line as `id | name | country`):\n"
        f"{listing}\n\n"
        f"Which of these plausibly broadcast {meta['name']}?"
    )

    result = await ai_client.parse(SYSTEM, prompt, LeagueMatches)

    rank = {"high": 3, "medium": 2, "low": 1}
    floor = rank.get(min_confidence, 1)

    # Claude can only pick from the catalog we sent, but verify rather than
    # trust — a hallucinated id would silently poison the mapping table.
    kept, dropped = [], []
    for match in result.matches:
        channel = by_id.get(match.channel_id)
        if channel is None:
            dropped.append(match.channel_id)
            continue
        if rank.get(match.confidence, 0) < floor:
            continue
        kept.append({
            "channel_id": match.channel_id,
            "name": channel["name"],
            "country": channel.get("country"),
            "confidence": match.confidence,
            "reason": match.reason,
        })

    if persist:
        await db.execute(
            delete(LeagueChannelMap).where(
                LeagueChannelMap.league_code == code, LeagueChannelMap.source == "ai"
            )
        )
        for rank_index, match in enumerate(kept):
            db.add(LeagueChannelMap(
                league_code=code,
                channel_id=match["channel_id"],
                source="ai",
                confidence=match["confidence"],
                rank=rank_index,
                note=match["reason"][:255],
            ))
        await db.commit()

    return {
        "league_code": code,
        "league_name": meta["name"],
        "catalog_size": len(catalog),
        "matches": kept,
        "unknown_ids": dropped,   # non-empty means Claude invented an id
        "notes": result.notes,
        "persisted": persist,
    }


async def mapped_channel_ids(db: AsyncSession, league_code: str) -> list[str]:
    """Stored channel ids for a competition, best first. Empty = fall back to keywords."""
    result = await db.execute(
        select(LeagueChannelMap)
        .where(LeagueChannelMap.league_code == league_code.upper())
        .order_by(LeagueChannelMap.rank)
    )
    return [row.channel_id for row in result.scalars()]
