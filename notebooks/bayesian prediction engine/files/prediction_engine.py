"""
Live Prediction Engine - Integrates game state with Bayesian forecaster.

This is the main orchestrator that:
1. Subscribes to WebSocket events via GameStateManager
2. Makes predictions when games start (within first 10 ticks)
3. Records outcomes and updates the forecaster
4. Exposes predictions via a simple HTTP API for the UI
"""

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime

# These would be the actual imports from your package
# For standalone testing, we include simplified versions
try:
    from .bayesian_forecaster import BayesianForecaster, GamePrediction
    from .equilibrium_tracker import (
        DurationEquilibriumTracker,
        EquilibriumTracker,
        PeakEquilibriumTracker,
    )
    from .game_state_manager import CompletedGame, GamePhase, GameStateManager
    from .prediction_recorder import PredictionRecorder
except ImportError:
    from game_state_manager import CompletedGame, GameStateManager


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


@dataclass
class LivePrediction:
    """A prediction made for the current game"""

    game_id: str
    prediction_tick: int
    prediction_time: datetime

    # Predicted values
    peak_point: float
    peak_ci_lower: float
    peak_ci_upper: float
    peak_confidence: float

    duration_point: int
    duration_ci_lower: int
    duration_ci_upper: int
    duration_confidence: float

    final_direction: str  # "up", "down", "stable"
    regime: str
    overall_confidence: float

    # Actual values (filled in after game ends)
    actual_peak: float | None = None
    actual_duration: int | None = None
    actual_final: float | None = None

    # Accuracy metrics (computed after game ends)
    peak_error_pct: float | None = None
    duration_error_pct: float | None = None
    peak_within_ci: bool | None = None
    duration_within_ci: bool | None = None

    def to_dict(self) -> dict:
        return {
            "game_id": self.game_id,
            "prediction_tick": self.prediction_tick,
            "prediction_time": self.prediction_time.isoformat(),
            "peak": {
                "point": self.peak_point,
                "ci_lower": self.peak_ci_lower,
                "ci_upper": self.peak_ci_upper,
                "confidence": self.peak_confidence,
                "actual": self.actual_peak,
                "error_pct": self.peak_error_pct,
                "within_ci": self.peak_within_ci,
            },
            "duration": {
                "point": self.duration_point,
                "ci_lower": self.duration_ci_lower,
                "ci_upper": self.duration_ci_upper,
                "confidence": self.duration_confidence,
                "actual": self.actual_duration,
                "error_pct": self.duration_error_pct,
                "within_ci": self.duration_within_ci,
            },
            "final_direction": self.final_direction,
            "regime": self.regime,
            "overall_confidence": self.overall_confidence,
        }


