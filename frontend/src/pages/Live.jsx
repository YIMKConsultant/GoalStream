import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Play, Clapperboard, Tv, Radio } from 'lucide-react'
import api from '../api/client'
import { useLiveScores } from '../hooks/useLiveScores'
import { HlsPlayer } from '../components/StreamPlayer'
import WatchOfficial from '../components/WatchOfficial'

// Yellow pill button, matching the left-pane style.
const yBtn = 'flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold ' +
  'text-yellow-300 bg-yellow-400/15 ring-1 ring-yellow-400/40 hover:bg-yellow-400/25 transition-colors'

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
        <div className="mt-4 pt-4 border-t border-white/5 space-y-4">
          {/* Legal, licensed way to watch — always shown */}
          <WatchOfficial match={match} />

          {/* Free catalog channels that MAY carry it (best-effort) */}
          {!channels ? (
            <p className="text-white/30 text-sm">Finding free channels…</p>
          ) : channels.length === 0 ? (
            <p className="text-white/30 text-sm">
              No free channels are serving this league right now — the free catalog's
              premium sports feeds are usually geo-locked or offline.
            </p>
          ) : (
            <>
              <p className="text-white/40 text-xs mb-2">
                Channels verified serving right now that <em>may</em> be airing this match —
                no schedule guarantee, and some are region-locked:
              </p>
              <div className="flex flex-wrap gap-2">
                {channels.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => c.alive !== false && onPlay(c)}
                    disabled={c.alive === false}
                    className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border transition-colors ${
                      c.alive === false
                        ? 'border-white/5 text-white/30 cursor-not-allowed'
                        : 'border-white/10 text-white/70 hover:border-green-500 hover:text-green-400'
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${c.alive === false ? 'bg-white/20' : 'bg-green-400 animate-pulse'}`} />
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
  const [playing, setPlaying] = useState(null)        // sports channels live now

  // Free sports channels that are actually streaming — shown until matches go live.
  useEffect(() => {
    api.get('/iptv/featured').then(setPlaying).catch(() => setPlaying([]))
  }, [])

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
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <h1 className="text-4xl font-extrabold">Live Football <span className="text-yellow-400">Now</span></h1>
        <div className="flex flex-wrap gap-2 shrink-0">
          <Link to="/live/videos" className={yBtn}><Play size={16} /> Videos</Link>
          <Link to="/live/replays" className={yBtn}><Clapperboard size={16} /> Replays</Link>
          <Link to="/live/channels" className={yBtn}><Tv size={16} /> All channels</Link>
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
        <section>
          <div className="flex items-center gap-2 mb-1">
            <Radio size={18} className="text-red-400 animate-pulse" />
            <h2 className="text-xl font-bold">Sports channels live now</h2>
          </div>
          <p className="text-white/40 text-sm mb-4">
            No league match is live yet — here are free sports channels streaming right now.
          </p>

          {playing === null ? (
            <p className="text-white/30 text-sm">Finding channels that are on air…</p>
          ) : playing.length === 0 ? (
            <p className="text-white/30 text-sm">
              No channels are streaming this moment. Try{' '}
              <Link to="/live/channels" className="text-yellow-400 hover:underline">all channels</Link>{' '}
              or{' '}
              <Link to="/live/replays" className="text-yellow-400 hover:underline">replays</Link>.
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {playing.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setActive(c)}
                  className={`card text-left p-4 transition-transform hover:scale-[1.02] ${active?.id === c.id ? 'border-yellow-400' : ''}`}
                >
                  <div className="flex items-center justify-between mb-3 text-xs">
                    <span className="text-white/40">{c.country ?? '—'}</span>
                    <span className="flex items-center gap-1 text-green-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" /> Live
                    </span>
                  </div>
                  <div className="flex flex-col items-center gap-2 py-2">
                    <Tv size={24} className="text-yellow-400" />
                    <span className="text-base font-bold text-center">{c.name}</span>
                    <span className="text-xs text-white/40">{c.quality ?? 'Click to watch'}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>
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
