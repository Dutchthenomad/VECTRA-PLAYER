"""
Example Subscriber - Demonstrates correct BaseSubscriber usage.

This is a reference implementation showing:
- How to inherit from BaseSubscriber
- How to implement required methods
- How to optionally override hooks
- How to filter events
"""

import logging
from dataclasses import dataclass, field

from foundation.client import FoundationClient
from foundation.events import GameTickEvent, PlayerStateEvent, PlayerTradeEvent
from foundation.subscriber import BaseSubscriber

logger = logging.getLogger(__name__)


@dataclass
class ExampleSubscriberState:
    """State tracked by the example subscriber."""

    last_price: float = 1.0
    last_tick: int = 0
    last_phase: str = "UNKNOWN"
    cash: float = 0.0
    position_qty: float = 0.0
    connected: bool = False
    trades_seen: list = field(default_factory=list)


class ExampleSubscriber(BaseSubscriber):
    """
    Example subscriber that demonstrates correct usage patterns.

    This subscriber:
    - Tracks latest game state
    - Tracks player balance
    - Logs all events
    - Optionally tracks other player trades
    """

    def __init__(self, client: FoundationClient, track_trades: bool = False):
        """
        Initialize example subscriber.

        Args:
            client: FoundationClient instance
            track_trades: If True, track other player trades
        """
        self.state = ExampleSubscriberState()
        self._track_trades = track_trades
        super().__init__(client)

    def on_game_tick(self, event: GameTickEvent) -> None:
        """
        Handle game.tick event.

        Updates local state with latest price/tick/phase.
        """
        self.state.last_price = event.price
        self.state.last_tick = event.tick_count
        self.state.last_phase = event.phase

        logger.debug(f"Tick {event.tick_count}: price={event.price:.4f} phase={event.phase}")

    def on_player_state(self, event: PlayerStateEvent) -> None:
        """
        Handle player.state event.

        Updates local state with latest balance/position.
        """
        self.state.cash = event.cash
        self.state.position_qty = event.position_qty

        logger.debug(f"Player state: cash={event.cash:.4f} position={event.position_qty:.4f}")

    def on_connection_change(self, connected: bool) -> None:
        """
        Handle connection state change.

        Updates connected flag and logs the change.
        """
        self.state.connected = connected

        if connected:
            logger.info("Connected to Foundation Service")
        else:
            logger.warning("Disconnected from Foundation Service")

    def on_player_trade(self, event: PlayerTradeEvent) -> None:
        """
        Handle player.trade event (optional).

        Only tracks trades if track_trades was enabled.
        """
        if self._track_trades:
            trade_info = {
                "username": event.username,
                "type": event.trade_type,
                "qty": event.qty,
                "price": event.price,
            }
            self.state.trades_seen.append(trade_info)

            logger.debug(
                f"Trade: {event.username} {event.trade_type} {event.qty:.4f} @ {event.price:.4f}"
            )

    def get_state(self) -> ExampleSubscriberState:
        """Get current tracked state."""
        return self.state

    def reset_trades(self) -> None:
        """Clear tracked trades list."""
        self.state.trades_seen.clear()
