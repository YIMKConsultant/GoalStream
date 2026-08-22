import { NavLink, Navigate, Outlet, Link } from 'react-router-dom'
import { LayoutDashboard, Users, Tv, Settings, ArrowLeft, ShieldCheck, Sparkles } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

const TABS = [
  { to: '/admin',          label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/admin/users',    label: 'Users',    icon: Users },
  { to: '/admin/channels', label: 'Channels', icon: Tv },
  { to: '/admin/ai',       label: 'AI',       icon: Sparkles, superuser: true },
  { to: '/admin/settings', label: 'Settings', icon: Settings, superuser: true },
]

function tabClass({ isActive }) {
  return (
    'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ' +
    (isActive
      ? 'bg-yellow-400/15 text-yellow-300 ring-1 ring-yellow-400/40'
      : 'text-white/60 hover:text-white hover:bg-white/5')
  )
}

export default function AdminLayout() {
  const { user } = useAuth()

  // Server-side checks are the real gate (every /api/admin route requires it);
  // this just keeps the UI out of the way for everyone else.
  if (!user) return <Navigate to="/login" replace />
  if (!user.is_admin && !user.is_superuser) return <Navigate to="/" replace />

  return (
    <div className="min-h-screen bg-pitch-900">
      <header className="border-b border-white/10 bg-pitch-800/80 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4 mb-4">
            <Link to="/" className="text-white/40 hover:text-yellow-300 transition-colors" title="Back to site">
              <ArrowLeft size={22} />
            </Link>
            <h1 className="text-2xl font-extrabold">
              Admin <span className="text-yellow-400">Console</span>
            </h1>
            <span className="flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-full bg-yellow-400/15 text-yellow-300 ring-1 ring-yellow-400/30">
              <ShieldCheck size={14} />
              {user.is_superuser ? 'Superuser' : 'Admin'}
            </span>
            <span className="ml-auto text-sm text-white/50">{user.username}</span>
          </div>

          <nav className="flex flex-wrap gap-2">
            {TABS.filter((t) => !t.superuser || user.is_superuser).map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={tabClass}>
                <Icon size={16} /> {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
