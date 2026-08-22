import { useEffect, useRef, useState, useCallback } from 'react'
import Hls from 'hls.js'
import api from '../api/client'

export function HlsPlayer({ src }) {
  const videoRef = useRef(null)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    setError('')
    const video = videoRef.current
    if (!video) return
    const cleanup = []

    if (Hls.isSupported()) {
      const hls = new Hls({
        // Generous timeouts + retries: proxied LIVE playlists add latency, and
        // free restreams stall briefly. Give them room before failing.
        manifestLoadingTimeOut: 20000,
        manifestLoadingMaxRetry: 4,
        manifestLoadingRetryDelay: 1000,
        levelLoadingTimeOut: 20000,
        levelLoadingMaxRetry: 6,
        levelLoadingRetryDelay: 1000,
        fragLoadingTimeOut: 30000,
        fragLoadingMaxRetry: 6,
        fragLoadingRetryDelay: 1000,
        liveSyncDurationCount: 3,
        xhrSetup: (xhr) => {
          xhr.setRequestHeader('Origin', window.location.origin)
        },
      })

      // Recovering the stream is only half the job — the <video> element stays
      // paused after a stall, so every recovery path must also resume playback
      // or the picture freezes with no error shown.
      //
      // But a deliberate pause must stick. A `pause` event means the viewer hit
      // pause: a buffer stall fires `waiting` and leaves paused === false. So
      // `pause` is the signal to stop auto-resuming until they press play again.
      let userPaused = false
      const resume = () => { if (!userPaused) video.play().catch(() => {}) }

      let netRecover = 0
      let mediaRecover = 0
      hls.on(Hls.Events.ERROR, (_, data) => {
        // Non-fatal buffer stalls are the common case on flaky free restreams:
        // hls.js keeps the session but the element has already paused.
        if (!data.fatal) {
          if (data.details === Hls.ErrorDetails.BUFFER_STALLED_ERROR) {
            try { hls.startLoad() } catch {}
            resume()
          }
          return
        }
        if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
          if (netRecover++ < 5) {
            setTimeout(() => { try { hls.startLoad(); resume() } catch {} }, 1500)
          } else {
            setError(`Stream error: ${data.type} — ${data.details}`)
          }
        } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
          if (mediaRecover++ < 3) {
            try { hls.recoverMediaError(); resume() } catch {}
          } else {
            setError(`Stream error: ${data.type} — ${data.details}`)
          }
        } else {
          setError(`Stream error: ${data.type} — ${data.details}`)
        }
      })

      const onPause = () => { userPaused = true }
      const onPlay = () => {
        userPaused = false
        // A live stream drifts out of the playlist window while paused — the
        // server drops those segments, so resuming where we left off stalls.
        // Jump to the live edge, but only after a real gap, so a quick
        // pause/play doesn't skip the viewer forward for no reason.
        try {
          const edge = hls.liveSyncPosition
          if (edge == null || edge - video.currentTime <= 30) return
          const seekable = video.seekable
          if (seekable.length && edge <= seekable.end(seekable.length - 1)) {
            video.currentTime = edge
          }
        } catch {}
      }
      video.addEventListener('pause', onPause)
      video.addEventListener('play', onPlay)
      cleanup.push(() => {
        video.removeEventListener('pause', onPause)
        video.removeEventListener('play', onPlay)
      })
      // A clean fragment load resets the recovery counters, so a stream that
      // hiccups every few minutes keeps healing instead of exhausting retries.
      hls.on(Hls.Events.FRAG_BUFFERED, () => { netRecover = 0; mediaRecover = 0 })

      hls.loadSource(src)
      hls.attachMedia(video)
      hls.on(Hls.Events.MANIFEST_PARSED, () => video.play().catch(() => {}))
      return () => { cleanup.forEach((fn) => fn()); hls.destroy() }
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = src
      video.play().catch(() => {})
    } else {
      setError('Your browser does not support HLS video.')
    }
  }, [src, reloadKey])

  if (error) return (
    <div className="w-full h-full rounded-xl flex flex-col items-center justify-center bg-pitch-900 border border-red-800 gap-3 p-6">
      <span className="text-3xl">⚠️</span>
      <p className="text-red-400 text-sm text-center">{error}</p>
      <p className="text-white/30 text-xs text-center">Stream error — the URL may have expired.</p>
      <div className="flex gap-3">
        <button onClick={() => { setError(''); setReloadKey((k) => k + 1); }} className="btn-primary text-sm px-4 py-2">
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
