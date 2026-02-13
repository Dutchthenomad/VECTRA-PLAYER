"""
FastAPI application for rugs-sanitizer service.

Endpoints:
- /health         Health check
- /stats          Pipeline and broadcaster statistics
- /channels       List available channels
- /feed/game      WebSocket: GameTick events
- /feed/stats     WebSocket: SessionStats events
- /feed/trades    WebSocket: Trade events
- /feed/history   WebSocket: GameHistoryRecord events
- /feed/all       WebSocket: All events
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .models import Channel

if TYPE_CHECKING:
    from .broadcaster import ChannelBroadcaster
    from .history_collector import HistoryCollector
    from .sanitizer import SanitizationPipeline
    from .upstream import UpstreamClient

logger = logging.getLogger(__name__)

# Channel name to enum mapping for URL routing
CHANNEL_MAP: dict[str, Channel] = {
    "game": Channel.GAME,
    "stats": Channel.STATS,
    "trades": Channel.TRADES,
    "history": Channel.HISTORY,
    "all": Channel.ALL,
}


def create_app(
    pipeline: SanitizationPipeline | None = None,
    broadcaster: ChannelBroadcaster | None = None,
    upstream: UpstreamClient | None = None,
    history_collector: HistoryCollector | None = None,
) -> FastAPI:
    """Create FastAPI application.

    Components are passed in to allow testing with mocks.
    """
    start_time = datetime.now(UTC)

    app = FastAPI(
        title="Rugs Sanitizer Service",
        description="Sanitized, typed, categorized WebSocket feed for rugs.fun",
        version="1.0.0",
    )

    # --- Monitor UI ---

    @app.get("/monitor")
    async def monitor():
        """Redirect to monitor HTML page."""
        return RedirectResponse(url="/static/monitor.html")

    # Static files mounted after all routes (see end of function)

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        uptime = (datetime.now(UTC) - start_time).total_seconds()
        return {
            "status": "healthy",
            "service": "rugs-sanitizer",
            "version": "1.0.0",
            "uptime_seconds": uptime,
            "upstream": upstream.get_stats() if upstream else None,
            "pipeline": pipeline.get_stats() if pipeline else None,
            "broadcaster": broadcaster.get_stats() if broadcaster else None,
            "history_collector": (history_collector.get_stats() if history_collector else None),
        }

    @app.get("/stats")
    async def stats():
        """Detailed statistics."""
        return {
            "pipeline": pipeline.get_stats() if pipeline else {},
            "broadcaster": broadcaster.get_stats() if broadcaster else {},
            "upstream": upstream.get_stats() if upstream else {},
            "history_collector": (history_collector.get_stats() if history_collector else {}),
        }

    @app.get("/channels")
    async def channels():
        """List available WebSocket channels."""
        channel_info = []
        for name, ch in CHANNEL_MAP.items():
            clients = broadcaster.client_count(ch) if broadcaster else 0
            channel_info.append(
                {
                    "name": name,
                    "path": f"/feed/{name}",
                    "clients": clients,
                    "description": _channel_description(ch),
                }
            )
        return {"channels": channel_info}

    # --- WebSocket endpoints ---

    @app.websocket("/feed/{channel_name}")
    async def websocket_feed(websocket: WebSocket, channel_name: str):
        """WebSocket feed for a specific channel.

        Protocol: Server -> Client (unidirectional).
        Client can send 'ping' for keepalive.
        """
        if channel_name not in CHANNEL_MAP:
            await websocket.close(code=4004, reason=f"Unknown channel: {channel_name}")
            return

        channel = CHANNEL_MAP[channel_name]
        await websocket.accept()

        if broadcaster:
            await broadcaster.subscribe(websocket, channel)

        logger.info(f"Client connected to /feed/{channel_name}")

        try:
            while True:
                try:
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    if data.get("action") == "ping":
                        await websocket.send_json(
                            {
                                "type": "pong",
                                "ts": data.get("ts"),
                            }
                        )
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            logger.info(f"Client disconnected from /feed/{channel_name}")
        except Exception as e:
            logger.error(f"WebSocket error on /feed/{channel_name}: {e}")
        finally:
            if broadcaster:
                await broadcaster.unsubscribe(websocket, channel)

    # Mount static files LAST (catch-all path matching)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


def _channel_description(channel: Channel) -> str:
    """Human-readable channel description."""
    return {
        Channel.GAME: "GameTick events (price, phase, active, rugged)",
        Channel.STATS: "SessionStats (connectedPlayers, averageMultiplier, countNx)",
        Channel.TRADES: "Annotated Trade events (with forced sell, practice/real inference)",
        Channel.HISTORY: "GameHistoryRecord (every 10th rug, god candle captures)",
        Channel.ALL: "All events from all channels",
    }.get(channel, "Unknown")