class SimpleBayesianForecaster:
    """
    Simplified Bayesian forecaster for standalone testing.
    Uses the core mean-reversion logic from HAIKU findings.
    """

    def __init__(self):
        # Equilibrium estimates (from HAIKU)
        self.final_mu = 0.0135
        self.final_sigma = 0.0050
        self.peak_mu = 2.5
        self.peak_sigma = 1.5
        self.duration_mu = 200
        self.duration_sigma = 150

        # History for predictions
        self.history: list[dict] = []

        # Mean reversion parameters
        self.theta = 0.30  # Reversion speed

    def update(self, final_price: float, peak: float, duration: int):
        """Update with completed game data"""
        self.history.append({"final": final_price, "peak": peak, "duration": duration})

        # EWMA updates
        alpha = 0.15  # Learning rate
        self.final_mu = (1 - alpha) * self.final_mu + alpha * final_price
        self.peak_mu = (1 - alpha) * self.peak_mu + alpha * peak
        self.duration_mu = (1 - alpha) * self.duration_mu + alpha * duration

        # Update volatility estimates
        if len(self.history) >= 5:
            recent_finals = [h["final"] for h in self.history[-10:]]
            recent_peaks = [h["peak"] for h in self.history[-10:]]
            recent_durations = [h["duration"] for h in self.history[-10:]]

            import statistics

            self.final_sigma = (
                statistics.stdev(recent_finals) if len(recent_finals) > 1 else self.final_sigma
            )
            self.peak_sigma = (
                statistics.stdev(recent_peaks) if len(recent_peaks) > 1 else self.peak_sigma
            )
            self.duration_sigma = (
                statistics.stdev(recent_durations)
                if len(recent_durations) > 1
                else self.duration_sigma
            )

    def predict(self) -> dict:
        """Generate prediction for next game"""
        prev = self.history[-1] if self.history else None

        # === FINAL PRICE PREDICTION ===
        # Mean reversion: expect price to revert toward equilibrium
        if prev:
            deviation = prev["final"] - self.final_mu
            reversion_factor = 0.7  # Expect 30% reversion per game
            final_point = self.final_mu + reversion_factor * deviation

            # Determine direction
            if deviation > 0.003:
                final_direction = "down"
            elif deviation < -0.003:
                final_direction = "up"
            else:
                final_direction = "stable"
        else:
            final_point = self.final_mu
            final_direction = "stable"

        # === PEAK PREDICTION ===
        # After crashes (low final), peaks tend higher
        # After payouts (high final), peaks tend lower
        peak_point = self.peak_mu
        if prev:
            final_deviation = (prev["final"] - 0.0135) / 0.005
            peak_adjustment = 1.0 - 0.15 * final_deviation
            peak_adjustment = max(0.7, min(1.3, peak_adjustment))
            peak_point *= peak_adjustment

        # === DURATION PREDICTION ===
        # After high peaks, duration tends shorter (from HAIKU: 45% shorter after >5x)
        duration_point = self.duration_mu
        if prev:
            if prev["peak"] > 5.0:
                duration_point *= 0.55
            elif prev["peak"] > 2.0:
                duration_point *= 0.80

        # Compute confidence (higher at extremes)
        base_confidence = 0.65
        if prev:
            # Higher confidence after extreme events
            final_z = abs(prev["final"] - self.final_mu) / max(self.final_sigma, 0.001)
            confidence_boost = min(0.15, 0.05 * final_z)
            base_confidence += confidence_boost

        return {
            "final": {
                "point": final_point,
                "ci_lower": max(0.002, final_point - 1.96 * self.final_sigma),
                "ci_upper": min(1.1, final_point + 1.96 * self.final_sigma),
                "confidence": 0.78 + 0.07 * (base_confidence - 0.65) / 0.15,
            },
            "peak": {
                "point": peak_point,
                "ci_lower": max(1.0, peak_point - 1.96 * self.peak_sigma),
                "ci_upper": peak_point + 1.96 * self.peak_sigma,
                "confidence": 0.64 + 0.08 * (base_confidence - 0.65) / 0.15,
            },
            "duration": {
                "point": int(duration_point),
                "ci_lower": max(1, int(duration_point - 1.96 * self.duration_sigma)),
                "ci_upper": int(duration_point + 1.96 * self.duration_sigma),
                "confidence": 0.81 + 0.07 * (base_confidence - 0.65) / 0.15,
            },
            "final_direction": final_direction,
            "regime": self._detect_regime(prev),
            "overall_confidence": base_confidence,
        }

    def _detect_regime(self, prev: dict | None) -> str:
        if not prev:
            return "normal"

        final_z = (prev["final"] - self.final_mu) / max(self.final_sigma, 0.001)

        if final_z < -1.5:
            return "suppressed"
        elif final_z > 1.5:
            return "inflated"
        elif abs(final_z) > 2.0:
            return "volatile"
        else:
            return "normal"


