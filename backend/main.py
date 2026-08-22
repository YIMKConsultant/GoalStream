import asyncio
import contextlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from config import settings
from database import AsyncSessionLocal
from routers import (
    admin, auth, leagues, matches, streams, favorites, proxy, iptv, video,
    presence as presence_router,
)
from services import presence, settings_store
from services.iptv_org import get_playing_channels
from websocket import live_scores_ws


async def _warm_featured():
    """Keep the Featured (playing channels) cache warm so the page loads fast."""
    while True:
        with contextlib.suppress(Exception):
            await get_playing_channels()
        await asyncio.sleep(720)  # refresh before the 15-min cache expires


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Pull any superuser-set overrides (API key, default channel tier) into the
    # in-memory store before the first request lands.
    async with AsyncSessionLocal() as db:
        await settings_store.load(db)
    tasks: list[asyncio.Task] = [asyncio.create_task(_warm_featured())]
    if settings.presence_tracking:
        tasks.append(asyncio.create_task(
            presence.report_loop(settings.presence_report_seconds)
        ))
    yield
    for task in tasks:
        task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(
    title="GoalStream API",
    description="Backend for the GoalStream app — live scores, streams, standings.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def track_viewers(request: Request, call_next):
    """Stamp every request into the live viewer table (see services/presence.py)."""
    if settings.presence_tracking:
        with contextlib.suppress(Exception):
            headers = request.headers
            presence.touch(
                presence.client_ip(headers, request.client.host if request.client else None),
                path=request.url.path,
                country_hint=headers.get("cf-ipcountry"),
                user_agent=headers.get("user-agent", ""),
            )
    return await call_next(request)


# REST routers
app.include_router(auth.router)
app.include_router(leagues.router)
app.include_router(matches.router)
app.include_router(streams.router)
app.include_router(favorites.router)
app.include_router(proxy.router)
app.include_router(iptv.router)
app.include_router(video.router)
app.include_router(presence_router.router)
app.include_router(admin.router)

# WebSocket
app.add_api_websocket_route("/ws/live", live_scores_ws)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "GoalStream API is running"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
