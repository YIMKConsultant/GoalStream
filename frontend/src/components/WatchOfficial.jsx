import { ExternalLink, Search } from 'lucide-react'

// Legal, licensed broadcasters. We deep-link out to the service the viewer
// is subscribed to — we never restream. Malaysia-first (your market), then
// global. The "Find your broadcaster" link is always region-accurate.
const PROVIDERS = [
  { name: 'sooka',    url: 'https://sooka.my/' },
  { name: 'Astro GO', url: 'https://astrogo.astro.com.my/' },
  { name: 'unifi TV', url: 'https://unifi.com.my/en/personal/broadband/unifi-tv' },
  { name: 'beIN',     url: 'https://www.beinsports.com/' },
  { name: 'ESPN+',    url: 'https://plus.espn.com/' },
  { name: 'DAZN',     url: 'https://www.dazn.com/' },
]

export default function WatchOfficial({ match }) {
  const home = match?.homeTeam?.name || ''
  const away = match?.awayTeam?.name || ''
  const findUrl =
    'https://www.google.com/search?q=' +
    encodeURIComponent(`where to watch ${home} vs ${away} live tv`)

  return (
    <div className="rounded-xl bg-yellow-400/5 ring-1 ring-yellow-400/20 p-4">
      <div className="flex items-center justify-between gap-3 mb-3">
        <h4 className="text-sm font-bold text-yellow-300">Watch on official broadcaster</h4>
        <a
          href={findUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs font-semibold text-yellow-400 hover:underline shrink-0"
        >
          <Search size={13} /> Find your broadcaster
        </a>
      </div>
      <div className="flex flex-wrap gap-2">
        {PROVIDERS.map((p) => (
          <a
            key={p.name}
            href={p.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-white/10 text-white/80 hover:border-yellow-400 hover:text-yellow-300 transition-colors"
          >
            {p.name} <ExternalLink size={13} className="opacity-60" />
          </a>
        ))}
      </div>
      <p className="text-[11px] text-white/30 mt-2">
        Opens the licensed provider — sign in with your subscription to watch live.
      </p>
    </div>
  )
}
