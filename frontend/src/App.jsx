import { Routes, Route, Outlet, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import League from './pages/League'
import Match from './pages/Match'
import Live from './pages/Live'
import Channels from './pages/Channels'
import Replays from './pages/Replays'
import Videos from './pages/Videos'
import Leagues from './pages/Leagues'
import Featured from './pages/Featured'
import Login from './pages/Login'
import Signup from './pages/Signup'
import AdminLayout from './pages/admin/AdminLayout'
import AdminOverview from './pages/admin/AdminOverview'
import AdminUsers from './pages/admin/AdminUsers'
import AdminChannels from './pages/admin/AdminChannels'
import AdminSettings from './pages/admin/AdminSettings'
import AdminAI from './pages/admin/AdminAI'

// App shell — sidebar + scrollable content area.
function Shell() {
  return (
    <div className="flex min-h-screen bg-pitch-900">
      <Sidebar />
      <main className="flex-1 min-w-0">
        <Outlet />
      </main>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route path="/"              element={<Dashboard />} />
        <Route path="/live"          element={<Live />} />
        <Route path="/replay"        element={<Replays />} />
        <Route path="/leagues"       element={<Leagues />} />
        <Route path="/featured"      element={<Featured />} />
        <Route path="/live/channels" element={<Channels />} />
        <Route path="/live/replays"  element={<Replays />} />
        <Route path="/live/videos"   element={<Videos />} />
        <Route path="/league/:code"  element={<League />} />
        <Route path="/match/:id"     element={<Match />} />
      </Route>
      {/* Admin console — its own shell, gated in AdminLayout. */}
      <Route path="/admin" element={<AdminLayout />}>
        <Route index             element={<AdminOverview />} />
        <Route path="users"      element={<AdminUsers />} />
        <Route path="channels"   element={<AdminChannels />} />
        <Route path="ai"         element={<AdminAI />} />
        <Route path="settings"   element={<AdminSettings />} />
      </Route>

      {/* Every route above is open — an account is only needed for favourites. */}
      <Route path="/login"    element={<Login />} />
      <Route path="/signup"   element={<Signup />} />
      <Route path="/register" element={<Navigate to="/signup" replace />} />
    </Routes>
  )
}
