import { Link } from 'react-router-dom'

const STATUS_LABEL = {
  IN_PLAY:   { text: 'LIVE',      cls: 'bg-red-600 animate-pulse' },
  PAUSED:    { text: 'HT',        cls: 'bg-yellow-600' },
  FINISHED:  { text: 'FT',        cls: 'bg-white/20' },
  SCHEDULED: { text: 'UPCOMING',  cls: 'bg-blue-700' },
  POSTPONED: { text: 'POSTPONED', cls: 'bg-gray-600' },
}

function formatTime(utcDate) {
  if (!utcDate) return ''
  return new Date(utcDate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function TeamRow({ team, score, side }) {
  return (
    <div className={`flex items-center gap-3 ${side === 'away' ? 'flex-row-reverse text-right' : ''}`}>
      {team.crest && (
        <img src={team.crest} alt={team.name} className="w-8 h-8 object-contain" />
      )}
      <span className="font-medium text-sm truncate max-w-[120px]">
        {team.shortName || team.name}
      </span>
      <span className="text-xl font-bold text-green-400 ml-auto">
        {score ?? '-'}
      </span>
    </div>
  )
}

export default function MatchCard({ match }) {
  const badge = STATUS_LABEL[match.status] ?? { text: match.status, cls: 'bg-white/20' }
  const home = match.score?.fullTime?.home
  const away = match.score?.fullTime?.away

  return (
    <Link to={`/match/${match.id}`} className="card block p-4 hover:scale-[1.01] transition-transform">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 text-xs text-white/40">
        <span>{match.league_name}</span>
        <div className="flex items-center gap-2">
          {match.has_stream && (
            <span className="text-green-400 font-semibold">▶ Watch</span>
          )}
          <span className={`px-2 py-0.5 rounded-full text-white text-[10px] font-bold ${badge.cls}`}>
            {badge.text}
          </span>
        </div>
      </div>

      {/* Teams & score */}
      <div className="space-y-2">
        <TeamRow team={match.homeTeam} score={home} side="home" />
        <div className="text-center text-white/20 text-xs">
          {match.status === 'SCHEDULED' ? formatTime(match.utcDate) : 'vs'}
        </div>
        <TeamRow team={match.awayTeam} score={away} side="away" />
      </div>
    </Link>
  )
}
