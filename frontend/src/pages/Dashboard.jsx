import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Play, ArrowRight } from 'lucide-react'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useLiveScores } from '../hooks/useLiveScores'
import VideoEmbed from '../components/VideoEmbed'
import { badge, isLive, kickoffTime as kickoff } from '../lib/matchStatus'

// Big featured match card (the Assassin's Creed / PUBG slot in the template).
function FeatureMatch({ match }) {
  const b = badge(match.status)
  const h = match.score?.fullTime?.home ?? 0
  const a = match.score?.fullTime?.away ?? 0
  const live = isLive(match)
  return (
    <Link to={`/match/${match.id}`} className="card block p-5 hover:scale-[1.01] transition-transform">
      <div className="flex items-center justify-between mb-4 text-xs">
        <span className="text-white/40">{match.league_name}</span>
        <span className={`px-2 py-0.5 rounded-full text-white text-[10px] font-bold ${b.cls}`}>{b.text}</span>
      </div>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          {match.homeTeam.crest && <img src={match.homeTeam.crest} alt="" className="w-9 h-9 object-contain" />}
          <span className="font-semibold text-sm truncate">{match.homeTeam.shortName || match.homeTeam.name}</span>
        </div>
        <div className="text-center shrink-0">
          {live || match.status === 'FINISHED'
            ? <span className="text-2xl font-black tabular-nums">{h} <span className="text-white/20">:</span> {a}</span>
            : <span className="text-sm text-white/50">{kickoff(match.utcDate)}</span>}
        </div>
        <div className="flex items-center gap-2 min-w-0 flex-row-reverse text-right">
          {match.awayTeam.crest && <img src={match.awayTeam.crest} alt="" className="w-9 h-9 object-contain" />}
          <span className="font-semibold text-sm truncate">{match.awayTeam.shortName || match.awayTeam.name}</span>
        </div>
      </div>
    </Link>
  )
}

function RecentRow({ match }) {
  const b = badge(match.status)
  const h = match.score?.fullTime?.home ?? '-'
  const a = match.score?.fullTime?.away ?? '-'
  return (
    <Link to={`/match/${match.id}`} className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors">
      {match.homeTeam.crest && <img src={match.homeTeam.crest} alt="" className="w-7 h-7 object-contain shrink-0" />}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium truncate">
          {match.homeTeam.shortName || match.homeTeam.name} <span className="text-white/30">v</span> {match.awayTeam.shortName || match.awayTeam.name}
        </p>
        <p className="text-xs text-white/40">{match.league_name}</p>
      </div>
      <div className="text-right shrink-0">
        <span className="text-sm font-bold tabular-nums">{h}:{a}</span>
        <span className={`block text-[9px] font-bold px-1.5 rounded ${b.cls}`}>{b.text}</span>
      </div>
    </Link>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const live = useLiveScores()
  const [today, setToday] = useState([])
  const [hero, setHero] = useState(null)
  const [q, setQ] = useState('')

  useEffect(() => { api.get('/leagues/today').then(setToday).catch(() => setToday([])) }, [])
  useEffect(() => { api.get('/video/feed?limit=10').then((d) => setHero(d[0] ?? null)).catch(() => {}) }, [])

  // Featured = live matches first, then today's upcoming, deduped, top 2.
  const featured = useMemo(() => {
    const seen = new Set()
    const out = []
    for (const m of [...live, ...today]) {
      if (seen.has(m.id)) continue
      seen.add(m.id)
      out.push(m)
    }
    return out.slice(0, 2)
  }, [live, today])

  // Recent Matches rail = today's matches, filtered by search.
  const recent = useMemo(() => {
    const all = today.length ? today : live
    if (!q.trim()) return all.slice(0, 8)
    const needle = q.toLowerCase()
    return all.filter((m) =>
      (m.homeTeam.name + m.awayTeam.name + m.league_name).toLowerCase().includes(needle)
    ).slice(0, 12)
  }, [today, live, q])

  return (
    <div className="flex gap-6 p-6 lg:p-8">
      {/* Main column */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-6">
          <h1 className="text-3xl font-extrabold">Hello {user?.username || 'there'} !</h1>
          <div className="sm:ml-auto relative w-full sm:w-[400px]">
            <Search size={20} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search teams, leagues…"
              className="w-full bg-pitch-800 border border-white/10 rounded-xl pl-11 pr-4 py-3.5 text-base placeholder-white/30 focus:outline-none focus:border-yellow-400/50"
            />
          </div>
        </div>

        {/* Hero — latest Replay highlight */}
        <div className="rounded-2xl overflow-hidden bg-black mb-6">
          {hero ? (
            <VideoEmbed video={hero} />
          ) : (
            <div className="aspect-video flex flex-col items-center justify-center text-white/40 gap-2">
              <Play size={40} />
              <p className="text-sm">Loading latest highlight…</p>
            </div>
          )}
        </div>
        {hero && (
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="font-bold">{hero.title}</h2>
              <p className="text-xs text-white/40">{hero.competition} · Replay</p>
            </div>
            <Link to="/replay" className="text-sm text-yellow-400 hover:underline flex items-center gap-1">
              More replays <ArrowRight size={14} />
            </Link>
          </div>
        )}

        {/* Two featured matches */}
        <h2 className="text-lg font-bold mb-3">Featured matches</h2>
        {featured.length === 0 ? (
          <p className="text-white/30 text-sm">No matches to feature right now.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {featured.map((m) => <FeatureMatch key={m.id} match={m} />)}
          </div>
        )}
      </div>

      {/* Right rail — Recent Matches */}
      <aside className="hidden xl:block w-80 shrink-0">
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold">Recent Matches</h2>
            <Link to="/" className="text-white/40 hover:text-yellow-400"><ArrowRight size={18} /></Link>
          </div>
          {recent.length === 0 ? (
            <p className="text-white/30 text-sm">No matches today.</p>
          ) : (
            <div className="flex flex-col gap-1">
              {recent.map((m) => <RecentRow key={m.id} match={m} />)}
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
