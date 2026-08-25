# GoalStream

Live football scores, fixtures, highlights and free-to-air sports channels.

A FastAPI backend joins football-data.org (fixtures, scores, standings), Scorebat
(highlight videos) and the iptv-org catalog (free TV channels), and serves them to
a React + Vite frontend. Streams are relayed through a server-side proxy so the
browser never hits CORS or an expired upstream ticket.

**GoalStream only relays streams served by the broadcaster or a licensed
platform.** Roughly 55% of the iptv-org sports catalog turns out to be
unauthorized restreams of paid channels — bare IPs and rented VPSs serving Sky,
Fox and Ziggo. Those are classified and blocked at the proxy; see
[Stream policy](#stream-policy).

---

## Requirements

| | Version | Notes |
|---|---|---|
| Python | 3.11+ | Developed on 3.13 |
| Node.js | 18+ | For Vite 5 |
| A football-data.org API key | free tier | [Sign up](https://www.football-data.org/) — without it, fixtures and scores are empty |

---

## Quick start

You need **two terminals** — one for the backend, one for the frontend.

### Terminal 1 — backend (port 8000)

```bash
cd backend

# First run only: create and populate the virtualenv.
python -m venv ../.venv
../.venv/Scripts/activate        # Windows
# source ../.venv/bin/activate   # macOS / Linux
pip install -r requirements.txt

# First run only: create your config, then edit it (see Configuration below).
copy .env.example .env           # Windows PowerShell / cmd
# cp .env.example .env           # Git Bash / macOS / Linux

python -m uvicorn main:app --reload
```

Backend is up when you see `Uvicorn running on http://127.0.0.1:8000`.
Interactive API docs: <http://localhost:8000/docs>

### Terminal 2 — frontend (port 3000)

```bash
cd frontend
npm install                      # first run only
npm run dev
```

```
VITE v5.4.x  ready in 400 ms
➜  Local:   http://localhost:3000/
```

Open <http://localhost:3000>.

> The frontend proxies `/api` and `/ws` to `localhost:8000` (see
> `vite.config.js`), so **the backend must be running or every page will be
> empty**. There is no separate frontend API URL to configure.

### Create an admin account

With the backend's virtualenv active:

```bash
cd backend
python seed_admin.py                          # admin / ChangeMe123!
python seed_admin.py alice alice@x.com secret # or a named account
```

Safe to re-run — an existing username is promoted rather than duplicated.
**Change the password immediately after first login.** Then sign in and visit
<http://localhost:3000/admin>.

---

## Configuration

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Required | What it does |
|---|---|---|
| `FOOTBALL_API_KEY` | **yes** | football-data.org key. Without it there are no fixtures, scores or standings. |
| `SECRET_KEY` | **yes in production** | Signs JWTs. Change from the default. |
| `SCOREBAT_TOKEN` | no | [Free token](https://www.scorebat.com/video-api/) for the highlights feed. Without it the feed falls back to a frozen sample whose embeds often show "video unavailable". |
| `PROXY_SIGNING_KEY` | no | Signs stream URLs so the proxy can't fetch arbitrary URLs. Falls back to `SECRET_KEY`. |
| `DATABASE_URL` | no | Defaults to SQLite at `backend/football_watch.db`. Created automatically on first run. |
| `CORS_ORIGINS` | no | Comma-separated. Only matters if you serve the frontend from another origin. |

The Anthropic API key for AI channel discovery is **not** set here — an admin
enters it at `/admin/ai`, so it can be rotated without a restart.

---

## Pages

| Route | What it is |
|---|---|
| `/` | Dashboard — scores, highlights, and **Live now** (in-play matches with playable channels) |
| `/live` | Live Now — live and upcoming fixtures, plus free sports channels on air |
| `/live/channels` | The full free channel catalog |
| `/live/replays` | Channels airing classic matches |
| `/live/videos` | Highlight reels |
| `/leagues`, `/league/:code` | Competitions, fixtures and standings |
| `/match/:id` | One match |
| `/admin` | Users, channel policy, AI discovery, settings (admin only) |

---

## Stream policy

Every stream URL is classified by **origin** before it can be played
(`backend/services/stream_origin.py`), on a default-deny basis:

| Class | Meaning | Playable |
|---|---|---|
| `official` | Broadcaster-owned host or licensed FAST/CDN platform | yes |
| `restream` | Bare IP, non-standard port, throwaway TLD, URL shortener | no |
| `unverified` | Anything unrecognised — a review queue, not a verdict | no |

Enforcement lives in `routers/proxy.py`, the only endpoint that moves video, so
filtering a listing alone cannot be bypassed by guessing a channel id.

A channel is only offered **under a specific fixture** when it actually holds
rights to that competition. In practice the free catalog holds no rights holder
for most leagues, so those fixtures show the official broadcaster instead
(`components/WatchOfficial.jsx`, configured in `config.OFFICIAL_WATCH`).

The exception is **RTM** (Malaysia's public broadcaster, `services/rtm.py`) —
free, licensed, and the carrier for all 104 FIFA World Cup 2026 matches.

---

## Project layout

```
backend/
  main.py               FastAPI app and router wiring
  config.py             Settings, LEAGUES, OFFICIAL_WATCH
  models.py             SQLAlchemy models
  routers/              auth, leagues, matches, iptv, proxy, video, admin, …
  services/
    football_api.py     football-data.org client
    iptv_org.py         Free channel catalog, liveness, league mapping
    rtm.py              RTM free-to-air channels
    stream_origin.py    Origin classification (the stream policy above)
    ai_discovery.py     Claude-assisted league → channel mapping
  seed_admin.py         Create/promote the superuser
frontend/
  src/pages/            Dashboard, Live, Leagues, Match, admin/…
  src/components/       LiveNow, WatchOfficial, StreamPlayer, …
  src/lib/              Shared helpers (see Known issues)
```

---

## Known issues

**`frontend/src/lib/` is gitignored.** Line 17 of `.gitignore` is a bare `lib/`
rule, which matches it:

```
$ git check-ignore -v frontend/src/lib/channelMatch.js
.gitignore:17:lib/    frontend/src/lib/channelMatch.js
```

`channelMatch.js`, `matchStatus.js` and `lastWatched.js` have therefore never
been committed, and **a fresh clone will not build** — Vite fails on the missing
imports. Fix by narrowing the rule:

```diff
-lib/
+/lib/
```

then `git add -f frontend/src/lib/`.

**`Password.txt` is committed to the repository.** If it holds anything more
than local run notes, rotate those credentials and remove the file from history.

**`services/stream_scraper.py` does not work.** RTM Klik is a Next.js SPA whose
HTML contains no `.m3u8` URLs, so the regex scraper returns `None` for every
page and `/api/proxy/extract` is dead. RTM playback goes through
`services/rtm.py` instead.

**Channel liveness is volatile.** Free streams drop in and out constantly; the
same league can return a different number of live channels minutes apart. Probe
results are cached for 2 minutes.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| Every page empty, console shows `/api/...` failing | Backend isn't running on port 8000 |
| No fixtures or scores anywhere | `FOOTBALL_API_KEY` missing or invalid in `backend/.env` |
| Fixtures load but a competition 404s | football-data.org's free tier doesn't carry it; `EL` and `ECL` are marked `fixtures: True` but aren't on the free plan |
| Highlights show "video unavailable" | `SCOREBAT_TOKEN` not set — the fallback feed is stale |
| A match shows no channels, only broadcaster links | Working as intended — no free rights holder for that competition |
| Vite fails on missing `../lib/...` imports | The gitignore issue above |
| `npm run dev` port conflict | Change `server.port` in `frontend/vite.config.js` |
