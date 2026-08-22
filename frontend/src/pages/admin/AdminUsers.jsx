import { useCallback, useEffect, useMemo, useState } from 'react'
import { Search, Trash2, X, Check, Ban } from 'lucide-react'
import api from '../../api/client'
import { useAuth } from '../../context/AuthContext'

const TIERS = ['public', 'free', 'member', 'premium']

const tierPill = (tier) => ({
  public:  'bg-white/10 text-white/60',
  free:    'bg-sky-400/15 text-sky-300 ring-1 ring-sky-400/30',
  member:  'bg-violet-400/15 text-violet-300 ring-1 ring-violet-400/30',
  premium: 'bg-yellow-400/15 text-yellow-300 ring-1 ring-yellow-400/30',
}[tier] ?? 'bg-white/10 text-white/60')

// Panel for granting / blocking individual channels for one user.
function GrantEditor({ user, channels, onClose }) {
  const [grants, setGrants] = useState({})
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.get(`/admin/users/${user.id}/grants`)
      .then((rows) => setGrants(Object.fromEntries(rows.map((g) => [g.channel_id, g.mode]))))
      .catch(setError)
  }, [user.id])

  const setMode = async (channelId, mode) => {
    setBusy(channelId); setError('')
    try {
      if (mode === null) {
        await api.delete(`/admin/users/${user.id}/grants/${channelId}`)
        setGrants((g) => { const n = { ...g }; delete n[channelId]; return n })
      } else {
        await api.put(`/admin/users/${user.id}/grants/${channelId}`, { mode })
        setGrants((g) => ({ ...g, [channelId]: mode }))
      }
    } catch (e) { setError(e) } finally { setBusy('') }
  }

  // Overridden channels first, then whatever matches the search.
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const matched = needle
      ? channels.filter((c) => c.name.toLowerCase().includes(needle))
      : channels.filter((c) => grants[c.id])
    return matched.slice(0, 60)
  }, [channels, q, grants])

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div className="card w-full max-w-2xl max-h-[85vh] flex flex-col p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-lg font-bold">Channel overrides — {user.username}</h2>
          <button onClick={onClose} className="text-white/40 hover:text-white"><X size={20} /></button>
        </div>
        <p className="text-white/40 text-sm mb-4">
          Overrides beat the tier rules. Tier is <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${tierPill(user.tier)}`}>{user.tier}</span>.
        </p>

        {error && <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm px-3 py-2 rounded-lg mb-3">{String(error)}</div>}

        <div className="relative mb-4">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
          <input
            value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search channels to add an override…"
            className="w-full bg-pitch-900 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-sm focus:border-yellow-400/50 outline-none"
          />
        </div>

        <div className="flex-1 overflow-y-auto -mx-2 px-2">
          {shown.length === 0 ? (
            <p className="text-white/30 text-sm py-8 text-center">
              {q ? 'No channels match.' : 'No overrides yet — search above to add one.'}
            </p>
          ) : shown.map((c) => {
            const mode = grants[c.id]
            return (
              <div key={c.id} className="flex items-center gap-3 py-2 border-b border-white/5">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{c.name}</p>
                  <p className="text-xs text-white/40">{c.country ?? '—'} · needs {c.tier}</p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <button
                    onClick={() => setMode(c.id, mode === 'allow' ? null : 'allow')}
                    disabled={busy === c.id}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold flex items-center gap-1 transition-colors disabled:opacity-50 ${
                      mode === 'allow' ? 'bg-green-500/20 text-green-300 ring-1 ring-green-400/40'
                                       : 'text-white/40 hover:text-green-300 hover:bg-white/5'}`}
                  >
                    <Check size={13} /> Allow
                  </button>
                  <button
                    onClick={() => setMode(c.id, mode === 'block' ? null : 'block')}
                    disabled={busy === c.id}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold flex items-center gap-1 transition-colors disabled:opacity-50 ${
                      mode === 'block' ? 'bg-red-500/20 text-red-300 ring-1 ring-red-400/40'
                                       : 'text-white/40 hover:text-red-300 hover:bg-white/5'}`}
                  >
                    <Ban size={13} /> Block
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default function AdminUsers() {
  const { user: me } = useAuth()
  const [users, setUsers] = useState([])
  const [channels, setChannels] = useState([])
  const [q, setQ] = useState('')
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null)

  const load = useCallback(() => {
    api.get(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ''}`).then(setUsers).catch(setError)
  }, [q])

  useEffect(() => { load() }, [load])
  useEffect(() => { api.get('/admin/channels?limit=1000').then(setChannels).catch(() => {}) }, [])

  const patch = async (id, changes) => {
    setError('')
    try {
      const updated = await api.patch(`/admin/users/${id}`, changes)
      setUsers((list) => list.map((u) => (u.id === id ? updated : u)))
    } catch (e) { setError(e) }
  }

  const remove = async (u) => {
    if (!window.confirm(`Delete ${u.username}? This also removes their grants and favourites.`)) return
    setError('')
    try {
      await api.delete(`/admin/users/${u.id}`)
      setUsers((list) => list.filter((x) => x.id !== u.id))
    } catch (e) { setError(e) }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-4 mb-5">
        <h2 className="text-lg font-bold">Users</h2>
        <div className="relative w-full sm:w-80 sm:ml-auto">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
          <input
            value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search username or email…"
            className="w-full bg-pitch-800 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-sm focus:border-yellow-400/50 outline-none"
          />
        </div>
      </div>

      {error && <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm px-4 py-2 rounded-lg mb-4">{String(error)}</div>}

      <div className="card overflow-x-auto">
        <table className="w-full text-sm min-w-[860px]">
          <thead className="text-white/40 text-xs uppercase tracking-wide">
            <tr className="border-b border-white/10">
              <th className="text-left font-semibold px-4 py-3">User</th>
              <th className="text-left font-semibold px-4 py-3">Tier</th>
              <th className="text-left font-semibold px-4 py-3">Role</th>
              <th className="text-left font-semibold px-4 py-3">Status</th>
              <th className="text-right font-semibold px-4 py-3">Channels</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-white/5 last:border-0">
                <td className="px-4 py-3">
                  <p className="font-semibold">{u.username}</p>
                  <p className="text-xs text-white/40">{u.email}</p>
                </td>
                <td className="px-4 py-3">
                  <select
                    value={u.tier}
                    onChange={(e) => patch(u.id, { tier: e.target.value })}
                    className={`rounded-full px-3 py-1 text-xs font-bold outline-none cursor-pointer ${tierPill(u.tier)}`}
                  >
                    {TIERS.map((t) => <option key={t} value={t} className="bg-pitch-800 text-white">{t}</option>)}
                  </select>
                </td>
                <td className="px-4 py-3">
                  {me?.is_superuser ? (
                    <div className="flex gap-3 text-xs">
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input type="checkbox" checked={u.is_admin}
                          onChange={(e) => patch(u.id, { is_admin: e.target.checked })} />
                        admin
                      </label>
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input type="checkbox" checked={u.is_superuser}
                          onChange={(e) => patch(u.id, { is_superuser: e.target.checked })} />
                        super
                      </label>
                    </div>
                  ) : (
                    <span className="text-xs text-white/40">
                      {u.is_superuser ? 'superuser' : u.is_admin ? 'admin' : 'user'}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => patch(u.id, { is_active: !u.is_active })}
                    className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                      u.is_active ? 'bg-green-500/15 text-green-300' : 'bg-red-500/15 text-red-300'}`}
                  >
                    {u.is_active ? 'active' : 'disabled'}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-2">
                    <button onClick={() => setEditing(u)}
                      className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-white/15 text-white/70 hover:border-yellow-400 hover:text-yellow-300 transition-colors">
                      Overrides
                    </button>
                    {me?.is_superuser && u.id !== me.id && (
                      <button onClick={() => remove(u)} title="Delete user"
                        className="text-white/30 hover:text-red-400 transition-colors">
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr><td colSpan={5} className="text-center text-white/30 py-10">No users found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {editing && (
        <GrantEditor user={editing} channels={channels} onClose={() => setEditing(null)} />
      )}
    </div>
  )
}
