from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from config import settings
from routers import auth, leagues, matches, streams, favorites, proxy, iptv
from websocket import live_scores_ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


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

# WebSocket
app.add_api_websocket_route("/ws/live", live_scores_ws)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "GoalStream API is running"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
