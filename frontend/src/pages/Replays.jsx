import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { HlsPlayer } from '../components/StreamPlayer'

export default function Replays() {
  const [channels, setChannels] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showOffline, setShowOffline] = useState(false)
  const [active, setActive] = useState(null)

  useEffect(() => {
    setLoading(true)
    api.get(`/iptv/replays?include_offline=${showOffline}`)
      .then((data) => setChannels(data))
      .catch(() => setError('Could not load replay channels.'))
      .finally(() => setLoading(false))
  }, [showOffline])

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <Link to="/live" className="text-white/40 text-sm hover:text-green-400">← Live football</Link>
        <h1 className="text-3xl font-extrabold mt-1 mb-1">Replays & <span className="text-green-400">Classic Matches</span></h1>
        <p className="text-white/40 text-sm">
          Free 24/7 channels airing classic games & full-match replays — FIFA+ carries a World Cup archive.
          Live-status is checked on our server.
        </p>
      </div>

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

      <label className="flex items-center gap-2 text-sm text-white/50 mb-5 cursor-pointer w-fit">
        <input type="checkbox" checked={showOffline} onChange={(e) => setShowOffline(e.target.checked)} />
        Show offline channels too
      </label>

      {loading ? (
        <div className="text-white/30 text-center py-16">Checking channels…</div>
      ) : error ? (
        <div className="text-red-400 text-center py-16">{error}</div>
      ) : channels.length === 0 ? (
        <p className="text-white/30 text-sm">No replay channels are live right now.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {channels.map((c) => (
            <button
              key={c.id}
              onClick={() => c.alive && setActive(c)}
              disabled={!c.alive}
              className={`card text-left p-4 transition-transform ${
                c.alive ? 'hover:scale-[1.01]' : 'opacity-50 cursor-not-allowed'
              } ${active?.id === c.id ? 'border-green-500' : ''}`}
            >
              <div className="flex items-center justify-between mb-3 text-xs">
                <span className="text-white/40">{c.country ?? '—'}</span>
                {c.alive ? (
                  <span className="flex items-center gap-1 text-green-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" /> Live
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-white/30">
                    <span className="w-1.5 h-1.5 rounded-full bg-white/30" /> Offline
                  </span>
                )}
              </div>
              <div className="flex flex-col items-center gap-2 py-3">
                <span className="text-3xl">🎞️</span>
                <span className="text-base font-bold text-green-400 text-center">{c.name}</span>
                <span className="text-xs text-white/40">{c.alive ? (c.quality ?? 'Click to watch') : 'Currently unavailable'}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
