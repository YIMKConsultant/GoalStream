import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import League from './pages/League'
import Match from './pages/Match'
import Live from './pages/Live'
import Channels from './pages/Channels'
import Replays from './pages/Replays'
import Login from './pages/Login'
import Register from './pages/Register'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/"               element={<Home />} />
          <Route path="/live"           element={<Live />} />
          <Route path="/live/channels"  element={<Channels />} />
          <Route path="/live/replays"   element={<Replays />} />
          <Route path="/league/:code"   element={<League />} />
          <Route path="/match/:id"      element={<Match />} />
          <Route path="/login"          element={<Login />} />
          <Route path="/register"       element={<Register />} />
        </Routes>
      </main>
      <footer className="text-center text-white/20 text-xs py-6 border-t border-white/5">
        GoalStream © {new Date().getFullYear()} · Powered by football-data.org
      </footer>
    </div>
  )
}
