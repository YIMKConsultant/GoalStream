import { Routes, Route, Outlet } from 'react-router-dom'
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
import Register from './pages/Register'

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
      <Route path="/login"    element={<Login />} />
      <Route path="/register" element={<Register />} />
    </Routes>
  )
}
