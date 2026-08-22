import { useCallback, useEffect, useState } from 'react'
import { Search, EyeOff, Eye, RotateCcw } from 'lucide-react'
import api from '../../api/client'

const TIERS = ['public', 'free', 'member', 'premium']

const TIER_HELP = {
  public:  'Anyone, including visitors who have not signed in',
  free:    'Signed-in accounts only — hidden from the free page',
  member:  'Member and premium accounts',
  premium: 'Premium accounts only',
}

const tierPill = (tier) => ({
  public:  'bg-white/10 text-white/60',
  free:    'bg-sky-400/15 text-sky-300 ring-1 ring-sky-400/30',
  member:  'bg-violet-400/15 text-violet-300 ring-1 ring-violet-400/30',
  premium: 'bg-yellow-400/15 text-yellow-300 ring-1 ring-yellow-400/30',
}[tier] ?? 'bg-white/10 text-white/60')

export default function AdminChannels() {
  const [channels, setChannels] = useState([])
  const [q, setQ] = useState('')
  const [tierFilter, setTierFilter] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    const params = new URLSearchParams({ limit: '500' })
    if (q) params.set('q', q)
    if (tierFilter) params.set('tier', tierFilter)
    api.get(`/admin/channels?${params}`)
      .then(setChannels).catch(setError).finally(() => setLoading(false))
  }, [q, tierFilter])

  useEffect(() => {
    const id = setTimeout(load, 250)     // debounce the search box
    return () => clearTimeout(id)
  }, [load])

  const save = async (channel, changes) => {
    setBusy(channel.id); setError('')
    const next = { tier: channel.tier, hidden: channel.hidden, note: channel.note, ...changes }
    try {
      const updated = await api.put(`/admin/channels/${channel.id}/policy`, next)
      setChannels((list) => list.map((c) => (c.id === channel.id ? updated : c)))
    } catch (e) { setError(e) } finally { setBusy('') }
  }

  const reset = async (channel) => {
    setBusy(channel.id); setError('')
    try {
      await api.delete(`/admin/channels/${channel.id}/policy`)
      load()
    } catch (e) { setError(e) } finally { setBusy('') }
  }

  return (
    <div>
      <h2 className="text-lg font-bold mb-1">Channels</h2>
      <p className="text-white/40 text-sm mb-5">
        A channel&apos;s tier is the minimum a viewer needs. Anything above{' '}
        <span className="text-sky-300 font-semibold">public</span> disappears from the
        free watching page until the visitor signs in.
      </p>

      <div className="flex flex-wrap gap-3 mb-5">
        <div className="relative flex-1 min-w-[240px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
          <input
            value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search channel or country…"
            className="w-full bg-pitch-800 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-sm focus:border-yellow-400/50 outline-none"
          />
        </div>
        <select
          value={tierFilter} onChange={(e) => setTierFilter(e.target.value)}
          className="bg-pitch-800 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-yellow-400/50"
        >
          <option value="">All tiers</option>
          {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      <div className="flex flex-wrap gap-3 mb-5 text-xs">
        {TIERS.map((t) => (
          <span key={t} className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded-full font-bold ${tierPill(t)}`}>{t}</span>
            <span className="text-white/40">{TIER_HELP[t]}</span>
          </span>
        ))}
      </div>

      {error && <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm px-4 py-2 rounded-lg mb-4">{String(error)}</div>}

      {loading ? (
        <p className="text-white/30">Loading catalog…</p>
      ) : (
        <>
          <p className="text-white/30 text-xs mb-2">{channels.length} channels</p>
          <div className="card divide-y divide-white/5">
            {channels.map((c) => (
              <div key={c.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-sm truncate">
                    {c.name}
                    {c.customised && (
                      <span className="ml-2 text-[10px] font-bold uppercase text-yellow-300/70">custom</span>
                    )}
                  </p>
                  <p className="text-xs text-white/40">{c.country ?? '—'} · {c.id}</p>
                </div>

                <select
                  value={c.tier}
                  disabled={busy === c.id}
                  onChange={(e) => save(c, { tier: e.target.value })}
                  className={`rounded-full px-3 py-1 text-xs font-bold outline-none cursor-pointer disabled:opacity-50 ${tierPill(c.tier)}`}
                >
                  {TIERS.map((t) => <option key={t} value={t} className="bg-pitch-800 text-white">{t}</option>)}
                </select>

                <button
                  onClick={() => save(c, { hidden: !c.hidden })}
                  disabled={busy === c.id}
                  title={c.hidden ? 'Hidden from every listing' : 'Visible'}
                  className={`p-1.5 rounded-lg transition-colors disabled:opacity-50 ${
                    c.hidden ? 'bg-red-500/15 text-red-300' : 'text-white/30 hover:text-white'}`}
                >
                  {c.hidden ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>

                <button
                  onClick={() => reset(c)}
                  disabled={busy === c.id || !c.customised}
                  title="Reset to the default tier"
                  className="p-1.5 rounded-lg text-white/30 hover:text-yellow-300 transition-colors disabled:opacity-20"
                >
                  <RotateCcw size={16} />
                </button>
              </div>
            ))}
            {channels.length === 0 && (
              <p className="text-center text-white/30 py-10">No channels match.</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}
