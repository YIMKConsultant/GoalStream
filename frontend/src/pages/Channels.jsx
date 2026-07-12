import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { HlsPlayer } from '../components/StreamPlayer'

export default function Channels() {
  const [channels, setChannels] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [country, setCountry] = useState('')
  const [active, setActive] = useState(null)

  useEffect(() => {
    api.get('/iptv/channels')
      .then((data) => setChannels(data))
      .catch(() => setError('Could not load live channels from iptv-org.'))
      .finally(() => setLoading(false))
  }, [])

  const countries = useMemo(() => {
    const counts = {}
    for (const c of channels) if (c.country) counts[c.country] = (counts[c.country] || 0) + 1
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([code]) => code)
  }, [channels])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return channels.filter((c) =>
      (!country || c.country === country) &&
      (!q || c.name.toLowerCase().includes(q))
    )
  }, [channels, query, country])

  if (loading) return <div className="text-white/30 text-center py-24">Loading live channels…</div>
  if (error)   return <div className="text-red-400 text-center py-24">{error}</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <Link to="/live" className="text-white/40 text-sm hover:text-green-400">← Live football</Link>
        <h1 className="text-3xl font-extrabold mt-1 mb-1">All Live <span className="text-green-400">Sports</span> Channels</h1>
        <p className="text-white/40 text-sm">
          {channels.length} channels · sourced from the free iptv-org catalog
        </p>
      </div>

      {active && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-bold">{active.name}</h2>
              <p className="text-white/40 text-xs">
                {active.country ?? '—'}{active.quality ? ` · ${active.quality}` : ''}
              </p>
            </div>
            <button onClick={() => setActive(null)} className="btn-ghost text-sm px-3 py-1.5">✕ Close</button>
          </div>
          <div className="aspect-video bg-black rounded-xl overflow-hidden">
            <HlsPlayer key={active.id} src={active.proxied_url} />
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-5">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search channels…"
          className="flex-1 min-w-[200px] bg-pitch-800 border border-white/10 rounded-lg px-4 py-2 text-sm focus:border-green-500 outline-none"
        />
        <select
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="bg-pitch-800 border border-white/10 rounded-lg px-4 py-2 text-sm focus:border-green-500 outline-none"
        >
          <option value="">All countries ({channels.length})</option>
          {countries.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {filtered.length === 0 ? (
        <p className="text-white/30 text-sm">No channels match your search.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((c) => (
            <button
              key={c.id}
              onClick={() => setActive(c)}
              className={`card text-left p-4 hover:scale-[1.01] transition-transform ${
                active?.id === c.id ? 'border-green-500' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-3 text-xs text-white/40">
                <span>{c.country ?? '—'}</span>
                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-white text-[10px] font-bold bg-red-600">
                  LIVE
                </span>
              </div>
              <div className="flex flex-col items-center gap-2 py-3">
                <span className="text-3xl">📺</span>
                <span className="text-base font-bold text-green-400 text-center">{c.name}</span>
                <span className="text-xs text-white/40">{c.quality ?? 'Click to watch'}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
