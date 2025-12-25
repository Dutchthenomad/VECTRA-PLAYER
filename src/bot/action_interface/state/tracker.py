"""
StateTracker - Hybrid state capture for BotActionInterface.

HYBRID approach:
- Live mode: Uses LiveStateProvider (server-authoritative)
- Replay mode: Falls back to GameState (locally calculated)

Responsibilities:
- Capture PlayerState before/after actions
- Capture GameContext at action time
- Emit PlayerAction events to EventBus
"""

import logging
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from bot.action_interface.types import ActionParams, ActionResult, GameContext
from models.events.player_action import PlayerState
from services.event_bus import EventBus, Events

if TYPE_CHECKING:
    from core.game_state import GameState
    from services.live_state_provider import LiveStateProvider

logger = logging.getLogger(__name__)


class StateTracker:
    """
    Hybrid state tracker for action recording.

    Uses LiveStateProvider when available (server-authoritative),
    falls back to GameState when not in live mode.
    """

    def __init__(
        self,
        game_state: "GameState",
        event_bus: EventBus,
        live_state_provider: "LiveStateProvider | None" = None,
    ):
        """
        Initialize StateTracker.

        Args:
            game_state: GameState instance (fallback for replay mode)
            event_bus: EventBus instance for publishing PlayerAction events
            live_state_provider: Optional LiveStateProvider (for live mode)
        """
        self._game_state = game_state
        self._event_bus = event_bus
        self._live_state_provider = live_state_provider

        logger.info(f"StateTracker initialized (live_mode={self._is_live_mode()})")

    def _is_live_mode(self) -> bool:
        """Check if we're in live mode with server-authoritative state."""
        if self._live_state_provider is None:
            return False
        return self._live_state_provider.is_live

    def capture_state_before(self) -> PlayerState:
        """
        Capture player state before an action.

        Uses LiveStateProvider if in live mode, otherwise GameState.

        Returns:
            PlayerState with current financial state
        """
        if self._is_live_mode():
            # Live mode: Use server-authoritative state
            return PlayerState(
                cash=self._live_state_provider.cash,
                position_qty=self._live_state_provider.position_qty,
                avg_cost=self._live_state_provider.avg_cost,
                total_invested=self._live_state_provider.total_invested,
                cumulative_pnl=self._live_state_provider.cumulative_pnl,
            )
        else:
            # Replay mode: Use locally calculated state from GameState
            balance = self._game_state.get("balance", Decimal("0"))
            position = self._game_state.get("position")

            position_qty = Decimal("0")
            avg_cost = Decimal("0")
            total_invested = Decimal("0")

            if position and position.get("status") == "active":
                position_qty = position.get("amount", Decimal("0"))
                avg_cost = position.get("entry_price", Decimal("0"))
                total_invested = position_qty * avg_cost

            # For replay mode, cumulative_pnl is derived from balance change
            initial_balance = self._game_state.get("initial_balance", Decimal("0.100"))
            cumulative_pnl = balance - initial_balance

            return PlayerState(
                cash=balance,
                position_qty=position_qty,
                avg_cost=avg_cost,
                total_invested=total_invested,
                cumulative_pnl=cumulative_pnl,
            )

    def capture_game_context(self) -> GameContext:
        """
        Capture game context at action time.

        Always uses GameState (same source in both live and replay modes).

        Returns:
            GameContext with game snapshot
        """
        snap = self._game_state.get_snapshot()

        return GameContext(
            game_id=snap.game_id or "unknown",
            tick=snap.tick,
            price=snap.price,
            phase=snap.phase,
            is_active=snap.active,
            connected_players=0,  # Not tracked in GameState
        )

    def emit_player_action(
        self,
        result: ActionResult,
        params: ActionParams,
        session_id: str = "unknown",
        player_id: str = "local",
        username: str | None = None,
    ) -> None:
        """
        Emit PlayerAction event to EventBus for persistence.

        Args:
            result: ActionResult with execution outcome
            params: ActionParams with action details
            session_id: Session identifier
            player_id: Player identifier
            username: Player display name
        """
        try:
            # Generate action_id if not present
            action_id = result.action_id or str(uuid.uuid4())

            # Build event payload matching PlayerAction schema
            payload = {
                "action_id": action_id,
                "session_id": session_id,
                "game_id": result.game_context.game_id if result.game_context else "unknown",
                "player_id": player_id,
                "username": username,
                "action_type": result.action_type.value,
                "button": params.button,
                "amount": params.amount,
                "percentage": params.percentage,
                "game_context": (
                    {
                        "game_id": result.game_context.game_id,
                        "tick": result.game_context.tick,
                        "price": result.game_context.price,
                        "phase": result.game_context.phase,
                        "is_pre_round": False,  # Not tracked yet
                        "connected_players": result.game_context.connected_players,
                    }
                    if result.game_context
                    else None
                ),
                "state_before": (
                    {
                        "cash": result.state_before.cash,
                        "position_qty": result.state_before.position_qty,
                        "avg_cost": result.state_before.avg_cost,
                        "total_invested": result.state_before.total_invested,
                        "cumulative_pnl": result.state_before.cumulative_pnl,
                    }
                    if result.state_before
                    else None
                ),
                "timestamps": {
                    "client_ts": result.client_ts,
                    "server_ts": result.server_ts or result.client_ts,
                    "confirmed_ts": result.confirmed_ts or result.client_ts,
                },
                "outcome": {
                    "success": result.success,
                    "executed_price": result.executed_price,
                    "executed_amount": result.executed_amount,
                    "fee": None,  # Not tracked yet
                    "error": result.error,
                    "error_reason": None,  # Not tracked yet
                },
                "state_after": (
                    {
                        "cash": result.state_after.cash,
                        "position_qty": result.state_after.position_qty,
                        "avg_cost": result.state_after.avg_cost,
                        "total_invested": result.state_after.total_invested,
                        "cumulative_pnl": result.state_after.cumulative_pnl,
                    }
                    if result.state_after
                    else None
                ),
            }

            # Publish to EventBus
            self._event_bus.publish(Events.BOT_ACTION, payload)

            logger.debug(
                f"PlayerAction emitted: {action_id} ({result.action_type.value}) "
                f"success={result.success}"
            )

        except Exception as e:
            logger.error(f"Failed to emit PlayerAction: {e}", exc_info=True)
