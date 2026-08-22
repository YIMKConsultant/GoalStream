import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Trophy, Play } from 'lucide-react'
import api from '../api/client'

// Mirrors backend/config.py LEAGUES — used until /api/leagues answers, and as a
// fallback if it doesn't. `fixtures: false` = browsable, but the data provider
// has no fixture/standings feed for it.
const FALLBACK = [
  { code: 'PL',   name: 'Premier League',     country: 'England',      fixtures: true },
  { code: 'CL',   name: 'Champions League',   country: 'Europe',       fixtures: true },
  { code: 'EL',   name: 'Europa League',      country: 'Europe',       fixtures: true },
  { code: 'ECL',  name: 'Conference League',  country: 'Europe',       fixtures: true },
  { code: 'PD',   name: 'La Liga',            country: 'Spain',        fixtures: true },
  { code: 'BL1',  name: 'Bundesliga',         country: 'Germany',      fixtures: true },
  { code: 'SA',   name: 'Serie A',            country: 'Italy',        fixtures: true },
  { code: 'FL1',  name: 'Ligue 1',            country: 'France',       fixtures: true },
  { code: 'DED',  name: 'Eredivisie',         country: 'Netherlands',  fixtures: true },
  { code: 'PPL',  name: 'Primeira Liga',      country: 'Portugal',     fixtures: true },
  { code: 'WC',   name: 'FIFA World Cup',     country: 'World',        fixtures: true },
  { code: 'SPL',  name: 'Saudi Pro League',   country: 'Saudi Arabia', fixtures: false },
  { code: 'MLS',  name: 'Major League Soccer',country: 'USA & Canada', fixtures: false },
  { code: 'CAFP', name: 'CAF Premier League', country: 'Africa',       fixtures: false },
  { code: 'CAFW', name: "CAF Women's Champions League", country: 'Africa', fixtures: false },
  { code: 'WWC',  name: "FIFA Women's World Cup", country: 'World',    fixtures: false },
]

export default function Leagues() {
  const [leagues, setLeagues] = useState(FALLBACK)

  useEffect(() => {
    api.get('/leagues')
      .then((data) => { if (data?.length) setLeagues(data) })
      .catch(() => {})
  }, [])

  return (
    <div className="p-6 lg:p-8">
      <h1 className="text-3xl font-extrabold mb-1">Leagues</h1>
      <p className="text-white/40 text-base mb-6">
        Hit <span className="text-yellow-300 font-semibold">Watch</span> to start the competition
        on Live, or open a league for fixtures, results and standings.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {leagues.map((l) => (
          <div key={l.code} className="card p-5 flex items-center gap-4">
            <Link to={`/league/${l.code}`} className="flex items-center gap-4 min-w-0 flex-1 group">
              <span className="w-11 h-11 rounded-xl bg-yellow-400/15 ring-1 ring-yellow-400/30 flex items-center justify-center shrink-0">
                <Trophy size={20} className="text-yellow-400" />
              </span>
              <div className="min-w-0">
                <p className="font-bold truncate group-hover:text-yellow-300 transition-colors">{l.name}</p>
                <p className="text-xs text-white/40 truncate">
                  {l.country}
                  {l.fixtures === false && <span className="text-amber-300/70"> · channels only</span>}
                </p>
              </div>
            </Link>

            {/* Straight to the player — Live picks the channel itself. */}
            <Link
              to={`/live?league=${l.code}`}
              className="shrink-0 flex items-center gap-1.5 text-xs font-bold px-3 py-2 rounded-lg bg-yellow-400 text-pitch-900 hover:bg-yellow-300 transition-colors"
            >
              <Play size={13} /> Watch
            </Link>
          </div>
        ))}
      </div>
    </div>
  )
}
