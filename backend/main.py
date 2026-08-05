import asyncio
import contextlib
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from config import settings
from routers import auth, leagues, matches, streams, favorites, proxy, iptv, video
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
    warmer = asyncio.create_task(_warm_featured())
    yield
    warmer.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await warmer


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

# REST routers
app.include_router(auth.router)
app.include_router(leagues.router)
app.include_router(matches.router)
app.include_router(streams.router)
app.include_router(favorites.router)
app.include_router(proxy.router)
app.include_router(iptv.router)
app.include_router(video.router)

# WebSocket
app.add_api_websocket_route("/ws/live", live_scores_ws)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "GoalStream API is running"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
