import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api/client'
import MatchCard from '../components/MatchCard'
import StandingsTable from '../components/StandingsTable'
import { isLive, isUpcoming, isFinished } from '../lib/matchStatus'

const LEAGUE_NAMES = {
  PL: 'Premier League', CL: 'Champions League', EL: 'Europa League',
  ECL: 'Conference League', PD: 'La Liga', BL1: 'Bundesliga',
  SA: 'Serie A', FL1: 'Ligue 1', DED: 'Eredivisie', PPL: 'Primeira Liga',
  WC: 'FIFA World Cup', SPL: 'Saudi Pro League', MLS: 'Major League Soccer',
  CAFP: 'CAF Premier League', CAFW: "CAF Women's Champions League",
  WWC: "FIFA Women's World Cup",
}

export default function League() {
  const { code } = useParams()
  const [tab, setTab] = useState('matches')
  const [matches, setMatches] = useState([])
  const [standings, setStandings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [meta, setMeta] = useState(null)

  useEffect(() => {
    api.get('/leagues')
      .then((all) => setMeta(all.find((l) => l.code === code) ?? null))
      .catch(() => setMeta(null))
  }, [code])

  useEffect(() => {
    setLoading(true)
    setMatches([])
    setStandings(null)
    setTab('matches')
    api.get(`/leagues/${code}/matches`)
      .then(setMatches)
      .catch(() => setMatches([]))
      .finally(() => setLoading(false))
  }, [code])

  const loadStandings = () => {
    if (standings) { setTab('standings'); return }
    api.get(`/leagues/${code}/standings`)
      .then((data) => { setStandings(data); setTab('standings') })
      .catch(() => setTab('standings'))
  }

  const noFeed = meta?.fixtures === false

  const live     = matches.filter(isLive)
  const upcoming = matches.filter(isUpcoming)
    .sort((a, b) => new Date(a.utcDate) - new Date(b.utcDate))
  const finished = matches.filter(isFinished)
    .sort((a, b) => new Date(b.utcDate) - new Date(a.utcDate))

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-extrabold mb-1">{meta?.name ?? LEAGUE_NAMES[code] ?? code}</h1>
      <p className="text-white/40 text-sm mb-6">Current season fixtures &amp; results</p>

      {noFeed && (
        <div className="mb-6 rounded-xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-200/90">
          Our scores provider doesn&apos;t carry this competition, so fixtures and
          the table are empty here. You can still find it on{' '}
          <Link to="/live" className="underline hover:text-amber-100">Live</Link> — the
          channels that normally broadcast it are listed there.
        </div>
      )}

      {/* Upcoming matches — always visible above tabs */}
      {!loading && upcoming.length > 0 && (
        <section className="mb-6">
          <h2 className="text-lg font-bold mb-3 text-blue-400">Upcoming Games</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
            {upcoming.map((m) => <MatchCard key={m.id} match={m} />)}
          </div>
        </section>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-white/10 pb-3">
        {['matches', 'standings'].map((t) => (
          <button
            key={t}
            onClick={t === 'standings' ? loadStandings : () => setTab('matches')}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${
              tab === t ? 'bg-green-600 text-white' : 'text-white/50 hover:text-white'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {loading && <div className="text-white/30 text-center py-12">Loading…</div>}

      {!loading && tab === 'matches' && (
        <div className="space-y-8">
          {live.length > 0 && (
            <section>
              <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
                <span className="live-dot" /> Live
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                {live.map((m) => <MatchCard key={m.id} match={m} />)}
              </div>
            </section>
          )}
          {finished.length > 0 && (
            <section>
              <h2 className="text-lg font-bold mb-3 text-white/80">Results</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                {finished.map((m) => <MatchCard key={m.id} match={m} />)}
              </div>
            </section>
          )}
          {matches.length === 0 && (
            <p className="text-white/30 text-center py-12">No matches found for this league.</p>
          )}
        </div>
      )}

      {!loading && tab === 'standings' && (
        standings?.table?.length ? (
          <div className="card p-4">
            <StandingsTable table={standings.table} />
          </div>
        ) : (
          <p className="text-white/30 text-center py-12">No table available for this competition.</p>
        )
      )}
    </div>
  )
}
