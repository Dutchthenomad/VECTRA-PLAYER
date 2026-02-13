"""
FastAPI application for Rugs Feed Service.

Endpoints:
- /health - Health check
- /feed - WebSocket feed for downstream subscribers
- /api/games - Recent captured games
- /api/games/{game_id} - Single game with events
- /api/seeds - Seed reveals for PRNG analysis
- /api/history - Complete game records from gameHistory
- /api/export - JSONL export for attack suite
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from .broadcaster import get_broadcaster
from .storage import EventStorage

logger = logging.getLogger(__name__)


def create_app(
    db_path: str = "/data/rugs_feed.db",
    auto_connect: bool = True,
) -> FastAPI:
    """
    Create FastAPI application.

    Args:
        db_path: Path to SQLite database
        auto_connect: Whether to auto-connect to rugs.fun

    Returns:
        FastAPI application instance
    """
    start_time = datetime.now(timezone.utc)

    # Create storage instance at app creation time
    # Closures capture this variable for all route handlers
    storage = EventStorage(db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan handler."""
        # Startup
        await storage.initialize()
        logger.info(f"Storage initialized: {db_path}")

        yield

        # Shutdown
        await storage.close()
        logger.info("Storage closed")

    app = FastAPI(
        title="Rugs Feed Service",
        description="Direct WebSocket capture for rugs.fun PRNG analysis",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        stats = await storage.get_stats()

        return {
            "status": "healthy",
            "service": "rugs-feed",
            "version": "1.0.0",
            "uptime_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            "stats": stats,
        }

    @app.get("/api/games")
    async def get_games(limit: int = 100):
        """Get recent captured games."""
        games = await storage.get_recent_games(limit=limit)
        return {"games": games, "count": len(games)}

    @app.get("/api/games/{game_id}")
    async def get_game(game_id: str):
        """Get single game with all events."""
        events = await storage.get_game_events(game_id)
        if not events:
            raise HTTPException(404, f"Game {game_id} not found")

        return {"game_id": game_id, "events": events, "event_count": len(events)}

    @app.get("/api/seeds")
    async def get_seeds(limit: int = 100):
        """Get games with revealed server seeds."""
        seeds = await storage.get_seed_reveals(limit=limit)
        return {"seeds": seeds, "count": len(seeds)}

    @app.get("/api/export")
    async def export_prng():
        """Export data in JSONL format for PRNG attack suite."""
        data = await storage.export_for_prng()

        async def generate():
            for item in data:
                yield json.dumps(item) + "\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": "attachment; filename=rugs_seeds.jsonl"},
        )

    @app.get("/api/stats")
    async def get_stats():
        """Get service statistics."""
        storage_stats = await storage.get_stats()
        broadcaster = get_broadcaster()
        return {
            **storage_stats,
            "broadcaster": broadcaster.get_stats(),
        }

    @app.get("/api/history")
    async def get_history(limit: int = 100, with_seed_only: bool = False):
        """
        Get complete game records from gameHistory.

        These are captured on rug events and include:
        - Server seed (provablyFair)
        - Global trades and sidebets
        - Peak multiplier
        """
        records = await storage.get_game_history(limit=limit, with_seed_only=with_seed_only)
        return {"records": records, "count": len(records)}

    @app.websocket("/feed")
    async def websocket_feed(websocket: WebSocket):
        """
        WebSocket feed for downstream subscribers.

        Broadcasts all raw Socket.IO events from rugs.fun.
        Protocol: Server -> Client only (unidirectional).
        Clients can send 'ping' for keepalive.
        """
        await websocket.accept()

        broadcaster = get_broadcaster()
        await broadcaster.register(websocket)

        logger.info("WebSocket client connected to /feed")

        try:
            while True:
                # Keep connection alive, handle client pings
                try:
                    message = await websocket.receive_text()
                    # Handle ping
                    data = json.loads(message)
                    if data.get("action") == "ping":
                        await websocket.send_json({"type": "pong", "ts": data.get("ts")})
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from /feed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await broadcaster.unregister(websocket)

    return app
