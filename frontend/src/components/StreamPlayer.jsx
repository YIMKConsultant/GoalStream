import { useEffect, useRef, useState, useCallback } from 'react'
import Hls from 'hls.js'
import api from '../api/client'

function HlsPlayer({ src }) {
  const videoRef = useRef(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setError('')
    const video = videoRef.current
    if (!video) return

    if (Hls.isSupported()) {
      const hls = new Hls({
        xhrSetup: (xhr) => {
          xhr.setRequestHeader('Origin', window.location.origin)
        }
      })
      hls.loadSource(src)
      hls.attachMedia(video)
      hls.on(Hls.Events.MANIFEST_PARSED, () => video.play().catch(() => {}))
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) setError(`Stream error: ${data.type} — ${data.details}`)
      })
      return () => hls.destroy()
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = src
      video.play().catch(() => {})
    } else {
      setError('Your browser does not support HLS video.')
    }
  }, [src])

  if (error) return (
    <div className="w-full h-full rounded-xl flex flex-col items-center justify-center bg-pitch-900 border border-red-800 gap-3 p-6">
      <span className="text-3xl">⚠️</span>
      <p className="text-red-400 text-sm text-center">{error}</p>
      <p className="text-white/30 text-xs text-center">Stream error — the URL may have expired.</p>
      <div className="flex gap-3">
        <button onClick={() => { setError(''); }} className="btn-primary text-sm px-4 py-2">
          ↺ Retry
        </button>
        <a href={src} target="_blank" rel="noopener noreferrer" className="btn-ghost text-sm px-4 py-2">
          ↗ Open directly
        </a>
      </div>
    </div>
  )

  return (
    <video
      ref={videoRef}
      controls
      className="w-full h-full rounded-xl bg-black"
      playsInline
    />
  )
}

function EmbedPlayer({ src }) {
  const [blocked, setBlocked] = useState(false)

  return blocked ? (
    <div className="w-full h-full rounded-xl flex flex-col items-center justify-center bg-pitch-900 border border-white/10 gap-4">
      <span className="text-4xl">📺</span>
      <p className="text-white/50 text-sm text-center px-4">
        This broadcaster blocks embedding.<br />Click below to watch in a new tab.
      </p>
      <a
        href={src}
        target="_blank"
        rel="noopener noreferrer"
        className="btn-primary px-6 py-2"
      >
        ▶ Watch Live Stream
      </a>
    </div>
  ) : (
    <iframe
      src={src}
      className="w-full h-full rounded-xl"
      allowFullScreen
      allow="autoplay; encrypted-media"
      onError={() => setBlocked(true)}
      onLoad={(e) => {
        try {
          // If blocked by X-Frame-Options the contentDocument will be null
          if (!e.target.contentDocument) setBlocked(true)
        } catch {
          setBlocked(true)
        }
      }}
    />
  )
}

function YouTubePlayer({ src }) {
  // Convert watch URL to embed URL if needed
  const embedUrl = src.includes('watch?v=')
    ? src.replace('watch?v=', 'embed/')
    : src
  return <EmbedPlayer src={embedUrl} />
}

function AutoPlayer({ pageUrl }) {
  const [src, setSrc] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.get(`/proxy/extract?page_url=${encodeURIComponent(pageUrl)}`)
      .then((data) => setSrc(data.proxied_url))
      .catch(() => setErr('Could not extract stream from broadcaster page.'))
  }, [pageUrl])

  if (err) return <div className="w-full h-full flex items-center justify-center text-red-400 text-sm">{err}</div>
  if (!src) return <div className="w-full h-full flex items-center justify-center text-white/30 text-sm">Extracting live stream…</div>
  return <HlsPlayer src={src} />
}

export default function StreamPlayer({ streams }) {
  const [selected, setSelected] = useState(0)

  if (!streams || streams.length === 0) {
    return (
      <div className="aspect-video bg-pitch-800 rounded-xl flex flex-col items-center justify-center text-white/30 border border-white/5">
        <span className="text-5xl mb-3">📺</span>
        <p className="text-lg">No stream available yet</p>
        <p className="text-sm mt-1">Check back when the match starts</p>
      </div>
    )
  }

  const stream = streams[selected]

  return (
    <div>
      {/* Player */}
      <div className="aspect-video bg-black rounded-xl overflow-hidden">
        {stream.stream_type === 'm3u8' && <HlsPlayer src={stream.stream_url} />}
        {stream.stream_type === 'auto' && <AutoPlayer pageUrl={stream.stream_url} />}
        {stream.stream_type === 'youtube' && <YouTubePlayer src={stream.stream_url} />}
        {stream.stream_type === 'embed' && <EmbedPlayer src={stream.stream_url} />}
      </div>

      {/* Stream selector + direct open button */}
      <div className="flex flex-wrap items-center gap-2 mt-3">
        {streams.length > 1 && streams.map((s, i) => (
          <button
            key={s.id}
            onClick={() => setSelected(i)}
            className={`text-sm px-4 py-1.5 rounded-lg border transition-colors ${
              i === selected
                ? 'border-green-500 bg-green-600/20 text-green-400'
                : 'border-white/10 text-white/50 hover:border-white/30'
            }`}
          >
            {s.label} · {s.language}
          </button>
        ))}
        <a
          href={stream.stream_url}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto text-sm px-4 py-1.5 rounded-lg border border-green-600 text-green-400 hover:bg-green-600/20 transition-colors"
        >
          ↗ Open in new tab
        </a>
      </div>
    </div>
  )
}
