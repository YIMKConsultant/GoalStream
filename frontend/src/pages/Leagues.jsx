import { Link } from 'react-router-dom'
import { Trophy } from 'lucide-react'

const LEAGUES = [
  { code: 'PL',  name: 'Premier League',    country: 'England' },
  { code: 'CL',  name: 'Champions League',  country: 'Europe' },
  { code: 'EL',  name: 'Europa League',     country: 'Europe' },
  { code: 'ECL', name: 'Conference League', country: 'Europe' },
  { code: 'PD',  name: 'La Liga',           country: 'Spain' },
  { code: 'BL1', name: 'Bundesliga',        country: 'Germany' },
  { code: 'SA',  name: 'Serie A',           country: 'Italy' },
  { code: 'FL1', name: 'Ligue 1',           country: 'France' },
  { code: 'DED', name: 'Eredivisie',        country: 'Netherlands' },
  { code: 'PPL', name: 'Primeira Liga',     country: 'Portugal' },
  { code: 'WC',  name: 'FIFA World Cup',     country: 'World' },
]

export default function Leagues() {
  return (
    <div className="p-6 lg:p-8">
      <h1 className="text-3xl font-extrabold mb-1">Leagues</h1>
      <p className="text-white/40 text-base mb-6">Pick a competition for fixtures, results and standings.</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {LEAGUES.map((l) => (
          <Link key={l.code} to={`/league/${l.code}`} className="card p-5 flex items-center gap-4 hover:scale-[1.01] transition-transform">
            <span className="w-11 h-11 rounded-xl bg-yellow-400/15 ring-1 ring-yellow-400/30 flex items-center justify-center shrink-0">
              <Trophy size={20} className="text-yellow-400" />
            </span>
            <div className="min-w-0">
              <p className="font-bold truncate">{l.name}</p>
              <p className="text-xs text-white/40">{l.country}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
