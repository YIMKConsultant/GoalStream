import { Link } from 'react-router-dom'

const STATUS_LABEL = {
  IN_PLAY:   { text: 'LIVE',      cls: 'bg-red-600 animate-pulse' },
  PAUSED:    { text: 'HT',        cls: 'bg-yellow-500 text-pitch-900' },
  FINISHED:  { text: 'FT',        cls: 'bg-white/20' },
  SCHEDULED: { text: 'UPCOMING',  cls: 'bg-blue-700' },
  POSTPONED: { text: 'POSTPONED', cls: 'bg-gray-600' },
}

function formatDateTime(utcDate) {
  if (!utcDate) return { time: '', date: '' }
  const d = new Date(utcDate)
  return {
    time: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    date: d.toLocaleDateString([], { day: '2-digit', month: 'short' }),
  }
}

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
  const badge = STATUS_LABEL[match.status] ?? { text: match.status, cls: 'bg-white/20' }
  const home = match.score?.fullTime?.home
  const away = match.score?.fullTime?.away
  const scheduled = match.status === 'SCHEDULED'
  const { time, date } = formatDateTime(match.utcDate)

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
