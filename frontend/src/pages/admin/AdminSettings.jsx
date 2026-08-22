import { useEffect, useState } from 'react'
import { KeyRound, Save, ShieldAlert } from 'lucide-react'
import api from '../../api/client'

export default function AdminSettings() {
  const [rows, setRows] = useState([])
  const [edits, setEdits] = useState({})
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)

  const load = () => api.get('/admin/settings').then((d) => setRows(d.settings)).catch(setError)
  useEffect(() => { load() }, [])

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setSaved(false); setSaving(true)
    try {
      const d = await api.put('/admin/settings', { values: edits })
      setRows(d.settings)
      setEdits({})
      setSaved(true)
    } catch (err) { setError(err) } finally { setSaving(false) }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-bold mb-1">Settings</h2>
      <p className="text-white/40 text-sm mb-5">
        These override <code className="text-white/60">backend/.env</code> and take effect
        immediately — no restart. Superuser only.
      </p>

      <div className="flex gap-3 rounded-xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 mb-6 text-sm text-amber-200/90">
        <ShieldAlert size={18} className="shrink-0 mt-0.5" />
        <p>
          Saved values live in the <code>app_settings</code> table in plain text.
          Anyone with the database file can read the API key.
        </p>
      </div>

      {error && <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm px-4 py-2 rounded-lg mb-4">{String(error)}</div>}
      {saved && <div className="bg-green-900/30 border border-green-700 text-green-300 text-sm px-4 py-2 rounded-lg mb-4">Saved — live now.</div>}

      <form onSubmit={submit} className="space-y-5">
        {rows.map((row) => (
          <div key={row.key}>
            <label className="flex items-center gap-2 text-sm text-white/70 mb-1">
              {row.secret && <KeyRound size={14} className="text-yellow-400" />}
              {row.label}
              {row.overridden && (
                <span className="text-[10px] font-bold uppercase text-yellow-300/70">overridden</span>
              )}
            </label>
            <input
              type="text"
              value={edits[row.key] ?? ''}
              placeholder={row.value || (row.secret ? 'not set' : '')}
              onChange={(e) => setEdits({ ...edits, [row.key]: e.target.value })}
              className="w-full bg-pitch-900 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-yellow-400/50 outline-none transition-colors font-mono text-sm"
            />
            <p className="text-xs text-white/30 mt-1">
              {row.secret
                ? `Currently ${row.value || 'unset'} — leave blank to keep it.`
                : `Currently ${row.value || 'unset'}.`}
            </p>
          </div>
        ))}

        <button
          type="submit"
          disabled={saving || Object.keys(edits).length === 0}
          className="btn-primary flex items-center gap-2 px-5 py-2.5 disabled:opacity-40"
        >
          <Save size={16} /> {saving ? 'Saving…' : 'Save changes'}
        </button>
      </form>
    </div>
  )
}
