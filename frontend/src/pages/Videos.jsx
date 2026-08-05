import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import VideoEmbed from '../components/VideoEmbed'

export default function Videos() {
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [competition, setCompetition] = useState('')
  const [active, setActive] = useState(null)

  useEffect(() => {
    setLoading(true)
    const q = competition ? `?competition=${encodeURIComponent(competition)}` : ''
    api.get(`/video/feed${q}`)
      .then((data) => { setVideos(data); setActive(data[0] ?? null) })
      .catch(() => setError('Could not load match videos.'))
      .finally(() => setLoading(false))
  }, [competition])

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="mb-6">
        <Link to="/live" className="text-white/40 text-sm hover:text-green-400">← Live football</Link>
        <h1 className="text-3xl font-extrabold mt-1 mb-1">Match <span className="text-green-400">Videos</span></h1>
        <p className="text-white/40 text-sm">
          Highlights &amp; match videos from the free Scorebat feed — a rolling window of recent games across many leagues.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        {['', 'Champions League', 'Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1'].map((c) => (
          <button
            key={c || 'all'}
            onClick={() => setCompetition(c)}
            className={`text-sm px-3 py-1.5 rounded-lg border transition-colors ${
              competition === c
                ? 'border-green-500 text-green-400'
                : 'border-white/10 text-white/60 hover:border-white/30'
            }`}
          >
            {c || 'All'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-white/30 text-center py-16">Loading videos…</div>
      ) : error ? (
        <div className="text-red-400 text-center py-16">{error}</div>
      ) : videos.length === 0 ? (
        <p className="text-white/30 text-sm">No videos for this competition right now.</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Player */}
          <div className="lg:col-span-2">
            {active && (
              <div>
                <VideoEmbed video={active} className="rounded-xl overflow-hidden" />
                <h2 className="text-lg font-bold mt-3">{active.title}</h2>
                <p className="text-white/40 text-xs">{active.competition}</p>
              </div>
            )}
          </div>

          {/* Playlist */}
          <div className="flex flex-col gap-2 max-h-[70vh] overflow-y-auto pr-1">
            {videos.map((v) => (
              <button
                key={v.matchview_url ?? v.title}
                onClick={() => setActive(v)}
                className={`card text-left p-3 flex gap-3 items-center transition-colors ${
                  active?.matchview_url === v.matchview_url ? 'border-green-500' : 'hover:border-white/20'
                }`}
              >
                {v.thumbnail && (
                  <img src={v.thumbnail} alt="" className="w-20 h-12 object-cover rounded shrink-0" />
                )}
                <div className="min-w-0">
                  <p className="text-sm font-semibold truncate">{v.title}</p>
                  <p className="text-white/40 text-xs truncate">{v.competition}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
