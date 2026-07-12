import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api/client'
import StreamPlayer from '../components/StreamPlayer'

const STATUS_COLOR = {
  IN_PLAY: 'text-red-400', PAUSED: 'text-yellow-400',
  FINISHED: 'text-white/40', SCHEDULED: 'text-blue-400',
}

function formatDate(utcDate) {
  if (!utcDate) return ''
  return new Date(utcDate).toLocaleString([], {
    weekday: 'short', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function Match() {
  const { id } = useParams()
  const [match, setMatch] = useState(null)
  const [streams, setStreams] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.allSettled([
      api.get(`/matches/${id}`),
      api.get(`/matches/${id}/streams`),
    ]).then(([matchResult, streamsResult]) => {
      if (matchResult.status === 'fulfilled') setMatch(matchResult.value)
      if (streamsResult.status === 'fulfilled') setStreams(streamsResult.value)
    }).finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="text-white/30 text-center py-24">Loading…</div>
  if (!match && streams.length === 0) return <div className="text-red-400 text-center py-24">Match not found.</div>

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">

      {/* Header */}
      <p className="text-white/40 text-sm mb-2">{match?.league_name ?? 'Live Stream'}</p>
      <p className="text-white/30 text-xs mb-6">{match ? formatDate(match.utcDate) : ''}</p>

      {/* Stream-only card (no football API match) */}
      {!match && (
        <div className="card p-6 mb-6 text-center">
          <h1 className="text-2xl font-bold text-green-400">{streams[0]?.label ?? 'Live Match'}</h1>
          <p className="text-white/40 text-sm mt-1">{streams[0]?.language} · {streams[0]?.stream_type?.toUpperCase()}</p>
        </div>
      )}

      {/* Score board */}
      {match && (
        <div className="card p-6 mb-6">
          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-col items-center gap-2 flex-1">
              {match.homeTeam.crest && (
                <img src={match.homeTeam.crest} alt={match.homeTeam.name} className="w-16 h-16 object-contain" />
              )}
              <span className="font-bold text-center text-lg">{match.homeTeam.name}</span>
            </div>

            <div className="flex flex-col items-center shrink-0">
              <div className="text-5xl font-black tracking-tight">
                {match.score?.fullTime?.home ?? '-'} <span className="text-white/20">:</span> {match.score?.fullTime?.away ?? '-'}
              </div>
              <span className={`text-sm font-semibold mt-1 ${STATUS_COLOR[match.status] ?? 'text-white/40'}`}>
                {match.status?.replace('_', ' ')}
              </span>
              {match.score?.halfTime?.home != null && (
                <span className="text-xs text-white/30 mt-1">
                  HT {match.score.halfTime.home} - {match.score.halfTime.away}
                </span>
              )}
            </div>

            <div className="flex flex-col items-center gap-2 flex-1">
              {match.awayTeam.crest && (
                <img src={match.awayTeam.crest} alt={match.awayTeam.name} className="w-16 h-16 object-contain" />
              )}
              <span className="font-bold text-center text-lg">{match.awayTeam.name}</span>
            </div>
          </div>

          {(match.venue || match.referees?.length > 0) && (
            <div className="mt-4 pt-4 border-t border-white/5 flex flex-wrap gap-4 text-xs text-white/30">
              {match.venue && <span>📍 {match.venue}</span>}
              {match.referees?.length > 0 && <span>🟨 {match.referees[0]}</span>}
            </div>
          )}
        </div>
      )}

      {/* Stream player */}
      <div className="mb-6">
        <h2 className="text-lg font-bold mb-3">
          {streams.length > 0 ? `Watch — ${streams.length} stream${streams.length > 1 ? 's' : ''} available` : 'Stream'}
        </h2>
        <StreamPlayer streams={streams} />
      </div>

    </div>
  )
}
