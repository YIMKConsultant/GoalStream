import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Play, Clapperboard, Tv, Radio, Clock } from 'lucide-react'
import api from '../api/client'
import { useLiveScores } from '../hooks/useLiveScores'
import { HlsPlayer } from '../components/StreamPlayer'
import { isLive, isUpcoming, kickoffTime, timeUntil, kickoffPhrase } from '../lib/matchStatus'
import { reasonOf, carriesLeague } from '../lib/channelMatch'
import { saveLastWatched, loadLastWatched, clearLastWatched } from '../lib/lastWatched'

// Yellow pill button, matching the left-pane style.
const yBtn = 'flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold ' +
  'text-yellow-300 bg-yellow-400/15 ring-1 ring-yellow-400/40 hover:bg-yellow-400/25 transition-colors'

const STATUS_LABEL = { IN_PLAY: 'LIVE', PAUSED: 'HT', LIVE: 'LIVE' }

// One match row + expandable "watch" panel of candidate channels for its league.
// Works for both a match in play and one kicking off later today.
function MatchRow({ match, onPlay, channelCache, loadChannels }) {
  const [open, setOpen] = useState(false)
  const league = match.league_code
  const channels = channelCache[league]
  const live = isLive(match)

  const toggle = () => {
    setOpen((o) => !o)
    if (!channels) loadChannels(league)
  }

  // The response includes offline candidates so we can explain a missing rights
  // holder — but don't dump 30 dead rows on the viewer. Show what's playable,
  // plus any offline rights holder, which is the one absence worth naming.
  const playable = (channels ?? []).filter((c) => c.alive !== false)
  const offlineHolders = (channels ?? []).filter((c) => c.alive === false && carriesLeague(c))
  const noHolderPlayable = !playable.some(carriesLeague)
  const shown = playable

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          {live ? (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-white text-[10px] font-bold bg-red-600 animate-pulse shrink-0">
              {STATUS_LABEL[match.status] ?? match.status}
            </span>
          ) : (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-blue-200 text-[10px] font-bold bg-blue-700/60 shrink-0">
              <Clock size={11} /> {kickoffTime(match.utcDate)}
            </span>
          )}
          <span className="font-semibold truncate">
            {match.homeTeam.name} <span className="text-white/30">vs</span> {match.awayTeam.name}
          </span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {live ? (
            <span className="text-xl font-black tabular-nums">
              {match.score?.fullTime?.home ?? 0}<span className="text-white/20"> : </span>{match.score?.fullTime?.away ?? 0}
            </span>
          ) : (
            <span className="text-xs text-white/40 hidden sm:block">{timeUntil(match.utcDate)}</span>
          )}
          <button onClick={toggle} className="btn-ghost text-sm px-3 py-1.5">
            {open ? '✕' : '📺 Watch'}
          </button>
        </div>
      </div>

      {open && (
        <div className="mt-4 pt-4 border-t border-white/5 space-y-4">
          {/* Free catalog channels that MAY carry it (best-effort) */}
          {!channels ? (
            <p className="text-white/30 text-sm">Finding free channels…</p>
          ) : shown.length === 0 ? (
            <p className="text-white/30 text-sm">
              No free channels are serving this league right now — the free catalog's
              premium sports feeds are usually geo-locked or offline.
            </p>
          ) : (
            <>
              <p className="text-white/40 text-xs mb-2">
                {live
                  ? <>Channels on air now. Only the ones marked <em>Carries this league</em> hold
                     rights to this competition — the rest are football channels showing
                     something else:</>
                  : <>This match kicks off {kickoffPhrase(match.utcDate)}, so nothing is showing it
                     yet. These channels carry the competition — come back around kickoff:</>}
              </p>
              {noHolderPlayable && offlineHolders.length > 0 && (
                <p className="text-xs text-amber-200/70 bg-amber-400/10 ring-1 ring-amber-400/20 rounded-lg px-3 py-2 mb-2">
                  {offlineHolders.map((c) => c.name).join(', ')} hold the rights here, but{' '}
                  {offlineHolders.length === 1 ? 'that feed is' : 'those feeds are'} geo-blocked
                  or offline right now.
                </p>
              )}
              <div className="flex flex-col gap-2">
                {shown.map((c) => {
                  const reason = reasonOf(c)
                  return (
                    <button
                      key={c.id}
                      onClick={() => c.alive !== false && onPlay(c, match)}
                      disabled={c.alive === false}
                      className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg border text-left transition-colors ${
                        c.alive === false
                          ? 'border-white/5 text-white/30 cursor-not-allowed'
                          : 'border-white/10 text-white/70 hover:border-green-500 hover:text-green-400'
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${c.alive === false ? 'bg-white/20' : 'bg-green-400 animate-pulse'}`} />
                      <span className="truncate">📺 {c.name}{c.country ? ` · ${c.country}` : ''}</span>
                      <span className={`ml-auto shrink-0 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${reason.tone}`}>
                        {reason.label}
                      </span>
                    </button>
                  )
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

// A set of matches grouped into per-league sections.
function LeagueSections({ groups, badgeFor, ...rowProps }) {
  return Object.entries(groups).map(([name, matches]) => (
    <section key={name} className="mb-6">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-lg font-bold">{name}</h3>
        {badgeFor(matches)}
      </div>
      <div className="flex flex-col gap-3">
        {matches.map((m) => <MatchRow key={m.id} match={m} {...rowProps} />)}
      </div>
    </section>
  ))
}

function groupByLeague(matches) {
  const groups = {}
  for (const m of matches) (groups[m.league_name] ??= []).push(m)
  return groups
}

export default function Live() {
  const liveMatches = useLiveScores()
  const [today, setToday] = useState(null)          // all of today's fixtures
  const [active, setActive] = useState(null)        // channel being played
  const [activeFor, setActiveFor] = useState(null)  // the match that channel is for
  const [channelCache, setChannelCache] = useState({}) // league_code -> channels[]
  const [playing, setPlaying] = useState(null)      // sports channels live now
  const autoPicked = useRef(false)                  // only auto-start once per visit

  const [params] = useSearchParams()
  const wantLeague = params.get('league')     // /live?league=PPL — play it, no picking

  const play = (channel, match = null) => {
    setActive(channel)
    setActiveFor(match)
    saveLastWatched(channel, match)
  }
  const stop = () => { setActive(null); setActiveFor(null); clearLastWatched() }

  // Free sports channels that are actually streaming.
  useEffect(() => {
    api.get('/iptv/featured').then(setPlaying).catch(() => setPlaying([]))
  }, [])

  // Today's fixtures, so a match kicking off later still shows up here.
  useEffect(() => {
    const load = () => api.get('/leagues/today').then(setToday).catch(() => setToday([]))
    load()
    const id = setInterval(load, 120000)   // statuses flip to live during the day
    return () => clearInterval(id)
  }, [])

  const loadChannels = (leagueCode) => {
    if (channelCache[leagueCode]) return
    // include_offline so the panel can name an offline rights holder instead of
    // silently showing only a generic channel.
    api.get(`/iptv/for-league/${leagueCode}?include_offline=true`)
      .then((data) => setChannelCache((prev) => ({ ...prev, [leagueCode]: data })))
      .catch(() => setChannelCache((prev) => ({ ...prev, [leagueCode]: [] })))
  }

  // Live = websocket feed, topped up with anything today's list already marks live.
  const live = useMemo(() => {
    const byId = new Map()
    for (const m of [...liveMatches, ...(today ?? []).filter(isLive)]) byId.set(m.id, m)
    return [...byId.values()]
  }, [liveMatches, today])

  // Upcoming = today's fixtures not yet started, soonest first.
  const upcoming = useMemo(() => {
    const liveIds = new Set(live.map((m) => m.id))
    return (today ?? [])
      .filter((m) => isUpcoming(m) && !liveIds.has(m.id))
      .sort((a, b) => new Date(a.utcDate) - new Date(b.utcDate))
  }, [today, live])

  // Whatever the viewer came here for: a match in play, else the next kickoff.
  const nextMatch = useMemo(() => live[0] ?? upcoming[0] ?? null, [live, upcoming])

  // Start a league's channel without the viewer picking one — but ONLY a real
  // rights holder. "ziggo sport" and "arena sport" are in the generic football
  // keyword list, so they're candidates for every competition; auto-playing one
  // puts a Dutch or Slovak channel under a Primeira Liga heading, which reads
  // as the app showing the wrong match. If no rights holder is up we show the
  // list and the offline-broadcaster explanation instead of guessing.
  const startLeague = (code, match = null) =>
    api.get(`/iptv/for-league/${code}?include_offline=true`)
      .then((data) => {
        setChannelCache((prev) => ({ ...prev, [code]: data }))
        const best = data.find((c) => c.alive !== false && carriesLeague(c))
        if (best) play(best, match)
      })
      .catch(() => {})

  // Re-fetch by id rather than reusing a stored URL — stream tickets expire.
  const resumeChannel = (saved) =>
    api.get(`/iptv/channels/${saved.channelId}`)
      .then((channel) => {
        const match = [...live, ...upcoming].find((m) => m.id === saved.matchId) ?? null
        play(channel, match)
      })
      .catch(() => clearLastWatched())   // gone, or no longer permitted

  // Opens the page with football on screen. Runs once; if the viewer closes the
  // player or picks something else, we leave them alone.
  useEffect(() => {
    if (autoPicked.current || active) return

    if (wantLeague) {                       // came from Leagues — that league wins
      autoPicked.current = true
      startLeague(wantLeague)
      return
    }

    const saved = loadLastWatched()
    if (saved) {                            // pick up where they left off
      autoPicked.current = true
      resumeChannel(saved)
      return
    }

    if (!nextMatch) return                  // fixtures still loading — try again
    autoPicked.current = true
    startLeague(nextMatch.league_code, nextMatch)
  }, [nextMatch, active, wantLeague])

  const rowProps = { onPlay: play, channelCache, loadChannels }
  const nothingOn = live.length === 0 && upcoming.length === 0

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <h1 className="text-4xl font-extrabold">Live <span className="text-yellow-400">Now</span></h1>
        <div className="flex flex-wrap gap-2 shrink-0">
          <Link to="/live/videos" className={yBtn}><Play size={16} /> Videos</Link>
          <Link to="/live/replays" className={yBtn}><Clapperboard size={16} /> Replays</Link>
          <Link to="/live/channels" className={yBtn}><Tv size={16} /> All channels</Link>
        </div>
      </div>

      {/* Now playing */}
      {active && (
        <div className="mb-8">
          {activeFor && (
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                isLive(activeFor) ? 'bg-red-600 text-white animate-pulse' : 'bg-blue-700/60 text-blue-200'}`}>
                {isLive(activeFor) ? 'LIVE' : `${kickoffTime(activeFor.utcDate)} · ${timeUntil(activeFor.utcDate)}`}
              </span>
              <span className="text-sm font-semibold">
                {activeFor.homeTeam.name} <span className="text-white/30">vs</span> {activeFor.awayTeam.name}
              </span>
              <span className="text-xs text-white/40">{activeFor.league_name}</span>
            </div>
          )}
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-bold">{active.name}</h2>
              <p className="text-white/40 text-xs">{active.country ?? '—'}{active.quality ? ` · ${active.quality}` : ''}</p>
            </div>
            <button onClick={stop} className="btn-ghost text-sm px-3 py-1.5">✕ Close</button>
          </div>
          <div className="aspect-video bg-black rounded-xl overflow-hidden">
            <HlsPlayer key={active.id} src={active.proxied_url} />
          </div>
          {activeFor && (
            <p className="text-white/30 text-xs mt-2">
              {isLive(activeFor)
                ? <>{reasonOf(active).label} for {activeFor.league_name} — it may not be showing
                   this exact match.</>
                : <>This match kicks off {kickoffPhrase(activeFor.utcDate)}, so this channel is
                   showing its own programming until then.</>}
            </p>
          )}
        </div>
      )}

      {/* Live matches */}
      {live.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Radio size={20} className="text-red-400 animate-pulse" />
            <h2 className="text-xl font-bold">Live matches</h2>
          </div>
          <LeagueSections
            groups={groupByLeague(live)}
            badgeFor={(ms) => (
              <span className="text-xs bg-red-600/20 text-red-400 px-2 py-0.5 rounded-full">
                {ms.length} live
              </span>
            )}
            {...rowProps}
          />
        </div>
      )}

      {/* Kicking off later today */}
      {upcoming.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-1">
            <Clock size={20} className="text-blue-400" />
            <h2 className="text-xl font-bold">On today</h2>
            <span className="text-xs bg-blue-600/20 text-blue-300 px-2 py-0.5 rounded-full">
              {upcoming.length} {upcoming.length === 1 ? 'match' : 'matches'}
            </span>
          </div>
          <p className="text-white/40 text-sm mb-4">
            Kicking off later — open one to see the channels that carry the competition.
          </p>
          <LeagueSections
            groups={groupByLeague(upcoming)}
            badgeFor={(ms) => (
              <span className="text-xs text-white/40">
                from {kickoffTime(ms[0].utcDate)}
              </span>
            )}
            {...rowProps}
          />
        </div>
      )}

      {/* Sports channels on air — always available, not just as a fallback */}
      <section>
        <div className="flex items-center gap-2 mb-1">
          <Tv size={20} className="text-yellow-400" />
          <h2 className="text-xl font-bold">Sports channels on air</h2>
        </div>
        <p className="text-white/40 text-sm mb-4">
          {nothingOn
            ? 'No match is live or scheduled today — here are free sports channels streaming right now.'
            : 'Free sports channels streaming right now — click any to start watching.'}
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
                onClick={() => play(c)}
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
    </div>
  )
}
