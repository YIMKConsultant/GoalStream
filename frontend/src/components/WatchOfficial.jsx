import { useEffect, useState } from 'react'
import { ExternalLink, Ticket } from 'lucide-react'
import api from '../api/client'

/**
 * Where a competition can legitimately be watched.
 *
 * This is the honest answer to "how do I watch this match". The free catalog
 * carries no rights holder for any competition — measured, not assumed — so
 * offering a general football channel under a fixture was telling the viewer
 * their match was on when it wasn't. A link to the actual broadcaster is a
 * smaller promise and a true one.
 */
export default function WatchOfficial({ leagueCode, leagueName, compact = false }) {
  const [providers, setProviders] = useState(null)

  useEffect(() => {
    if (!leagueCode) return
    let cancelled = false
    api.get(`/leagues/${leagueCode}/watch`)
      .then((d) => { if (!cancelled) setProviders(d.providers ?? []) })
      .catch(() => { if (!cancelled) setProviders([]) })
    return () => { cancelled = true }
  }, [leagueCode])

  if (!providers?.length) return null

  return (
    <div className={`rounded-lg bg-white/[0.03] ring-1 ring-white/10 ${compact ? 'p-3' : 'p-4'}`}>
      <p className="text-xs text-white/50 mb-2.5">
        No free channel carries {leagueName || 'this competition'}. It's on:
      </p>
      <div className="flex flex-wrap gap-2">
        {providers.map((p) => (
          <a
            key={p.name}
            href={p.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-white/10
                       text-white/75 hover:border-yellow-400 hover:text-yellow-300 transition-colors"
          >
            {p.free ? <Ticket size={12} className="text-emerald-400" /> : <ExternalLink size={12} />}
            <span className="font-medium">{p.name}</span>
            <span className="text-white/30">{p.region}</span>
            {p.free && (
              <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full
                               bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/30">
                Free
              </span>
            )}
          </a>
        ))}
      </div>
    </div>
  )
}
