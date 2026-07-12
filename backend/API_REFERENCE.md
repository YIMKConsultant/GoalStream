# Football Watch — API Reference

Base URL: `http://localhost:8000`

---

## Auth

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | `{username, email, password}` | Register & get JWT |
| POST | `/api/auth/login` | `{username, password}` | Login & get JWT |
| GET  | `/api/auth/me` | — (Bearer token) | Current user info |

---

## Leagues

| Method | Endpoint | Params | Description |
|--------|----------|--------|-------------|
| GET | `/api/leagues` | — | List all supported leagues |
| GET | `/api/leagues/live` | — | Live / in-play matches (all leagues) |
| GET | `/api/leagues/today` | — | Today's matches (all leagues) |
| GET | `/api/leagues/teams/search` | `?q=Arsenal` | Search teams by name |
| GET | `/api/leagues/{code}/matches` | `?matchday=12` | Matches for a league |
| GET | `/api/leagues/{code}/standings` | — | League table / standings |

**League codes:** `PL` Premier League · `CL` Champions League · `EL` Europa League · `ECL` Conference League · `PD` La Liga · `BL1` Bundesliga · `SA` Serie A · `FL1` Ligue 1 · `DED` Eredivisie · `PPL` Primeira Liga · `WC` World Cup

---

## Matches

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/matches/{id}` | Match detail + stream availability |
| GET | `/api/matches/{id}/streams` | Available stream links for a match |
| GET | `/api/matches/team/{team_id}` | Team's matches (`?status=SCHEDULED`) |

---

## Streams  *(admin token required for write operations)*

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/api/streams` | `{match_id, league_code, label, stream_url, stream_type, language}` | Add stream (admin) |
| GET  | `/api/streams/match/{match_id}` | — | Active streams for a match |
| PUT  | `/api/streams/{id}` | same as POST body | Update stream (admin) |
| DELETE | `/api/streams/{id}` | — | Deactivate stream (admin) |

**stream_type values:** `m3u8` · `embed` · `youtube`

---

## Favorites  *(requires Bearer token)*

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| GET    | `/api/favorites` | — | User's favorite teams |
| POST   | `/api/favorites` | `{team_id, team_name}` | Add favorite team |
| DELETE | `/api/favorites/{team_id}` | — | Remove favorite team |

---

## WebSocket

Connect to `ws://localhost:8000/ws/live`

- Server pushes `{"event": "live_scores", "data": [...matches]}` every 30 seconds.
- Send `"ping"` → receive `{"event": "pong"}`.

---

## Interactive Docs

Visit `http://localhost:8000/docs` for Swagger UI.
