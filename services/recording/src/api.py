"""
Recording Service API - FastAPI endpoints for control and monitoring.

Endpoints:
    GET  /health          - Service health check
    GET  /recording/status - Current recording status and stats
    POST /recording/start  - Start recording
    POST /recording/stop   - Stop recording
    GET  /recording/stats  - Detailed statistics
    GET  /recording/recent - Recent captured games
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

if TYPE_CHECKING:
    from .subscriber import RecordingSubscriber

logger = logging.getLogger(__name__)


def extract_tick_count(game: dict) -> int:
    """Extract tick count from game data with robust field handling.

    Handles:
    - prices array (may be JSON string from Parquet)
    - Various field names: tickCount, ticks, tick_count
    """
    # Try prices array (may be JSON string)
    prices = game.get("prices")
    if prices:
        if isinstance(prices, str):
            try:
                prices = json.loads(prices)
            except (json.JSONDecodeError, TypeError):
                prices = []
        if isinstance(prices, list) and len(prices) > 0:
            return len(prices)

    # Try various field names
    for field in ["tickCount", "ticks", "tick_count"]:
        if game.get(field):
            try:
                return int(game[field])
            except (ValueError, TypeError):
                continue
    return 0


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    uptime_seconds: float
    foundation_connected: bool
    memory_mb: float | None = None


class StatusResponse(BaseModel):
    """Recording status response."""

    enabled: bool
    games_captured: int
    session_start: str | None
    last_rug_time: str | None
    last_rug_multiplier: float | None


class StatsResponse(BaseModel):
    """Detailed statistics response."""

    session: int
    today: int
    total: int
    deduped: int
    storage: dict


class ToggleResponse(BaseModel):
    """Toggle action response."""

    success: bool
    message: str
    enabled: bool


class RecentGame(BaseModel):
    """Recent game entry."""

    game_id: str
    ticks: int
    final_price: float
    captured_at: str


def create_app(
    subscriber: "RecordingSubscriber",
    config_path: Path,
    start_time: datetime,
) -> FastAPI:
    """
    Create FastAPI application with recording service endpoints.

    Args:
        subscriber: RecordingSubscriber instance
        config_path: Path to config directory for state persistence
        start_time: Service start time for uptime calculation

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Recording Service",
        description="VECTRA Recording Service - Captures game data via gameHistory extraction",
        version="1.0.0",
    )

    # Add CORS middleware for UI access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for local dev
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # State persistence path
    state_file = config_path / "recording_state.json"

    def _save_state() -> None:
        """Persist recording state to disk."""
        try:
            state = {
                "enabled": subscriber.is_recording,
                "last_updated": datetime.utcnow().isoformat(),
            }
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save recording state: {e}")

    def _load_state() -> bool | None:
        """Load recording state from disk."""
        try:
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                return state.get("enabled")
        except Exception as e:
            logger.error(f"Failed to load recording state: {e}")
        return None

    @app.on_event("startup")
    async def startup():
        """Load persisted state on startup."""
        saved_state = _load_state()
        if saved_state is not None:
            if saved_state and not subscriber.is_recording:
                subscriber.start_recording()
            elif not saved_state and subscriber.is_recording:
                subscriber.stop_recording()
            logger.info(f"Loaded recording state: enabled={saved_state}")

    def _get_memory_mb() -> float | None:
        """Get process memory usage in MB from /proc/self/status."""
        try:
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        # VmRSS is in kB
                        kb = int(line.split()[1])
                        return round(kb / 1024, 1)
        except Exception:
            pass
        return None

    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Health check endpoint."""
        uptime = (datetime.utcnow() - start_time).total_seconds()
        return HealthResponse(
            status="healthy",
            service="recording-service",
            version="1.0.0",
            uptime_seconds=round(uptime, 2),
            foundation_connected=subscriber._connected,
            memory_mb=_get_memory_mb(),
        )

    @app.get("/recording/status", response_model=StatusResponse)
    async def recording_status():
        """Get current recording status."""
        stats = subscriber.stats
        return StatusResponse(
            enabled=stats.is_recording,
            games_captured=stats.session_games,
            session_start=stats.session_start.isoformat() if stats.is_recording else None,
            last_rug_time=stats.last_rug_time.isoformat() if stats.last_rug_time else None,
            last_rug_multiplier=stats.last_rug_multiplier,
        )

    @app.post("/recording/start", response_model=ToggleResponse)
    async def start_recording():
        """Start recording."""
        if subscriber.is_recording:
            return ToggleResponse(
                success=False,
                message="Recording is already active",
                enabled=True,
            )

        subscriber.start_recording()
        _save_state()

        return ToggleResponse(
            success=True,
            message="Recording started",
            enabled=True,
        )

    @app.post("/recording/stop", response_model=ToggleResponse)
    async def stop_recording():
        """Stop recording."""
        if not subscriber.is_recording:
            return ToggleResponse(
                success=False,
                message="Recording is already stopped",
                enabled=False,
            )

        subscriber.stop_recording()
        _save_state()

        return ToggleResponse(
            success=True,
            message="Recording stopped",
            enabled=False,
        )

    @app.get("/recording/stats", response_model=StatsResponse)
    async def recording_stats():
        """Get detailed recording statistics."""
        stats = subscriber.stats
        storage_stats = subscriber._storage.get_storage_stats()

        return StatsResponse(
            session=stats.session_games,
            today=stats.today_games,
            total=stats.total_games,
            deduped=stats.deduped_count,
            storage=storage_stats,
        )

    @app.get("/recording/recent")
    async def recent_games(limit: int = 10):
        """Get recently captured games."""
        if limit > 100:
            raise HTTPException(status_code=400, detail="Limit cannot exceed 100")

        games = subscriber.get_recent_games(limit)

        # Transform to API format
        result = []
        for game in games:
            game_id = game.get("id") or game.get("gameId") or game.get("game_id", "unknown")
            result.append(
                {
                    "game_id": game_id,
                    "ticks": extract_tick_count(game),
                    "final_price": game.get("peakMultiplier")
                    or game.get("finalPrice")
                    or game.get("price", 0),
                    "captured_at": game.get("_captured_at", ""),
                }
            )

        return result

    return app
