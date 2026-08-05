import { useEffect, useState } from 'react'
import { Radio, Tv } from 'lucide-react'
import api from '../api/client'
import { HlsPlayer } from '../components/StreamPlayer'

export default function Featured() {
  const [channels, setChannels] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [active, setActive] = useState(null)

  useEffect(() => {
    setLoading(true)
    api.get('/iptv/featured')
      .then((data) => setChannels(data))
      .catch(() => setError('Could not load channels.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6 lg:p-8">
      <div className="flex items-center gap-2 mb-1">
        <h1 className="text-3xl font-extrabold">Featured</h1>
        <span className="flex items-center gap-1 text-red-400 text-sm font-bold">
          <Radio size={15} className="animate-pulse" /> LIVE
        </span>
      </div>
      <p className="text-white/40 text-base mb-6">Channels streaming right now — verified live on our server.</p>

      {active && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-bold">{active.name}</h2>
              <p className="text-white/40 text-xs">{active.country ?? '—'}{active.quality ? ` · ${active.quality}` : ''}</p>
            </div>
            <button onClick={() => setActive(null)} className="text-sm px-3 py-1.5 rounded-lg border border-white/15 text-white/70 hover:border-yellow-400 hover:text-yellow-300 transition-colors">✕ Close</button>
          </div>
          <div className="aspect-video bg-black rounded-xl overflow-hidden">
            <HlsPlayer key={active.id} src={active.proxied_url} />
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-white/30 text-center py-16">Checking which channels are live…</div>
      ) : error ? (
        <div className="text-red-400 text-center py-16">{error}</div>
      ) : channels.length === 0 ? (
        <p className="text-white/30 text-sm">No channels are streaming right now — check back around kickoff time.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {channels.map((c) => (
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
              <div className="flex flex-col items-center gap-2 py-3">
                <Tv size={26} className="text-yellow-400" />
                <span className="text-base font-bold text-center">{c.name}</span>
                <span className="text-xs text-white/40">{c.quality ?? 'Click to watch'}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
