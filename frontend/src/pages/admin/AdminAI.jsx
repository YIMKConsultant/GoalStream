import { useEffect, useState } from 'react'
import { Sparkles, KeyRound, Save, Plug, Trash2, ShieldAlert, Check } from 'lucide-react'
import api from '../../api/client'

const CONF = {
  high:   'bg-green-500/15 text-green-300 ring-1 ring-green-400/30',
  medium: 'bg-yellow-400/15 text-yellow-300 ring-1 ring-yellow-400/30',
  low:    'bg-white/10 text-white/50',
}

export default function AdminAI() {
  const [status, setStatus] = useState(null)
  const [leagues, setLeagues] = useState([])
  const [league, setLeague] = useState('')
  const [key, setKey] = useState('')
  const [model, setModel] = useState('')
  const [result, setResult] = useState(null)
  const [map, setMap] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')

  const loadStatus = () => api.get('/admin/ai/status').then(setStatus).catch(setError)

  useEffect(() => {
    loadStatus()
    api.get('/leagues').then((d) => {
      setLeagues(d)
      if (d.length) setLeague(d[0].code)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!league) return
    setResult(null)
    api.get(`/admin/ai/map/${league}`).then(setMap).catch(() => setMap(null))
  }, [league])

  const saveKey = async (e) => {
    e.preventDefault()
    setBusy('save'); setError(''); setOk('')
    const values = {}
    if (key) values.anthropic_api_key = key
    if (model) values.ai_model = model
    try {
      await api.put('/admin/settings', { values })
      setKey(''); setModel('')
      await loadStatus()
      setOk('Saved — live now.')
    } catch (err) { setError(err) } finally { setBusy('') }
  }

  const test = async () => {
    setBusy('test'); setError(''); setOk('')
    try {
      const r = await api.post('/admin/ai/test')
      setOk(`Connected to ${r.model} — replied "${r.reply}" (${r.input_tokens} in / ${r.output_tokens} out).`)
    } catch (err) { setError(err) } finally { setBusy('') }
  }

  const discover = async () => {
    setBusy('discover'); setError(''); setOk(''); setResult(null)
    try {
      const r = await api.post(`/admin/ai/discover/${league}?persist=true`)
      setResult(r)
      const m = await api.get(`/admin/ai/map/${league}`)
      setMap(m)
      setOk(`Saved ${r.matches.length} channels as the ${r.league_name} map.`)
    } catch (err) { setError(err) } finally { setBusy('') }
  }

  const clearMap = async () => {
    setBusy('clear'); setError(''); setOk('')
    try {
      await api.delete(`/admin/ai/map/${league}`)
      setMap(await api.get(`/admin/ai/map/${league}`))
      setResult(null)
      setOk('Map cleared — this league is back on the keyword fallback.')
    } catch (err) { setError(err) } finally { setBusy('') }
  }

  return (
    <div className="max-w-3xl">
      <h2 className="text-lg font-bold flex items-center gap-2 mb-1">
        <Sparkles size={20} className="text-yellow-400" /> AI channel discovery
      </h2>
      <p className="text-white/40 text-sm mb-5">
        Claude reads the free channel catalog and picks the broadcasters that carry
        each competition — replacing the hand-maintained keyword lists.
      </p>

      <div className="flex gap-3 rounded-xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 mb-6 text-sm text-amber-200/90">
        <ShieldAlert size={18} className="shrink-0 mt-0.5" />
        <p>
          This searches the <strong>free, legal</strong> catalog only. sooka, Astro GO,
          unifi TV, beIN and ESPN+ are licensed subscription services with no lawful
          free stream, so they are not searched — viewers are deep-linked to those
          providers instead.
        </p>
      </div>

      {error && <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm px-4 py-2 rounded-lg mb-4">{String(error)}</div>}
      {ok && <div className="bg-green-900/30 border border-green-700 text-green-300 text-sm px-4 py-2 rounded-lg mb-4">{ok}</div>}

      {/* ── Key ── */}
      <section className="card p-5 mb-6">
        <h3 className="font-bold mb-3 flex items-center gap-2"><KeyRound size={16} className="text-yellow-400" /> Claude API key</h3>
        <p className="text-sm text-white/50 mb-4">
          {status?.configured
            ? <>Configured — <code className="text-white/70">{status.key_preview}</code> using <code className="text-white/70">{status.model}</code>.</>
            : <>Not configured. Get a key at <span className="text-white/70">console.anthropic.com</span>.</>}
        </p>

        <form onSubmit={saveKey} className="space-y-3">
          <input
            type="text" value={key} onChange={(e) => setKey(e.target.value)}
            placeholder={status?.configured ? 'Paste a new key to replace it' : 'sk-ant-...'}
            className="w-full bg-pitch-900 border border-white/10 rounded-lg px-4 py-2.5 text-white font-mono text-sm focus:border-yellow-400/50 outline-none"
          />
          <input
            type="text" value={model} onChange={(e) => setModel(e.target.value)}
            placeholder={status?.model ?? 'claude-opus-5'}
            className="w-full bg-pitch-900 border border-white/10 rounded-lg px-4 py-2.5 text-white font-mono text-sm focus:border-yellow-400/50 outline-none"
          />
          <div className="flex gap-2">
            <button type="submit" disabled={busy === 'save' || (!key && !model)}
              className="btn-primary flex items-center gap-2 px-4 py-2 text-sm disabled:opacity-40">
              <Save size={15} /> {busy === 'save' ? 'Saving…' : 'Save'}
            </button>
            <button type="button" onClick={test} disabled={busy === 'test' || !status?.configured}
              className="btn-ghost flex items-center gap-2 px-4 py-2 text-sm disabled:opacity-40">
              <Plug size={15} /> {busy === 'test' ? 'Testing…' : 'Test connection'}
            </button>
          </div>
        </form>
      </section>

      {/* ── Discovery ── */}
      <section className="card p-5">
        <h3 className="font-bold mb-3">Build a league&apos;s channel map</h3>
        <div className="flex flex-wrap gap-2 mb-4">
          <select
            value={league} onChange={(e) => setLeague(e.target.value)}
            className="bg-pitch-900 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-yellow-400/50"
          >
            {leagues.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
          </select>
          <button onClick={discover} disabled={busy === 'discover' || !status?.configured}
            className="btn-primary flex items-center gap-2 px-4 py-2 text-sm disabled:opacity-40">
            <Sparkles size={15} /> {busy === 'discover' ? 'Claude is reading the catalog…' : 'Run discovery'}
          </button>
          {map?.using_ai_map && (
            <button onClick={clearMap} disabled={busy === 'clear'}
              className="btn-ghost flex items-center gap-2 px-3 py-2 text-sm text-white/50 hover:text-red-300 disabled:opacity-40">
              <Trash2 size={15} /> Clear map
            </button>
          )}
        </div>

        {result?.notes && <p className="text-sm text-white/50 mb-3 italic">{result.notes}</p>}
        {result?.unknown_ids?.length > 0 && (
          <p className="text-xs text-amber-300/80 mb-3">
            Dropped {result.unknown_ids.length} suggested id(s) not present in the catalog.
          </p>
        )}

        {map === null ? (
          <p className="text-white/30 text-sm">Loading…</p>
        ) : !map.using_ai_map ? (
          <p className="text-white/30 text-sm">
            No map yet — this league uses the keyword fallback. Run discovery to replace it.
          </p>
        ) : (
          <>
            <p className="text-xs text-green-300/70 mb-2 flex items-center gap-1.5">
              <Check size={13} /> {map.channels.length} channels — live now on Live and match pages
            </p>
            <div className="divide-y divide-white/5">
              {map.channels.map((c, i) => (
                <div key={c.channel_id} className="flex items-start gap-3 py-2.5">
                  <span className="text-white/25 text-xs font-mono w-5 shrink-0 pt-0.5">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold">
                      {c.name} <span className="text-white/30 font-normal">{c.country ?? ''}</span>
                    </p>
                    {c.note && <p className="text-xs text-white/40 mt-0.5">{c.note}</p>}
                  </div>
                  <span className={`shrink-0 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${CONF[c.confidence] ?? CONF.low}`}>
                    {c.confidence}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  )
}
