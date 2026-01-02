"""
GameHistoryCaptureService - Captures gameHistory[] for CANONICAL verification.

Phase: RAG Knowledge Extraction

This service subscribes to WS_RAW_EVENT and captures:
1. Rug event PAIRS (two gameStateUpdate emissions within ~500ms)
2. All standard/newTrade events (other players' trades)
3. All newSideBet events (other players' sidebets)
4. gameHistory[] arrays containing complete game replays

Usage:
    from services.game_history_capture import GameHistoryCaptureService
    from services.event_bus import event_bus

    capture = GameHistoryCaptureService(event_bus, output_dir="/path/to/captures")
    capture.start()

    # Later...
    capture.stop()
    print(f"Captured {capture.rug_count} rug pairs")
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.event_bus import EventBus, Events

logger = logging.getLogger(__name__)


@dataclass
class CaptureState:
    """Tracks capture session state."""

    session_id: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    )
    rug_count: int = 0
    trade_count: int = 0
    sidebet_count: int = 0
    gamestate_count: int = 0

    # Rug event pair detection
    pending_rug_emission: dict | None = None
    pending_rug_timestamp: float = 0.0

    # Track last known game state
    last_game_id: str | None = None
    last_rugged_state: bool = False

    # Capture targets
    target_rugs: int = 4
    capture_complete: bool = False


class GameHistoryCaptureService:
    """
    Captures gameHistory events from live rugs.fun connection.

    Subscribes to EventBus for:
    - WS_RAW_EVENT: All WebSocket events

    Detects rug event PAIRS by watching for two gameStateUpdate events
    with gameHistory[] within ~500ms of each other.

    Thread-safe: All file operations and state access protected by lock.
    """

    RUG_PAIR_WINDOW_MS = 500  # Max time between paired emissions

    def __init__(
        self,
        event_bus: EventBus,
        output_dir: Path | str | None = None,
        target_rugs: int = 4,
    ):
        """
        Initialize GameHistoryCaptureService.

        Args:
            event_bus: EventBus instance to subscribe to
            output_dir: Directory to save captures (default: ~/rugs_data/gamehistory_captures/)
            target_rugs: Number of rug pairs to capture before marking complete
        """
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._running = False

        # Set output directory
        if output_dir is None:
            output_dir = Path.home() / "rugs_data" / "gamehistory_captures"
        self.output_dir = Path(output_dir)

        # Initialize state
        self._state = CaptureState(target_rugs=target_rugs)

        # Create session-specific output directory
        self._session_dir = self.output_dir / self._state.session_id
        self._rug_dir = self._session_dir / "rug_events"
        self._trades_dir = self._session_dir / "trades"
        self._sidebets_dir = self._session_dir / "sidebets"
        self._gamestates_dir = self._session_dir / "gamestates"

        # File handles (opened on start)
        self._trades_file = None
        self._sidebets_file = None

        logger.info(
            f"GameHistoryCaptureService initialized: "
            f"output_dir={self._session_dir}, target_rugs={target_rugs}"
        )

    # ========== Properties (Thread-safe getters) ==========

    @property
    def is_running(self) -> bool:
        """True if capture is active."""
        with self._lock:
            return self._running

    @property
    def rug_count(self) -> int:
        """Number of rug pairs captured."""
        with self._lock:
            return self._state.rug_count

    @property
    def trade_count(self) -> int:
        """Number of trades captured."""
        with self._lock:
            return self._state.trade_count

    @property
    def sidebet_count(self) -> int:
        """Number of sidebets captured."""
        with self._lock:
            return self._state.sidebet_count

    @property
    def is_complete(self) -> bool:
        """True if target rug count reached."""
        with self._lock:
            return self._state.capture_complete

    @property
    def session_dir(self) -> Path:
        """Session output directory."""
        return self._session_dir

    # ========== Lifecycle ==========

    def start(self) -> None:
        """Start capturing events."""
        with self._lock:
            if self._running:
                logger.warning("GameHistoryCaptureService already running")
                return

            # Create directories
            for d in [self._rug_dir, self._trades_dir, self._sidebets_dir, self._gamestates_dir]:
                d.mkdir(parents=True, exist_ok=True)

            # Open file handles
            self._trades_file = open(self._trades_dir / "trades_session.jsonl", "a")
            self._sidebets_file = open(self._sidebets_dir / "sidebets_session.jsonl", "a")

            self._running = True

        # Subscribe to events (outside lock to prevent deadlock)
        self._event_bus.subscribe(Events.WS_RAW_EVENT, self._on_ws_raw_event, weak=False)

        logger.info(
            f"GameHistoryCaptureService started: session={self._state.session_id}, "
            f"target={self._state.target_rugs} rug pairs"
        )

    def stop(self) -> None:
        """Stop capturing and save manifest."""
        # Unsubscribe first (outside lock)
        try:
            self._event_bus.unsubscribe(Events.WS_RAW_EVENT, self._on_ws_raw_event)
        except Exception as e:
            logger.warning(f"Error unsubscribing: {e}")

        with self._lock:
            if not self._running:
                return

            self._running = False

            # Close file handles
            if self._trades_file:
                self._trades_file.close()
                self._trades_file = None

            if self._sidebets_file:
                self._sidebets_file.close()
                self._sidebets_file = None

            # Save manifest
            self._save_manifest()

        logger.info(
            f"GameHistoryCaptureService stopped: "
            f"rugs={self._state.rug_count}, trades={self._state.trade_count}, "
            f"sidebets={self._state.sidebet_count}"
        )

    # ========== Event Handler ==========

    def _on_ws_raw_event(self, wrapped: dict[str, Any]) -> None:
        """
        Handle WS_RAW_EVENT events from EventBus.

        Routes to appropriate handler based on event type.
        """
        if not self._running:
            return

        try:
            data = wrapped.get("data", wrapped)
            if not isinstance(data, dict):
                return

            event_name = data.get("event")
            event_data = data.get("data", {})
            timestamp = time.time()  # Use current time for pairing detection

            # Route to appropriate handler
            if event_name == "gameStateUpdate":
                self._handle_game_state_update(event_data, timestamp)
            elif event_name == "standard/newTrade":
                self._handle_new_trade(event_data, timestamp)
            elif event_name == "newSideBet":
                self._handle_new_sidebet(event_data, timestamp)

        except Exception as e:
            logger.error(f"Error handling WS_RAW_EVENT: {e}")

    # ========== Event-Specific Handlers ==========

    def _handle_game_state_update(self, data: dict, timestamp: float) -> None:
        """Handle gameStateUpdate event - detect rug pairs."""
        with self._lock:
            self._state.gamestate_count += 1

            # Log progress every 100 events
            if self._state.gamestate_count % 100 == 0:
                game_id = data.get("gameId", "unknown")
                price = data.get("price", 0)
                tick = data.get("tickCount", 0)
                logger.info(
                    f"[GameHistoryCapture] gameStateUpdate #{self._state.gamestate_count}: "
                    f"game={game_id[:16] if game_id else 'unknown'}... price={price:.2f} tick={tick}"
                )

            if not self._is_rug_event(data):
                # Not a rug event - but track state
                self._state.last_game_id = data.get("gameId")
                self._state.last_rugged_state = data.get("rugged", False)
                return

            # This is a rug event!
            game_history = data.get("gameHistory", [])
            logger.info(
                f"[GameHistoryCapture] RUG EVENT DETECTED! "
                f"gameHistory contains {len(game_history)} games"
            )

            current_time_ms = timestamp * 1000

            if self._state.pending_rug_emission is not None:
                # Check if this is the second emission of a pair
                time_diff = current_time_ms - (self._state.pending_rug_timestamp * 1000)

                if time_diff <= self.RUG_PAIR_WINDOW_MS:
                    # This is emission 2 of the pair!
                    self._save_rug_emission(
                        self._state.pending_rug_emission, 1, self._state.pending_rug_timestamp
                    )
                    self._save_rug_emission(data, 2, timestamp)

                    logger.info(
                        f"[GameHistoryCapture] RUG PAIR #{self._state.rug_count} CAPTURED! "
                        f"(time_diff={time_diff:.0f}ms)"
                    )

                    # Clear pending and increment count
                    self._state.pending_rug_emission = None
                    self._state.pending_rug_timestamp = 0.0
                    self._state.rug_count += 1

                    if self._state.rug_count >= self._state.target_rugs:
                        self._state.capture_complete = True
                        logger.info(
                            f"[GameHistoryCapture] TARGET REACHED: "
                            f"{self._state.rug_count} rug pairs captured!"
                        )
                else:
                    # Too long since last emission - this is a new emission 1
                    logger.warning(
                        f"[GameHistoryCapture] Orphan emission detected "
                        f"(time_diff={time_diff:.0f}ms), starting new pair"
                    )
                    self._state.pending_rug_emission = data
                    self._state.pending_rug_timestamp = timestamp
            else:
                # First emission of a potential pair
                self._state.pending_rug_emission = data
                self._state.pending_rug_timestamp = timestamp
                logger.info(
                    "[GameHistoryCapture] Potential rug emission 1 detected, "
                    "waiting for emission 2..."
                )

    def _handle_new_trade(self, data: dict, timestamp: float) -> None:
        """Handle standard/newTrade event."""
        with self._lock:
            if not self._trades_file:
                return

            record = {
                "timestamp": timestamp,
                "iso": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
                "data": data,
            }
            self._trades_file.write(json.dumps(record, default=str) + "\n")
            self._trades_file.flush()
            self._state.trade_count += 1

            username = data.get("username", "unknown")
            trade_type = data.get("type", "unknown")
            amount = data.get("amount", 0)

            if self._state.trade_count % 5 == 0:
                logger.info(
                    f"[GameHistoryCapture] Trade #{self._state.trade_count}: "
                    f"{username} {trade_type} {amount:.4f} SOL"
                )

    def _handle_new_sidebet(self, data: dict, timestamp: float) -> None:
        """Handle newSideBet event."""
        with self._lock:
            if not self._sidebets_file:
                return

            record = {
                "timestamp": timestamp,
                "iso": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
                "data": data,
            }
            self._sidebets_file.write(json.dumps(record, default=str) + "\n")
            self._sidebets_file.flush()
            self._state.sidebet_count += 1

            username = data.get("username", "unknown")
            x_payout = data.get("xPayout", 0)
            logger.info(
                f"[GameHistoryCapture] Sidebet #{self._state.sidebet_count}: "
                f"{username} bet for {x_payout}x"
            )

    # ========== Helper Methods ==========

    def _is_rug_event(self, data: dict) -> bool:
        """Check if this gameStateUpdate indicates a rug event."""
        if not isinstance(data, dict):
            return False

        # Rug event = rugged is True AND gameHistory is present
        rugged = data.get("rugged", False)
        game_history = data.get("gameHistory", [])

        return rugged and len(game_history) > 0

    def _save_rug_emission(self, data: dict, emission_num: int, timestamp: float) -> Path:
        """Save a single rug emission to file."""
        rug_num = str(self._state.rug_count).zfill(3)
        filename = f"rug_{rug_num}_emission_{emission_num}.json"
        filepath = self._rug_dir / filename

        # Add capture metadata
        capture_data = {
            "capture_timestamp": timestamp,
            "capture_iso": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
            "session_id": self._state.session_id,
            "rug_number": self._state.rug_count,
            "emission_number": emission_num,
            "char_length": len(json.dumps(data)),
            "game_history_count": len(data.get("gameHistory", [])),
            "data": data,
        }

        with open(filepath, "w") as f:
            json.dump(capture_data, f, indent=2, default=str)

        logger.info(
            f"[GameHistoryCapture] Saved rug emission: {filename} "
            f"({capture_data['char_length']} chars, "
            f"{capture_data['game_history_count']} games in history)"
        )
        return filepath

    def _save_manifest(self) -> None:
        """Save capture session manifest."""
        manifest = {
            "session_id": self._state.session_id,
            "capture_start": self._state.session_id,  # Same format
            "capture_end": datetime.now(timezone.utc).isoformat(),
            "rug_pairs_captured": self._state.rug_count,
            "trades_captured": self._state.trade_count,
            "sidebets_captured": self._state.sidebet_count,
            "gamestates_processed": self._state.gamestate_count,
            "target_rugs": self._state.target_rugs,
            "target_reached": self._state.capture_complete,
            "output_directory": str(self._session_dir),
        }

        manifest_path = self._session_dir / "capture_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"[GameHistoryCapture] Manifest saved: {manifest}")

    # ========== State Snapshot ==========

    def get_snapshot(self) -> dict[str, Any]:
        """
        Get a complete snapshot of capture state.

        Returns:
            Dict with all current state values
        """
        with self._lock:
            return {
                "running": self._running,
                "session_id": self._state.session_id,
                "rug_count": self._state.rug_count,
                "trade_count": self._state.trade_count,
                "sidebet_count": self._state.sidebet_count,
                "gamestate_count": self._state.gamestate_count,
                "target_rugs": self._state.target_rugs,
                "capture_complete": self._state.capture_complete,
                "pending_rug": self._state.pending_rug_emission is not None,
                "output_directory": str(self._session_dir),
            }

    # ========== Context Manager ==========

    def __enter__(self) -> "GameHistoryCaptureService":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