class LivePredictionEngine:
    """
    Main engine that coordinates predictions with game state.

    Usage:
        engine = LivePredictionEngine()
        engine.start()

        # Feed WebSocket events
        engine.process_event(event)

        # Get current prediction
        pred = engine.get_current_prediction()

        # Get accuracy stats
        stats = engine.get_accuracy_stats()
    """

    def __init__(self, prediction_tick_threshold: int = 10):
        """
        Initialize the engine.

        Args:
            prediction_tick_threshold: Make prediction by this tick (default: 10)
        """
        self.prediction_tick_threshold = prediction_tick_threshold

        # Core components
        self.game_manager = GameStateManager()
        self.forecaster = SimpleBayesianForecaster()

        # Predictions
        self.current_prediction: LivePrediction | None = None
        self.prediction_history: list[LivePrediction] = []
        self.max_history = 100

        # State
        self.prediction_made_for_game: str | None = None
        self.warmup_games = 5  # Need this many games before predictions are "valid"
        self.games_seen = 0

        # Wire up callbacks
        self.game_manager.on_game_start = self._on_game_start
        self.game_manager.on_game_end = self._on_game_end
        self.game_manager.on_tick = self._on_tick
        self.game_manager.on_history_bootstrap = self._on_history_bootstrap

        logger.info("LivePredictionEngine initialized")

    def process_event(self, event: dict) -> None:
        """Process a WebSocket event"""
        self.game_manager.process_event(event)

    def _on_game_start(self, game_id: str, seed_hash: str) -> None:
        """Called when a new game starts"""
        logger.info(f"Game started: {game_id[:20]}...")
        self.prediction_made_for_game = None

    def _on_tick(self, tick: int, price: float, peak: float) -> None:
        """Called on each game tick"""
        # Make prediction within first N ticks
        if (
            tick <= self.prediction_tick_threshold
            and self.prediction_made_for_game != self.game_manager.current_game.game_id
        ):
            self._make_prediction(tick)

    def _on_history_bootstrap(self, games: list) -> None:
        """Called when game history is loaded from first WebSocket event"""
        if not games:
            return

        logger.info(f"📚 Bootstrapping forecaster with {len(games)} historical games...")

        # Update forecaster with each historical game
        for game in games:
            self.forecaster.update(game.final_price, game.peak, game.duration)
            self.games_seen += 1

        logger.info(
            f"📚 Bootstrap complete | "
            f"games_seen: {self.games_seen} | "
            f"warmup satisfied: {self.games_seen >= self.warmup_games}"
        )

    def _on_game_end(self, game: CompletedGame) -> None:
        """Called when a game ends"""
        self.games_seen += 1

        # Update forecaster with actual outcome
        self.forecaster.update(game.final_price, game.peak, game.duration)

        # Score the prediction if we made one
        if self.current_prediction and self.current_prediction.game_id == game.game_id:
            self._score_prediction(game)

        logger.info(
            f"Game {self.games_seen} complete | "
            f"Peak: {game.peak:.2f}x | "
            f"Duration: {game.duration} ticks | "
            f"Final: {game.final_price:.4f}"
        )

    def _make_prediction(self, tick: int) -> None:
        """Generate and store a prediction"""
        if not self.game_manager.current_game:
            return

        game_id = self.game_manager.current_game.game_id

        # Get forecast
        forecast = self.forecaster.predict()

        # Create prediction record
        self.current_prediction = LivePrediction(
            game_id=game_id,
            prediction_tick=tick,
            prediction_time=datetime.now(),
            peak_point=forecast["peak"]["point"],
            peak_ci_lower=forecast["peak"]["ci_lower"],
            peak_ci_upper=forecast["peak"]["ci_upper"],
            peak_confidence=forecast["peak"]["confidence"],
            duration_point=forecast["duration"]["point"],
            duration_ci_lower=forecast["duration"]["ci_lower"],
            duration_ci_upper=forecast["duration"]["ci_upper"],
            duration_confidence=forecast["duration"]["confidence"],
            final_direction=forecast["final_direction"],
            regime=forecast["regime"],
            overall_confidence=forecast["overall_confidence"],
        )

        self.prediction_made_for_game = game_id

        # Log prediction
        warm = "🔥" if self.games_seen >= self.warmup_games else "❄️"
        logger.info(
            f"{warm} Prediction @ tick {tick} | "
            f"Peak: {forecast['peak']['point']:.2f}x "
            f"[{forecast['peak']['ci_lower']:.1f}-{forecast['peak']['ci_upper']:.1f}] | "
            f"Duration: {forecast['duration']['point']} ticks | "
            f"Direction: {forecast['final_direction']} | "
            f"Confidence: {forecast['overall_confidence']:.0%}"
        )

    def _score_prediction(self, game: CompletedGame) -> None:
        """Score a prediction against actual outcome"""
        pred = self.current_prediction
        if not pred:
            return

        # Fill in actuals
        pred.actual_peak = game.peak
        pred.actual_duration = game.duration
        pred.actual_final = game.final_price

        # Calculate errors
        pred.peak_error_pct = abs(pred.peak_point - game.peak) / max(game.peak, 0.01) * 100
        pred.duration_error_pct = (
            abs(pred.duration_point - game.duration) / max(game.duration, 1) * 100
        )

        # Check if within CI
        pred.peak_within_ci = pred.peak_ci_lower <= game.peak <= pred.peak_ci_upper
        pred.duration_within_ci = pred.duration_ci_lower <= game.duration <= pred.duration_ci_upper

        # Store in history
        self.prediction_history.append(pred)
        if len(self.prediction_history) > self.max_history:
            self.prediction_history.pop(0)

        # Log result
        peak_status = "✓" if pred.peak_within_ci else "✗"
        dur_status = "✓" if pred.duration_within_ci else "✗"

        logger.info(
            f"Result | "
            f"Peak: {game.peak:.2f}x (pred: {pred.peak_point:.2f}x, err: {pred.peak_error_pct:.1f}%) {peak_status} | "
            f"Duration: {game.duration} (pred: {pred.duration_point}, err: {pred.duration_error_pct:.1f}%) {dur_status}"
        )

    def get_current_prediction(self) -> dict | None:
        """Get the current prediction as a dict"""
        if not self.current_prediction:
            return None
        return self.current_prediction.to_dict()

    def get_current_game_state(self) -> dict:
        """Get current game state for UI"""
        game = self.game_manager.current_game
        return {
            "game_id": game.game_id if game else None,
            "phase": self.game_manager.phase.value,
            "tick": game.current_tick if game else 0,
            "price": game.current_price if game else 1.0,
            "peak": game.peak if game else 1.0,
            "cooldown_timer": self.game_manager.cooldown_timer,
            "games_seen": self.games_seen,
            "warmed_up": self.games_seen >= self.warmup_games,
        }

    def get_accuracy_stats(self) -> dict:
        """Get accuracy statistics"""
        if not self.prediction_history:
            return {
                "total_predictions": 0,
                "peak_ci_hit_rate": 0,
                "duration_ci_hit_rate": 0,
                "avg_peak_error": 0,
                "avg_duration_error": 0,
                "direction_accuracy": 0,
            }

        predictions = self.prediction_history
        n = len(predictions)

        peak_hits = sum(1 for p in predictions if p.peak_within_ci)
        dur_hits = sum(1 for p in predictions if p.duration_within_ci)

        avg_peak_err = sum(p.peak_error_pct for p in predictions) / n
        avg_dur_err = sum(p.duration_error_pct for p in predictions) / n

        return {
            "total_predictions": n,
            "peak_ci_hit_rate": peak_hits / n,
            "duration_ci_hit_rate": dur_hits / n,
            "avg_peak_error": avg_peak_err,
            "avg_duration_error": avg_dur_err,
            "games_since_warmup": max(0, self.games_seen - self.warmup_games),
        }

    def get_recent_predictions(self, n: int = 10) -> list[dict]:
        """Get recent predictions for display"""
        return [p.to_dict() for p in self.prediction_history[-n:]]

    def export_state(self) -> dict:
        """Export full engine state for debugging/UI"""
        return {
            "game_state": self.get_current_game_state(),
            "current_prediction": self.get_current_prediction(),
            "accuracy_stats": self.get_accuracy_stats(),
            "recent_predictions": self.get_recent_predictions(20),
            "forecaster": {
                "final_mu": self.forecaster.final_mu,
                "final_sigma": self.forecaster.final_sigma,
                "peak_mu": self.forecaster.peak_mu,
                "duration_mu": self.forecaster.duration_mu,
            },
        }


