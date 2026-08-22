import { Link } from 'react-router-dom'
import { badge as statusBadge, isUpcoming, kickoffTime, kickoffDate } from '../lib/matchStatus'

// One team as a centered column: crest above, name below.
function Team({ team }) {
  return (
    <div className="flex flex-col items-center gap-2 text-center min-w-0">
      {team.crest
        ? <img src={team.crest} alt="" className="w-12 h-12 object-contain" />
        : <div className="w-12 h-12 rounded-full bg-white/5" />}
      <span className="text-sm font-semibold leading-tight line-clamp-2">
        {team.shortName || team.name}
      </span>
    </div>
  )
}

export default function MatchCard({ match }) {
  const badge = statusBadge(match.status)
  const home = match.score?.fullTime?.home
  const away = match.score?.fullTime?.away
  // Covers SCHEDULED and TIMED — a TIMED fixture used to fall through and render
  // a 0:0 scoreline instead of its kickoff time.
  const scheduled = isUpcoming(match)
  const time = kickoffTime(match.utcDate)
  const date = kickoffDate(match.utcDate)

  return (
    <Link
      to={`/match/${match.id}`}
      className="card block p-5 hover:scale-[1.01] transition-transform min-h-[168px]"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5 text-xs">
        <span className="text-white/40 truncate">{match.league_name}</span>
        <div className="flex items-center gap-2 shrink-0">
          {match.has_stream && <span className="text-yellow-400 font-semibold">▶ Watch</span>}
          <span className={`px-2 py-0.5 rounded-full text-white text-[10px] font-bold ${badge.cls}`}>
            {badge.text}
          </span>
        </div>
      </div>

      {/* Teams + centre (score or kickoff) */}
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <Team team={match.homeTeam} />

        <div className="flex flex-col items-center justify-center px-1">
          {scheduled ? (
            <>
              <span className="text-base font-bold tabular-nums">{time}</span>
              <span className="text-[11px] text-white/40">{date}</span>
            </>
          ) : (
            <span className="text-3xl font-black tabular-nums whitespace-nowrap">
              {home ?? 0}<span className="text-white/25 px-1">:</span>{away ?? 0}
            </span>
          )}
        </div>

        <Team team={match.awayTeam} />
      </div>
    </Link>
  )
}
