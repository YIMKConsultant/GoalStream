import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { useLiveScores } from '../hooks/useLiveScores'
import MatchCard from '../components/MatchCard'

function Section({ title, badge, children }) {
  return (
    <section className="mb-10">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-xl font-bold">{title}</h2>
        {badge}
      </div>
      {children}
    </section>
  )
}

function Grid({ matches, empty }) {
  if (!matches.length) return <p className="text-white/30 text-sm">{empty}</p>
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {matches.map((m) => <MatchCard key={m.id} match={m} />)}
    </div>
  )
}

export default function Home() {
  const liveMatches = useLiveScores()
  const [todayMatches, setTodayMatches] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/leagues/today')
      .then(setTodayMatches)
      .finally(() => setLoading(false))
  }, [])

  const upcoming = todayMatches.filter((m) => m.status === 'SCHEDULED')
  const finished  = todayMatches.filter((m) => m.status === 'FINISHED')

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Hero */}
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-extrabold mb-2">
          Watch <span className="text-green-400">Football</span> Live
        </h1>
        <p className="text-white/40">Premier League · Champions League · Europa League & more</p>
      </div>

      {/* Live */}
      <Section
        title="Live Now"
        badge={
          liveMatches.length > 0 && (
            <span className="flex items-center gap-1 text-xs bg-red-600/20 text-red-400 px-2 py-0.5 rounded-full">
              <span className="live-dot" /> {liveMatches.length} live
            </span>
          )
        }
      >
        {liveMatches.length === 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <Link
              to="/live"
              className="card block p-4 hover:scale-[1.01] transition-transform"
            >
              <div className="flex items-center justify-between mb-3 text-xs text-white/40">
                <span>Live TV</span>
                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-white text-[10px] font-bold bg-red-600 animate-pulse">
                  LIVE
                </span>
              </div>
              <div className="flex flex-col items-center gap-2 py-4">
                <span className="text-4xl">📺</span>
                <span className="text-lg font-bold text-green-400">Live Sports Channels</span>
                <span className="text-sm text-white/40">Browse live channels to watch</span>
              </div>
            </Link>
          </div>
        ) : (
          <Grid matches={liveMatches} empty="" />
        )}
      </Section>

      {loading ? (
        <div className="text-white/30 text-center py-12">Loading today's matches…</div>
      ) : (
        <>
          <Section title="Upcoming Today">
            <Grid matches={upcoming} empty="No upcoming matches today." />
          </Section>
          <Section title="Finished Today">
            <Grid matches={finished} empty="No finished matches today." />
          </Section>
        </>
      )}
    </div>
  )
}
