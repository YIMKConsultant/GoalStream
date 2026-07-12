import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useState } from 'react'

const LEAGUES = [
  { code: 'PL',  name: 'Premier League' },
  { code: 'CL',  name: 'Champions League' },
  { code: 'EL',  name: 'Europa League' },
  { code: 'ECL', name: 'Conference League' },
  { code: 'PD',  name: 'La Liga' },
  { code: 'BL1', name: 'Bundesliga' },
  { code: 'SA',  name: 'Serie A' },
  { code: 'FL1', name: 'Ligue 1' },
  { code: 'WC',  name: 'World Cup' },
]

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)

  const handleLogout = () => { logout(); navigate('/') }

  return (
    <nav className="sticky top-0 z-50 bg-pitch-800/95 backdrop-blur border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 flex items-center gap-6 h-16">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 font-bold text-xl text-green-400 shrink-0">
          ⚽ GoalStream
        </Link>

        {/* League dropdown */}
        <div className="relative">
          <button
            onClick={() => setOpen(!open)}
            className="flex items-center gap-1 text-white/70 hover:text-white text-sm transition-colors"
          >
            Leagues <span className="text-xs">{open ? '▲' : '▼'}</span>
          </button>
          {open && (
            <div className="absolute top-8 left-0 bg-pitch-800 border border-white/10 rounded-xl shadow-2xl w-52 py-2 z-50">
              {LEAGUES.map((l) => (
                <Link
                  key={l.code}
                  to={`/league/${l.code}`}
                  onClick={() => setOpen(false)}
                  className="block px-4 py-2 text-sm text-white/70 hover:bg-white/5 hover:text-green-400 transition-colors"
                >
                  {l.name}
                </Link>
              ))}
            </div>
          )}
        </div>

        <Link to="/live" className={`text-sm transition-colors ${location.pathname === '/live' ? 'text-green-400' : 'text-white/70 hover:text-white'}`}>
          Live
        </Link>
        <Link to="/today" className={`text-sm transition-colors ${location.pathname === '/today' ? 'text-green-400' : 'text-white/70 hover:text-white'}`}>
          Today
        </Link>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Auth */}
        {user ? (
          <div className="flex items-center gap-3">
            <span className="text-sm text-white/50 hidden sm:block">{user.username}</span>
            <button onClick={handleLogout} className="btn-ghost text-sm py-1.5 px-4">
              Logout
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Link to="/login" className="btn-ghost text-sm py-1.5 px-4">Login</Link>
            <Link to="/register" className="btn-primary text-sm py-1.5 px-4">Sign Up</Link>
          </div>
        )}
      </div>
    </nav>
  )
}
