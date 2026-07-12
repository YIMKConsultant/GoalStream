"""
WebSocket endpoint that pushes live score updates to connected React Native clients.
The scheduler polls the football API every 30 s while any client is connected.
"""
import asyncio
import json
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
from services.football_api import get_live_matches

connected: Set[WebSocket] = set()
_task: asyncio.Task | None = None


async def _broadcast_live_scores():
    while connected:
        try:
            matches = await get_live_matches()
            payload = json.dumps({"event": "live_scores", "data": matches})
            dead = set()
            for ws in list(connected):
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.add(ws)
            connected.difference_update(dead)
        except Exception:
            pass
        await asyncio.sleep(30)


async def live_scores_ws(websocket: WebSocket):
    global _task
    await websocket.accept()
    connected.add(websocket)

    if _task is None or _task.done():
        _task = asyncio.create_task(_broadcast_live_scores())

    try:
        while True:
            # Keep alive — client can send "ping"
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        connected.discard(websocket)
