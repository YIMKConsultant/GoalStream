import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useState } from 'react'
import ballLogo from '../assets/Soccer.avif'

const LEAGUES = [
  { code: 'PL',  name: 'Premier League' },
  { code: 'CL',  name: 'Champions League' },
  { code: 'EL',  name: 'Europa League' },
  { code: 'ECL', name: 'Conference League' },
  { code: 'PD',  name: 'La Liga' },
  { code: 'BL1', name: 'Bundesliga' },
  { code: 'SA',  name: 'Serie A' },
  { code: 'FL1', name: 'Ligue 1' },
  { code: 'SPL', name: 'Saudi Pro League' },
  { code: 'MLS', name: 'Major League Soccer' },
  { code: 'CAFP', name: 'CAF Premier League' },
  { code: 'CAFW', name: "CAF Women's CL" },
  { code: 'WC',  name: 'World Cup' },
  { code: 'WWC', name: "FIFA Women's World Cup" },
]

const CONTACT_EMAIL = 'yimkeducationalconsultant@gmail.com'

// Shared "yellow-edged button" look for the centre nav.
const navBtn = (active) =>
  `rounded-lg px-5 py-2 text-sm font-semibold border transition-all duration-150 ` +
  `bg-gradient-to-r from-yellow-400/15 via-transparent to-yellow-400/15 ` +
  (active
    ? 'text-yellow-300 border-yellow-400 shadow-[0_0_14px_rgba(250,204,21,0.35)]'
    : 'text-white/80 border-yellow-400/40 hover:text-yellow-300 hover:border-yellow-400 hover:shadow-[0_0_14px_rgba(250,204,21,0.30)]')

// Football logo mark (Soccer.avif).
function BallLogo() {
  return (
    <img
      src={ballLogo}
      alt="GoalStream"
      width="40"
      height="40"
      className="shrink-0 w-10 h-10 rounded-full object-cover ring-2 ring-yellow-400/60"
    />
  )
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)

  const handleLogout = () => { logout(); navigate('/') }
  const path = location.pathname

  return (
    <nav className="sticky top-0 z-50 bg-pitch-800/95 backdrop-blur border-b border-yellow-400/20">
      <div className="relative max-w-7xl mx-auto px-8 pt-3 h-20 flex items-center">
        {/* Logo + title — top-left with margin */}
        <Link to="/" className="flex items-center gap-3 ml-2 shrink-0">
          <BallLogo />
          <span className="font-extrabold text-xl tracking-tight">
            <span className="text-white">Goal</span>
            <span className="text-yellow-400">Stream</span>
          </span>
        </Link>

        {/* Centre nav — Live · Matches · Leagues */}
        <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-3">
          <Link to="/live" className={navBtn(path === '/live')}>Live</Link>
          <Link to="/" className={navBtn(path === '/')}>Matches</Link>

          <div
            className="relative"
            onMouseEnter={() => setOpen(true)}
            onMouseLeave={() => setOpen(false)}
          >
            <button className={`${navBtn(path.startsWith('/league'))} flex items-center gap-1.5`}>
              Leagues
              <svg width="10" height="10" viewBox="0 0 12 12" className={`transition-transform ${open ? 'rotate-180' : ''}`}>
                <path d="M2 4 L6 8 L10 4" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            {open && (
              // pt-2 keeps an invisible bridge so moving the cursor from the
              // button to the menu doesn't cross a gap and trigger mouse-leave.
              <div className="absolute top-full left-1/2 -translate-x-1/2 pt-2 z-50">
                <div className="bg-pitch-800 border border-yellow-400/20 rounded-xl shadow-2xl w-52 py-2">
                  {LEAGUES.map((l) => (
                    <Link
                      key={l.code}
                      to={`/league/${l.code}`}
                      onClick={() => setOpen(false)}
                      className="block px-4 py-2 text-sm text-white/70 hover:bg-yellow-400/10 hover:text-yellow-300 transition-colors"
                    >
                      {l.name}
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right corner — auth + Contact us */}
        <div className="ml-auto flex items-center gap-3">
          {user ? (
            <>
              <span className="text-sm text-white/50 hidden md:block">{user.username}</span>
              <button
                onClick={handleLogout}
                className="text-sm py-1.5 px-4 rounded-lg border border-white/15 text-white/70 hover:border-yellow-400 hover:text-yellow-300 transition-colors"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm py-1.5 px-4 rounded-lg border border-white/15 text-white/70 hover:border-yellow-400 hover:text-yellow-300 transition-colors">
                Sign In
              </Link>
              <Link to="/signup" className="text-sm py-1.5 px-4 rounded-lg bg-yellow-400 text-pitch-900 font-semibold hover:bg-yellow-300 transition-colors">
                Sign Up
              </Link>
            </>
          )}
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="text-sm py-1.5 px-4 rounded-lg bg-yellow-400 text-pitch-900 font-bold hover:bg-yellow-300 shadow-[0_0_14px_rgba(250,204,21,0.30)] transition-colors"
          >
            Contact us
          </a>
        </div>
      </div>
    </nav>
  )
}