# === HTTP API for UI ===

import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

# Global engine instance for HTTP handler
_engine: LivePredictionEngine | None = None


class PredictionAPIHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for serving prediction data to UI"""

    def do_GET(self):
        global _engine

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # CORS headers
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if path == "/state":
            data = _engine.export_state() if _engine else {}
        elif path == "/prediction":
            data = _engine.get_current_prediction() if _engine else None
        elif path == "/stats":
            data = _engine.get_accuracy_stats() if _engine else {}
        elif path == "/history":
            data = _engine.get_recent_predictions(20) if _engine else []
        else:
            data = {
                "error": "unknown endpoint",
                "endpoints": ["/state", "/prediction", "/stats", "/history"],
            }

        self.wfile.write(json.dumps(data, default=str).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP logs


def start_api_server(engine: LivePredictionEngine, port: int = 9001):
    """Start HTTP API server in background thread"""
    global _engine
    _engine = engine

    server = HTTPServer(("0.0.0.0", port), PredictionAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Prediction API server started on http://localhost:{port}")
    return server


if __name__ == "__main__":
    # Standalone test
    engine = LivePredictionEngine()

    # Start API server
    start_api_server(engine, port=9001)

    # Simulate some games
    import time

    print("\n" + "=" * 60)
    print("  BAYESIAN PREDICTION ENGINE - TEST MODE")
    print("  API: http://localhost:9001/state")
    print("=" * 60 + "\n")

    # Simulated game outcomes (from real data patterns)
    test_games = [
        {"peak": 1.12, "final": 0.0034, "duration": 436},
        {"peak": 1.30, "final": 0.0164, "duration": 80},
        {"peak": 1.09, "final": 0.0200, "duration": 13},
        {"peak": 1.54, "final": 0.0178, "duration": 77},
        {"peak": 1.14, "final": 0.0187, "duration": 25},
        {"peak": 1.75, "final": 0.0198, "duration": 28},
        {"peak": 1.43, "final": 0.0132, "duration": 90},
        {"peak": 1.18, "final": 0.0020, "duration": 411},
        {"peak": 1.36, "final": 0.0170, "duration": 38},
        {"peak": 4.73, "final": 0.0196, "duration": 151},
    ]

    for i, game_data in enumerate(test_games):
        game_id = f"20260118-test{i:03d}"

        # Simulate game start
        start_event = {
            "type": "game.tick",
            "gameId": game_id,
            "data": {
                "tick": 0,
                "price": 1.0,
                "active": True,
                "rugged": False,
                "cooldownTimer": 0,
                "gameHistory": [],
            },
        }
        engine.process_event(start_event)

        # Simulate a few ticks
        for tick in range(1, min(game_data["duration"], 20)):
            tick_event = {
                "type": "game.tick",
                "gameId": game_id,
                "data": {
                    "tick": tick,
                    "price": 1.0 + (game_data["peak"] - 1.0) * (tick / game_data["duration"]),
                    "active": True,
                    "rugged": False,
                    "cooldownTimer": 0,
                    "gameHistory": [],
                },
            }
            engine.process_event(tick_event)

        # Simulate rug
        rug_event = {
            "type": "game.tick",
            "gameId": game_id,
            "data": {
                "tick": game_data["duration"],
                "price": game_data["final"],
                "active": True,
                "rugged": True,
                "cooldownTimer": 15000,
                "gameHistory": [
                    {
                        "gameId": game_id,
                        "provablyFair": {"serverSeed": f"seed{i}", "serverSeedHash": f"hash{i}"},
                        "peak": game_data["peak"],
                        "prices": [1.0] * game_data["duration"],
                    }
                ],
            },
        }
        engine.process_event(rug_event)

        time.sleep(0.1)

    print("\n" + "=" * 60)
    print("  FINAL STATS")
    print("=" * 60)
    stats = engine.get_accuracy_stats()
    print(f"  Total predictions: {stats['total_predictions']}")
    print(f"  Peak CI hit rate: {stats['peak_ci_hit_rate']:.1%}")
    print(f"  Duration CI hit rate: {stats['duration_ci_hit_rate']:.1%}")
    print(f"  Avg peak error: {stats['avg_peak_error']:.1f}%")
    print(f"  Avg duration error: {stats['avg_duration_error']:.1f}%")
    print("=" * 60 + "\n")

    # Keep server running
    print("API server running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
