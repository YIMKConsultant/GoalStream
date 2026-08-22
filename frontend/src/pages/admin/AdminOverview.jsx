import { useEffect, useState } from 'react'
import { Users, Tv, Lock, KeyRound, Globe, Radio } from 'lucide-react'
import api from '../../api/client'

function Stat({ icon: Icon, label, value, hint }) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 text-white/40 text-xs font-semibold uppercase tracking-wide mb-2">
        <Icon size={14} /> {label}
      </div>
      <p className="text-3xl font-black tabular-nums">{value}</p>
      {hint && <p className="text-xs text-white/40 mt-1">{hint}</p>}
    </div>
  )
}

export default function AdminOverview() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  const load = () => api.get('/admin/stats').then(setStats).catch(setError)

  useEffect(() => {
    load()
    const id = setInterval(load, 15000)   // presence numbers go stale fast
    return () => clearInterval(id)
  }, [])

  if (error) return <p className="text-red-300">{String(error)}</p>
  if (!stats) return <p className="text-white/30">Loading…</p>

  const p = stats.presence ?? { online: 0, watching: 0, countries: [] }

  return (
    <div className="space-y-8">
      <section>
        <h2 className="text-lg font-bold mb-3">Right now</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Stat icon={Radio} label="Online" value={p.online} hint={`in the last ${p.window_seconds ?? 120}s`} />
          <Stat icon={Tv} label="Watching" value={p.watching} hint="pulling a stream" />
          <Stat icon={Globe} label="Countries" value={p.countries.length} />
          <Stat icon={Users} label="Accounts" value={stats.users} hint={`${stats.admins} admin`} />
        </div>

        {p.countries.length > 0 && (
          <div className="card p-5 mt-4">
            <h3 className="font-bold mb-3 text-sm">Viewers by country</h3>
            <div className="space-y-2">
              {p.countries.map((c) => (
                <div key={c.code + c.country} className="flex items-center gap-3">
                  <span className="w-44 shrink-0 text-sm text-white/70 truncate">
                    {c.country} <span className="text-white/30">({c.code})</span>
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full bg-yellow-400"
                      style={{ width: `${Math.round((c.viewers / p.online) * 100)}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-sm font-bold tabular-nums">{c.viewers}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-bold mb-3">Library &amp; access</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Stat icon={Tv} label="Channels" value={stats.catalog_channels} hint="in the live catalog" />
          <Stat icon={Lock} label="Restricted" value={stats.restricted_channels} hint="have a custom tier" />
          <Stat icon={KeyRound} label="User grants" value={stats.grants} hint="per-user overrides" />
          <Stat icon={Globe} label="Leagues" value={stats.leagues} />
        </div>
      </section>

      <section>
        <h2 className="text-lg font-bold mb-3">Accounts by tier</h2>
        <div className="flex flex-wrap gap-3">
          {(stats.tiers ?? []).map((tier) => (
            <div key={tier} className="card px-5 py-3">
              <p className="text-xs text-white/40 uppercase tracking-wide">{tier}</p>
              <p className="text-2xl font-black tabular-nums">{stats.users_by_tier?.[tier] ?? 0}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
