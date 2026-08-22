import { NavLink, Link, useNavigate } from 'react-router-dom'
import { LayoutDashboard, MonitorPlay, Clapperboard, Trophy, Star, Mail, Radio, LogOut, LogIn, ShieldCheck } from 'lucide-react'
import ballLogo from '../assets/Soccer.avif'
import { useAuth } from '../context/AuthContext'

const CONTACT_EMAIL = 'yimkeducationalconsultant@gmail.com'

const NAV = [
  { to: '/',         label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/live',     label: 'Live',      icon: MonitorPlay },
  { to: '/replay',   label: 'Replay',    icon: Clapperboard },
  { to: '/leagues',  label: 'Leagues',   icon: Trophy },
  { to: '/featured', label: 'Featured',  icon: Star },
]

function itemClass({ isActive }) {
  return (
    'flex items-center gap-4 px-4 py-4 rounded-xl text-[24px] font-bold transition-colors ' +
    (isActive
      ? 'bg-yellow-400/15 text-yellow-300 ring-1 ring-yellow-400/40'
      : 'text-white/70 hover:text-white hover:bg-white/5')
  )
}

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const handleLogout = () => { logout(); navigate('/') }

  return (
    <aside className="w-1/4 min-w-[330px] max-w-[460px] shrink-0 h-screen sticky top-0 bg-pitch-800 border-r border-white/5 flex flex-col px-6 py-7">
      {/* Logo */}
      <Link to="/" className="flex items-center gap-3 px-2 mb-9">
        <img src={ballLogo} alt="" className="w-14 h-14 rounded-full object-cover ring-2 ring-yellow-400/60" />
        <span className="font-extrabold text-[40px] leading-none tracking-tight">
          <span className="text-white">Goal</span><span className="text-yellow-400">Stream</span>
        </span>
      </Link>

      {/* Nav */}
      <nav className="flex flex-col gap-1.5">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={itemClass}>
            <Icon size={30} strokeWidth={2.2} />
            {label}
          </NavLink>
        ))}
        <a
          href={`mailto:${CONTACT_EMAIL}`}
          className="flex items-center gap-4 px-4 py-4 rounded-xl text-[24px] font-bold text-white/70 hover:text-white hover:bg-white/5 transition-colors"
        >
          <Mail size={30} strokeWidth={2.2} />
          Contact us
        </a>
      </nav>

      {/* Live shortcut card (replaces the template's "Upgrade Version") */}
      <Link
        to="/live"
        className="mt-auto rounded-2xl bg-gradient-to-br from-yellow-400/20 to-yellow-400/5 border border-yellow-400/30 p-5 text-center hover:border-yellow-400/60 transition-colors"
      >
        <div className="flex justify-center mb-2">
          <span className="flex items-center gap-1.5 text-yellow-300 text-[19px] font-bold">
            <Radio size={22} className="animate-pulse" /> LIVE
          </span>
        </div>
        <p className="text-[23px] font-bold text-white">Football live now</p>
        <p className="text-[16px] text-white/50 mt-1 mb-3">Jump straight into what's on</p>
        <span className="inline-block bg-yellow-400 text-pitch-900 text-[20px] font-bold px-5 py-2.5 rounded-lg">
          Watch Live →
        </span>
      </Link>

      {/* Account — signing in is optional, everything is watchable without it. */}
      <div className="mt-4 pt-4 border-t border-white/5">
        {user ? (
          <>
            {(user.is_admin || user.is_superuser) && (
              <Link
                to="/admin"
                className="flex items-center gap-3 px-2 py-2 mb-2 rounded-lg text-[20px] font-bold text-yellow-300/80 hover:text-yellow-300 hover:bg-white/5 transition-colors"
              >
                <ShieldCheck size={26} strokeWidth={2.2} /> Admin console
              </Link>
            )}
            <div className="flex items-center justify-between px-2">
              <span className="text-[22px] font-bold text-white/70 truncate">{user.username}</span>
              <button onClick={handleLogout} title="Log out" className="text-white/40 hover:text-yellow-300 transition-colors">
                <LogOut size={28} />
              </button>
            </div>
          </>
        ) : (
          <Link
            to="/login"
            className="flex items-center justify-center gap-3 w-full rounded-xl bg-yellow-400 text-pitch-900 text-[22px] font-bold px-4 py-3 hover:bg-yellow-300 transition-colors"
          >
            <LogIn size={26} strokeWidth={2.4} /> Sign In
          </Link>
        )}
      </div>
    </aside>
  )
}
