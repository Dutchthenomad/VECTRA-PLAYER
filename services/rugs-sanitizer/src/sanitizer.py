"""
Core sanitization pipeline.

Processes raw events from rugs-feed and produces typed, categorized,
phase-annotated data for downstream broadcast.

Pipeline: parse -> phase detect -> validate -> category split -> annotate -> emit
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from .god_candle_detector import GodCandleDetector
from .models import (
    Channel,
    GameHistoryRecord,
    GameTick,
    SanitizedEvent,
    SessionStats,
    Trade,
)
from .phase_detector import PhaseDetector
from .trade_annotator import TradeAnnotator

logger = logging.getLogger(__name__)

# Type alias for event callbacks
EventCallback = Callable[[SanitizedEvent], None]


class SanitizationPipeline:
    """Core event processing pipeline.

    Receives raw events from rugs-feed WebSocket, processes them through
    the sanitization pipeline, and emits typed SanitizedEvent objects
    to registered callbacks.
    """

    def __init__(self) -> None:
        self._phase_detector = PhaseDetector()
        self._trade_annotator = TradeAnnotator()
        self._god_candle_detector = GodCandleDetector()
        self._callbacks: dict[Channel, list[EventCallback]] = {ch: [] for ch in Channel}
        self._stats = PipelineStats()

    @property
    def phase_detector(self) -> PhaseDetector:
        return self._phase_detector

    @property
    def trade_annotator(self) -> TradeAnnotator:
        return self._trade_annotator

    @property
    def god_candle_detector(self) -> GodCandleDetector:
        return self._god_candle_detector

    def on_event(self, channel: Channel, callback: EventCallback) -> None:
        """Register a callback for events on a specific channel."""
        self._callbacks[channel].append(callback)

    def process_raw(self, raw_message: str | dict) -> list[SanitizedEvent]:
        """Process a raw message from rugs-feed WebSocket.

        Expected format from rugs-feed broadcaster:
        {
            "type": "raw_event",
            "event_type": "gameStateUpdate",
            "data": {...},
            "timestamp": "2026-02-06T03:04:19.123456",
            "game_id": "20260206-..."
        }

        Returns list of sanitized events produced (may be >1 for gameStateUpdate
        which splits into game + stats channels).
        """
        if isinstance(raw_message, str):
            try:
                raw_message = json.loads(raw_message)
            except json.JSONDecodeError:
                self._stats.parse_errors += 1
                logger.warning("Failed to parse raw message as JSON")
                return []

        event_type = raw_message.get("event_type", "")
        data = raw_message.get("data", {})
        timestamp_str = raw_message.get("timestamp", "")

        if not event_type or not data:
            self._stats.empty_events += 1
            return []

        self._stats.events_received += 1

        # Parse timestamp
        try:
            timestamp = (
                datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now(UTC)
            )
        except ValueError:
            timestamp = datetime.now(UTC)

        # Route by event type
        if event_type == "gameStateUpdate":
            return self._process_game_state(data, timestamp)
        elif event_type == "standard/newTrade":
            return self._process_trade(data, timestamp)
        else:
            # Pass through other event types unmodified
            self._stats.other_events += 1
            return []

    def _process_game_state(self, data: dict, timestamp: datetime) -> list[SanitizedEvent]:
        """Process gameStateUpdate into game + stats channels."""
        events: list[SanitizedEvent] = []
        game_id = data.get("gameId", "")

        # Phase detection
        phase = self._phase_detector.detect(data)
        self._phase_detector.process(data)

        # Update practice token info if availableShitcoins present
        if data.get("availableShitcoins"):
            self._trade_annotator.update_practice_tokens(data["availableShitcoins"])

        # --- Channel: GAME ---
        game_tick = GameTick.from_raw(data, phase)

        # God candle change-detection: override the stateless has_god_candle
        # flag with the detector's result. The wire re-reports stale god candle
        # data on every transition tick for the rest of the UTC day; the detector
        # tracks previously seen game IDs and only flags genuinely new ones.
        if game_tick.daily_records is not None:
            is_new = self._god_candle_detector.check(game_tick.daily_records)
            game_tick.has_god_candle = is_new

        game_event = SanitizedEvent.create(
            channel=Channel.GAME,
            event_type="gameStateUpdate",
            model=game_tick,
            game_id=game_id,
            phase=phase,
            timestamp=timestamp,
        )
        events.append(game_event)
        self._emit(Channel.GAME, game_event)
        self._stats.game_events += 1

        # --- Channel: STATS ---
        stats = SessionStats.from_raw(data)
        stats_event = SanitizedEvent.create(
            channel=Channel.STATS,
            event_type="gameStateUpdate",
            model=stats,
            game_id=game_id,
            phase=phase,
            timestamp=timestamp,
        )
        events.append(stats_event)
        self._emit(Channel.STATS, stats_event)
        self._stats.stats_events += 1

        # --- Channel: HISTORY (if gameHistory present) ---
        game_history = data.get("gameHistory")
        if game_history:
            for entry_raw in game_history:
                record = GameHistoryRecord.from_raw(entry_raw)
                history_event = SanitizedEvent.create(
                    channel=Channel.HISTORY,
                    event_type="gameHistory",
                    model=record,
                    game_id=record.id,
                    phase=phase,
                    timestamp=timestamp,
                )
                events.append(history_event)
                self._emit(Channel.HISTORY, history_event)
                self._stats.history_events += 1

        # Emit ALL
        for evt in events:
            self._emit(Channel.ALL, evt)

        return events

    def _process_trade(self, data: dict, timestamp: datetime) -> list[SanitizedEvent]:
        """Process standard/newTrade into trades channel."""
        game_id = data.get("gameId", "")
        phase = self._phase_detector.current_phase

        # Parse and annotate
        trade = Trade.from_raw(data)
        self._trade_annotator.annotate(trade, phase)

        # Create event
        trade_event = SanitizedEvent.create(
            channel=Channel.TRADES,
            event_type="standard/newTrade",
            model=trade,
            game_id=game_id,
            phase=phase,
            timestamp=timestamp,
        )
        self._emit(Channel.TRADES, trade_event)
        self._emit(Channel.ALL, trade_event)
        self._stats.trade_events += 1

        return [trade_event]

    def _emit(self, channel: Channel, event: SanitizedEvent) -> None:
        """Emit event to registered callbacks for a channel."""
        for cb in self._callbacks[channel]:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Callback error on {channel}: {e}")

    def get_stats(self) -> dict:
        """Return pipeline statistics."""
        return {
            "events_received": self._stats.events_received,
            "game_events": self._stats.game_events,
            "stats_events": self._stats.stats_events,
            "trade_events": self._stats.trade_events,
            "history_events": self._stats.history_events,
            "other_events": self._stats.other_events,
            "parse_errors": self._stats.parse_errors,
            "empty_events": self._stats.empty_events,
            "phase": self._phase_detector.get_stats(),
        }


class PipelineStats:
    """Counters for pipeline processing."""

    def __init__(self) -> None:
        self.events_received: int = 0
        self.game_events: int = 0
        self.stats_events: int = 0
        self.trade_events: int = 0
        self.history_events: int = 0
        self.other_events: int = 0
        self.parse_errors: int = 0
        self.empty_events: int = 0
