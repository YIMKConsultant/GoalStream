// Renders a Scorebat player in a responsive 16:9 frame.
// Prefers the extracted player src (clean React <iframe>); falls back to the
// match-view URL, then to the raw embed HTML if that's all we have.
export default function VideoEmbed({ video, className = '' }) {
  if (!video) return null
  const src = video.embed_url || video.matchview_url

  return (
    <div className={`relative w-full bg-black ${className}`} style={{ aspectRatio: '16 / 9' }}>
      {src ? (
        <iframe
          key={src}
          src={src}
          title={video.title || 'Match video'}
          frameBorder="0"
          allow="autoplay; fullscreen; encrypted-media; picture-in-picture"
          allowFullScreen
          className="absolute inset-0 w-full h-full"
        />
      ) : video.embed ? (
        <div className="absolute inset-0" dangerouslySetInnerHTML={{ __html: video.embed }} />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center text-white/40 text-sm">
          Video unavailable
        </div>
      )}
    </div>
  )
}
