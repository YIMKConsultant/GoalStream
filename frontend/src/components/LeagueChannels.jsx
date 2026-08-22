import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Tv } from 'lucide-react'
import api from '../api/client'
import { HlsPlayer } from './StreamPlayer'
import { reasonOf, carriesLeague } from '../lib/channelMatch'

/**
 * Plays the free channels that normally carry a competition.
 *
 * iptv-org publishes no schedule, so this can never promise "this match is on
 * this channel" — it offers the broadcasters that carry the league, already
 * liveness-checked, and starts the first working one so there's picture on
 * screen instead of an empty box.
 */
export default function LeagueChannels({ leagueCode, autoPlay = true, compact = false }) {
  const [channels, setChannels] = useState(null)
  const [active, setActive] = useState(null)

  useEffect(() => {
    if (!leagueCode) { setChannels([]); return }
    let cancelled = false
    setChannels(null)
    setActive(null)
    // include_offline so we can SAY the rights holder is down rather than
    // silently dropping it and leaving only a generic channel on screen —
    // which reads as "the app can't find my match".
    api.get(`/iptv/for-league/${leagueCode}?include_offline=true`)
      .then((data) => {
        if (cancelled) return
        setChannels(data)
        // Auto-start only a genuine rights holder — never a generic football
        // channel, which would look like the wrong match is playing.
        if (autoPlay) setActive(data.find((c) => c.alive !== false && carriesLeague(c)) ?? null)
      })
      .catch(() => { if (!cancelled) setChannels([]) })
    return () => { cancelled = true }
  }, [leagueCode, autoPlay])

  const playable = (channels ?? []).filter((c) => c.alive !== false)
  // Rights holders that exist in the catalog but aren't serving. Naming them is
  // the whole point: "Ziggo Sport is offline" is an answer, an empty list isn't.
  const offlineHolders = (channels ?? []).filter((c) => c.alive === false && carriesLeague(c))
  const noHolderPlayable = !playable.some(carriesLeague)

  if (channels === null) {
    return (
      <div className={`${compact ? 'aspect-video' : 'aspect-video'} bg-pitch-800 rounded-xl flex flex-col items-center justify-center text-white/30 border border-white/5 gap-2`}>
        <Tv size={32} />
        <p className="text-sm">Finding channels that carry this competition…</p>
      </div>
    )
  }

  if (playable.length === 0) {
    return (
      <div className="aspect-video bg-pitch-800 rounded-xl flex flex-col items-center justify-center text-white/30 border border-white/5 gap-2 px-6 text-center">
        <Tv size={32} />
        <p className="text-sm">No free channel is carrying this competition right now.</p>
        {offlineHolders.length > 0 ? (
          <p className="text-xs text-white/25 max-w-md">
            {offlineHolders.map((c) => c.name).join(', ')} hold{offlineHolders.length === 1 ? 's' : ''}{' '}
            the rights, but {offlineHolders.length === 1 ? 'its' : 'their'} free feed is
            geo-blocked or offline at the moment. These come and go — try again nearer kickoff.
          </p>
        ) : (
          <p className="text-xs text-white/25">
            Try <Link to="/live/channels" className="text-yellow-400 hover:underline">all channels</Link>.
          </p>
        )}
      </div>
    )
  }

  return (
    <div>
      <div className="aspect-video bg-black rounded-xl overflow-hidden">
        {active
          ? <HlsPlayer key={active.id} src={active.proxied_url} />
          : (
            <div className="w-full h-full flex flex-col items-center justify-center text-white/30 gap-2">
              <Tv size={32} />
              <p className="text-sm">Pick a channel below to start watching.</p>
            </div>
          )}
      </div>

      {active && (
        <p className="text-white/40 text-xs mt-2">
          Now playing <span className="text-white/70 font-semibold">{active.name}</span>
          {active.country ? ` · ${active.country}` : ''} — {reasonOf(active).label.toLowerCase()}.
          It may not be showing this exact match.
        </p>
      )}

      {/* The question this answers: "why can't it find a dedicated channel?" */}
      {noHolderPlayable && offlineHolders.length > 0 && (
        <p className="text-xs text-amber-200/70 bg-amber-400/10 ring-1 ring-amber-400/20 rounded-lg px-3 py-2 mt-3">
          {offlineHolders.map((c) => c.name).join(', ')} hold the rights to this competition,
          but {offlineHolders.length === 1 ? 'that free feed is' : 'those free feeds are'}{' '}
          geo-blocked or offline right now — so only general football channels are left below.
        </p>
      )}

      <div className="flex flex-col gap-2 mt-3">
        {playable.map((c) => {
          const reason = reasonOf(c)
          return (
            <button
              key={c.id}
              onClick={() => c.alive !== false && setActive(c)}
              disabled={c.alive === false}
              className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg border text-left transition-colors ${
                active?.id === c.id
                  ? 'border-yellow-400 text-yellow-300 bg-yellow-400/10'
                  : c.alive === false
                    ? 'border-white/5 text-white/30 cursor-not-allowed'
                    : 'border-white/10 text-white/70 hover:border-green-500 hover:text-green-400'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${c.alive === false ? 'bg-white/20' : 'bg-green-400 animate-pulse'}`} />
              <span className="truncate">{c.name}{c.country ? ` · ${c.country}` : ''}</span>
              <span className={`ml-auto shrink-0 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${reason.tone}`}>
                {reason.label}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
