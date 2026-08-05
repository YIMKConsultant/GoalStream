import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Clapperboard } from 'lucide-react'
import api from '../api/client'
import { HlsPlayer } from '../components/StreamPlayer'

// Yellow pill button, matching the Live page.
const yBtn = 'inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-base font-semibold ' +
  'text-yellow-300 bg-yellow-400/15 ring-1 ring-yellow-400/40 hover:bg-yellow-400/25 transition-colors'

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
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="mb-6">
        <Link to="/live" className={yBtn}><ArrowLeft size={18} /> Live</Link>
        <h1 className="text-4xl font-extrabold mt-3 mb-1">Replays &amp; <span className="text-yellow-400">Classic Matches</span></h1>
      </div>

      {active && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-xl font-bold">{active.name}</h2>
              <p className="text-white/40 text-sm">{active.country ?? '—'}{active.quality ? ` · ${active.quality}` : ''}</p>
            </div>
            <button onClick={() => setActive(null)} className={yBtn}>✕ Close</button>
          </div>
          <div className="aspect-video bg-black rounded-xl overflow-hidden">
            <HlsPlayer key={active.id} src={active.proxied_url} />
          </div>
        </div>
      )}

      <label className="flex items-center gap-2 text-base text-white/60 mb-5 cursor-pointer w-fit">
        <input type="checkbox" checked={showOffline} onChange={(e) => setShowOffline(e.target.checked)} />
        Show offline channels too
      </label>

      {loading ? (
        <div className="text-white/30 text-center py-16 text-lg">Checking channels…</div>
      ) : error ? (
        <div className="text-red-400 text-center py-16 text-lg">{error}</div>
      ) : channels.length === 0 ? (
        <p className="text-white/30 text-base">No replay channels are live right now.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {channels.map((c) => (
            <button
              key={c.id}
              onClick={() => c.alive && setActive(c)}
              disabled={!c.alive}
              className={`card text-left p-5 transition-transform ${
                c.alive ? 'hover:scale-[1.01]' : 'opacity-50 cursor-not-allowed'
              } ${active?.id === c.id ? 'border-yellow-400' : ''}`}
            >
              <div className="flex items-center justify-between mb-3 text-sm">
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
                <Clapperboard size={30} className="text-yellow-400" />
                <span className="text-lg font-bold text-center">{c.name}</span>
                <span className="text-sm text-white/40">{c.alive ? (c.quality ?? 'Click to watch') : 'Currently unavailable'}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
