import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { useLiveScores } from '../hooks/useLiveScores'
import { HlsPlayer } from '../components/StreamPlayer'

const STATUS_LABEL = { IN_PLAY: 'LIVE', PAUSED: 'HT' }

// One match row + expandable "watch" panel of candidate channels for its league.
function MatchRow({ match, onPlay, channelCache, loadChannels }) {
  const [open, setOpen] = useState(false)
  const league = match.league_code
  const channels = channelCache[league]

  const toggle = () => {
    setOpen((o) => !o)
    if (!channels) loadChannels(league)
  }

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-white text-[10px] font-bold bg-red-600 animate-pulse shrink-0">
            {STATUS_LABEL[match.status] ?? match.status}
          </span>
          <span className="font-semibold truncate">
            {match.homeTeam.name} <span className="text-white/30">vs</span> {match.awayTeam.name}
          </span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xl font-black tabular-nums">
            {match.score?.fullTime?.home ?? 0}<span className="text-white/20"> : </span>{match.score?.fullTime?.away ?? 0}
          </span>
          <button onClick={toggle} className="btn-ghost text-sm px-3 py-1.5">
            {open ? '✕' : '📺 Watch'}
          </button>
        </div>
      </div>

      {open && (
        <div className="mt-4 pt-4 border-t border-white/5">
          {!channels ? (
            <p className="text-white/30 text-sm">Finding channels…</p>
          ) : channels.length === 0 ? (
            <p className="text-white/30 text-sm">No candidate channels found for this league.</p>
          ) : (
            <>
              <p className="text-white/40 text-xs mb-2">
                Channels that <em>may</em> be airing this match — no schedule guarantee, and some are region-locked:
              </p>
              <div className="flex flex-wrap gap-2">
                {channels.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => onPlay(c)}
                    className="text-sm px-3 py-1.5 rounded-lg border border-white/10 text-white/70 hover:border-green-500 hover:text-green-400 transition-colors"
                  >
                    📺 {c.name}{c.country ? ` · ${c.country}` : ''}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default function Live() {
  const liveMatches = useLiveScores()
  const [active, setActive] = useState(null)          // channel being played
  const [channelCache, setChannelCache] = useState({}) // league_code -> channels[]

  const loadChannels = (leagueCode) => {
    if (channelCache[leagueCode]) return
    api.get(`/iptv/for-league/${leagueCode}`)
      .then((data) => setChannelCache((prev) => ({ ...prev, [leagueCode]: data })))
      .catch(() => setChannelCache((prev) => ({ ...prev, [leagueCode]: [] })))
  }

  // Group live matches by league name.
  const byLeague = useMemo(() => {
    const groups = {}
    for (const m of liveMatches) {
      (groups[m.league_name] ??= []).push(m)
    }
    return groups
  }, [liveMatches])

  const leagueNames = Object.keys(byLeague)

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="text-3xl font-extrabold mb-1">Live Football <span className="text-green-400">Now</span></h1>
          <p className="text-white/40 text-sm">Live matches by league · watch via free iptv-org channels</p>
        </div>
        <div className="flex gap-2 shrink-0">
          <Link to="/live/replays" className="btn-ghost text-sm px-3 py-1.5">🎞️ Replays</Link>
          <Link to="/live/channels" className="btn-ghost text-sm px-3 py-1.5">All channels →</Link>
        </div>
      </div>

      {/* Now playing */}
      {active && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-bold">{active.name}</h2>
              <p className="text-white/40 text-xs">{active.country ?? '—'}{active.quality ? ` · ${active.quality}` : ''}</p>
            </div>
            <button onClick={() => setActive(null)} className="btn-ghost text-sm px-3 py-1.5">✕ Close</button>
          </div>
          <div className="aspect-video bg-black rounded-xl overflow-hidden">
            <HlsPlayer key={active.id} src={active.proxied_url} />
          </div>
        </div>
      )}

      {/* Live matches grouped by league */}
      {leagueNames.length === 0 ? (
        <div className="card p-8 text-center">
          <span className="text-4xl">😴</span>
          <p className="text-lg font-bold mt-3">No football live right now</p>
          <p className="text-white/40 text-sm mt-1">
            When matches kick off they'll appear here by league. Meanwhile you can{' '}
            <Link to="/live/channels" className="text-green-400 hover:underline">browse all live channels</Link>.
          </p>
        </div>
      ) : (
        leagueNames.map((name) => (
          <section key={name} className="mb-8">
            <div className="flex items-center gap-2 mb-3">
              <h2 className="text-xl font-bold">{name}</h2>
              <span className="text-xs bg-red-600/20 text-red-400 px-2 py-0.5 rounded-full">
                {byLeague[name].length} live
              </span>
            </div>
            <div className="flex flex-col gap-3">
              {byLeague[name].map((m) => (
                <MatchRow
                  key={m.id}
                  match={m}
                  onPlay={setActive}
                  channelCache={channelCache}
                  loadChannels={loadChannels}
                />
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  )
}
