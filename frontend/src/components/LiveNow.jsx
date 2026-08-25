import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Radio, Tv, ArrowRight } from 'lucide-react'
import api from '../api/client'
import { HlsPlayer } from './StreamPlayer'
import { reasonOf, carriesLeague, inEnglish, languageLabel } from '../lib/channelMatch'
import WatchOfficial from './WatchOfficial'

/**
 * "Live now" — every in-play match with the channels that can show it, playable
 * without leaving the Dashboard.
 *
 * The Dashboard used to be scores-only: you could see that Hull City were 2-0 up
 * and had no way to watch it. Everything here is already liveness-checked and
 * English-first by the time it arrives; this component's only jobs are to fetch
 * once per league rather than once per match, and to be honest about what each
 * channel actually is.
 */

// Channels are per-LEAGUE, not per-match, so three live Championship games share
// one request. /iptv/for-league is slow when nothing is cached upstream, and
// firing it once per match would multiply that for no extra information.
function useLeagueChannels(leagueCodes) {
  const [byLeague, setByLeague] = useState({})

  useEffect(() => {
    let cancelled = false
    for (const code of leagueCodes) {
      if (code in byLeague) continue
      setByLeague((prev) => (code in prev ? prev : { ...prev, [code]: null }))
      api.get(`/iptv/for-league/${code}`)
        .then((data) => { if (!cancelled) setByLeague((p) => ({ ...p, [code]: data })) })
        .catch(() => { if (!cancelled) setByLeague((p) => ({ ...p, [code]: [] })) })
    }
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leagueCodes.join(',')])

  return byLeague
}

function ChannelButton({ channel, active, onPlay }) {
  const reason = reasonOf(channel)
  const language = languageLabel(channel)
  return (
    <button
      onClick={() => onPlay(channel)}
      className={`flex items-center gap-2 text-xs px-2.5 py-1.5 rounded-lg border text-left transition-colors ${
        active
          ? 'border-yellow-400 text-yellow-300 bg-yellow-400/10'
          : 'border-white/10 text-white/70 hover:border-green-500 hover:text-green-400'
      }`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse shrink-0" />
      <span className="truncate">{channel.name}</span>
      {language && (
        <span className={`shrink-0 text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full ${
          inEnglish(channel)
            ? 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/30'
            : 'bg-white/10 text-white/40'
        }`}>
          {language}
        </span>
      )}
      <span className={`shrink-0 text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full ${reason.tone}`}>
        {reason.label}
      </span>
    </button>
  )
}

function LiveMatch({ match, channels, active, onPlay }) {
  // Only an actual rights holder counts. A `general_football` channel that
  // happens to be on air is not showing this match, and listing it here is what
  // put US college football under a Championship heading.
  const shown = useMemo(
    () => (channels ? channels.filter(carriesLeague).slice(0, 4) : null),
    [channels],
  )

  const playingHere = active && shown?.some((c) => c.id === active.id)

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between gap-3 mb-1">
        <div className="flex items-center gap-2 min-w-0">
          <span className="px-2 py-0.5 rounded-full text-white text-[10px] font-bold bg-red-600 animate-pulse shrink-0">
            LIVE
          </span>
          <Link to={`/match/${match.id}`} className="font-semibold text-sm truncate hover:text-yellow-400">
            {match.homeTeam.shortName || match.homeTeam.name}
            <span className="text-white/30"> vs </span>
            {match.awayTeam.shortName || match.awayTeam.name}
          </Link>
        </div>
        <span className="text-lg font-black tabular-nums shrink-0">
          {match.score?.fullTime?.home ?? 0}
          <span className="text-white/20"> : </span>
          {match.score?.fullTime?.away ?? 0}
        </span>
      </div>
      <p className="text-xs text-white/40 mb-3">{match.league_name}</p>

      {shown === null ? (
        <p className="text-white/30 text-xs">Finding channels…</p>
      ) : shown.length === 0 ? (
        <WatchOfficial leagueCode={match.league_code} leagueName={match.league_name} compact />
      ) : (
        <div className="flex flex-wrap gap-2">
          {shown.map((c) => (
            <ChannelButton key={c.id} channel={c} active={active?.id === c.id} onPlay={onPlay} />
          ))}
        </div>
      )}

      {playingHere && (
        <div className="mt-3">
          <div className="aspect-video bg-black rounded-lg overflow-hidden">
            <HlsPlayer key={active.id} src={active.proxied_url} />
          </div>
          <p className="text-white/30 text-[11px] mt-1.5">
            {active.name} — {reasonOf(active).label.toLowerCase()}. It may not be showing this
            exact match.
          </p>
        </div>
      )}
    </div>
  )
}

export default function LiveNow({ matches }) {
  const [active, setActive] = useState(null)

  const leagueCodes = useMemo(
    () => [...new Set(matches.map((m) => m.league_code).filter(Boolean))],
    [matches],
  )
  const byLeague = useLeagueChannels(leagueCodes)

  if (matches.length === 0) return null

  return (
    <section className="mb-8">
      <div className="flex items-center gap-2 mb-1">
        <Radio size={18} className="text-red-400 animate-pulse" />
        <h2 className="text-lg font-bold">Live now</h2>
        <span className="text-xs bg-red-600/20 text-red-400 px-2 py-0.5 rounded-full">
          {matches.length} {matches.length === 1 ? 'match' : 'matches'}
        </span>
        <Link to="/live" className="ml-auto text-sm text-yellow-400 hover:underline flex items-center gap-1">
          Live page <ArrowRight size={14} />
        </Link>
      </div>
      <p className="text-white/40 text-sm mb-3">
        Only channels that actually hold rights to a competition are offered, English
        commentary first. Where none is free, you get the official broadcaster instead.
      </p>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {matches.map((m) => (
          <LiveMatch
            key={m.id}
            match={m}
            channels={byLeague[m.league_code]}
            active={active}
            onPlay={(c) => setActive((cur) => (cur?.id === c.id ? null : c))}
          />
        ))}
      </div>
      <p className="text-white/25 text-[11px] mt-3 flex items-center gap-1.5">
        <Tv size={12} /> GoalStream only relays streams served by the broadcaster or a
        licensed platform.
      </p>
    </section>
  )
}
