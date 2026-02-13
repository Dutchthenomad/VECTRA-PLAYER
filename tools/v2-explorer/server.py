"""
v2-explorer HTTP server.

Provides REST API for the sidebet replay engine and serves static files
for the trace visualization UI.

Endpoints:
  GET  /api/sidebet/games              — list available games
  POST /api/sidebet/replay             — replay game(s), summary only
  POST /api/sidebet/replay-traced      — replay single game with full trace

Run:
  cd tools/v2-explorer && python server.py
  # or: uvicorn server:app --host 0.0.0.0 --port 9040 --reload
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from modules.sidebet import SidebetModule
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="v2-explorer", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (demo-trace.html etc.)
_STATIC = Path(__file__).parent / "static"
if _STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

# Lazy-loaded module (loads game data on first request)
_module: SidebetModule | None = None


def _get_module() -> SidebetModule:
    global _module
    if _module is None:
        logger.info("Loading SidebetModule (first request — may take a few seconds)…")
        _module = SidebetModule()
    return _module


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ReplayRequest(BaseModel):
    game_id: str = Field(..., description="Game ID to replay")
    initial_bankroll: float = Field(1.0, ge=0.001)


class ReplayTracedRequest(BaseModel):
    game_id: str = Field(..., description="Single game ID for traced replay")
    initial_bankroll: float = Field(1.0, ge=0.001)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/sidebet/games")
def list_games(limit: int = Query(50, ge=1, le=500)):
    """List available games."""
    mod = _get_module()
    return mod.list_games(limit=limit)


@app.post("/api/sidebet/replay")
def replay(req: ReplayRequest):
    """Replay a single game — returns summary (no per-tick trace)."""
    mod = _get_module()
    try:
        result = mod.replay_game(req.game_id, initial_bankroll=req.initial_bankroll)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return asdict(result)


@app.post("/api/sidebet/replay-traced")
def replay_traced(req: ReplayTracedRequest):
    """Replay a single game with full per-tick pipeline trace.

    Response includes a `tick_traces` array with 5-stage pipeline
    output for every tick.  Use the /static/demo-trace.html UI to
    explore the data interactively.
    """
    mod = _get_module()
    try:
        result = mod.replay_game_traced(
            req.game_id,
            initial_bankroll=req.initial_bankroll,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return asdict(result)


@app.get("/")
def root():
    """Redirect to trace demo."""
    return {"message": "v2-explorer API", "docs": "/docs", "trace_ui": "/static/demo-trace.html"}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=9040, reload=True)
