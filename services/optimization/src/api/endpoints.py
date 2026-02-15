"""FastAPI endpoints for Optimization Service."""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

if TYPE_CHECKING:
    from ..subscriber import OptimizationSubscriber


def create_app(
    subscriber: "OptimizationSubscriber",
    config_path: Path,
    start_time: datetime,
) -> FastAPI:
    """
    Create FastAPI application.

    Args:
        subscriber: OptimizationSubscriber instance
        config_path: Path to config directory
        start_time: Service start time

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="Optimization Service",
        description="Statistical optimization and strategy profile producer",
        version="1.0.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "optimization-service",
            "uptime_seconds": (datetime.utcnow() - start_time).total_seconds(),
        }

    @app.get("/stats")
    async def get_stats():
        """Get service statistics."""
        return subscriber.stats.to_dict()

    @app.get("/profiles")
    async def list_profiles():
        """List generated profiles."""
        profile = subscriber.current_profile
        if profile:
            return {"profiles": [profile.to_dict()], "count": 1}
        return {"profiles": [], "count": 0}

    @app.get("/profiles/current")
    async def get_current_profile():
        """Get current active profile."""
        profile = subscriber.current_profile
        if not profile:
            raise HTTPException(status_code=404, detail="No profile generated yet")
        return profile.to_dict()

    @app.post("/profiles/generate")
    async def generate_profile():
        """Force profile generation."""
        profile = subscriber.force_generate_profile()
        if not profile:
            raise HTTPException(
                status_code=400,
                detail="Not enough games collected for profile generation",
            )
        return profile.to_dict()

    @app.get("/games")
    async def list_collected_games():
        """List collected games."""
        games = subscriber.get_collected_games()
        return {"games": games, "count": len(games)}

    @app.get("/analysis/survival")
    async def get_survival_analysis():
        """Get survival analysis from current data."""
        from ..analyzers.survival import (
            compute_conditional_probability,
            compute_survival_curve,
            find_optimal_entry_window,
        )

        games = subscriber.get_collected_games()
        if not games:
            raise HTTPException(status_code=400, detail="No games collected")

        durations = np.array([g.get("duration", 200) for g in games])

        survival = compute_survival_curve(durations)
        cond_prob = compute_conditional_probability(durations)
        optimal = find_optimal_entry_window(durations)

        return {
            "survival_curve": {
                "times": survival["times"].tolist(),
                "survival": survival["survival"].tolist(),
            },
            "conditional_probability_sample": {
                "tick_100": float(cond_prob[100]) if len(cond_prob) > 100 else None,
                "tick_200": float(cond_prob[200]) if len(cond_prob) > 200 else None,
                "tick_300": float(cond_prob[300]) if len(cond_prob) > 300 else None,
            },
            "optimal_entry": optimal,
        }

    return app
