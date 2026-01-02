"""
Human click interception for recording mode.

Wraps UI button callbacks to capture actions via BotActionInterface.
When a human clicks BUY/SELL/SIDEBET, the action is recorded with full context.

Phase B: ButtonEvent Logging Implementation
Emits ButtonEvents via EventBus for RL training data collection.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.game_state import GameState
    from services.live_state_provider import LiveStateProvider

    from ..interface import BotActionInterface

from bot.action_interface.types import ActionParams
from models.events.button_event import ButtonCategory, ButtonEvent, get_button_info
from models.events.player_action import ActionType
from services.async_loop_manager import AsyncLoopManager
from services.event_bus import EventBus, Events

logger = logging.getLogger(__name__)


class HumanActionInterceptor:
    """
    Intercepts human button clicks for recording.

    Usage:
        interceptor = HumanActionInterceptor(action_interface)

        # Wrap button callbacks in main_window setup
        buy_button.config(command=interceptor.wrap_buy(original_buy_handler, get_amount))
        sell_button.config(command=interceptor.wrap_sell(original_sell_handler, get_percentage))
        sidebet_button.config(command=interceptor.wrap_sidebet(original_sidebet_handler, get_amount))
    """

    def __init__(
        self,
        action_interface: "BotActionInterface",
        async_manager: AsyncLoopManager | None = None,
        game_state: "GameState | None" = None,
        event_bus: EventBus | None = None,
        live_state_provider: "LiveStateProvider | None" = None,
    ):
        """
        Initialize interceptor.

        Args:
            action_interface: BotActionInterface configured for RECORDING mode
            async_manager: Optional shared AsyncLoopManager instance
            game_state: Optional GameState for ButtonEvent context
            event_bus: Optional EventBus for ButtonEvent publishing
            live_state_provider: Optional LiveStateProvider for server-authoritative state
        """
        self._interface = action_interface
        self._loop: asyncio.AbstractEventLoop | None = None
        self._async_manager = async_manager
        self._owns_async_manager = False

        # ButtonEvent dependencies
        self._game_state = game_state
        self._event_bus = event_bus
        self._live_state_provider = live_state_provider

        # Sequence tracking for ActionSequence grouping
        self._current_sequence_id: str = str(uuid.uuid4())
        self._sequence_position: int = 0
        self._last_action_tick: int = 0

        logger.info("HumanActionInterceptor initialized")

    def _get_event_loop(self) -> asyncio.AbstractEventLoop | None:
        """
        Best-effort: return an event loop if one is available in this thread.

        IMPORTANT: This does not create a new loop. In GUI contexts (Tk thread),
        there often isn't a running asyncio loop; in that case we fall back to
        AsyncLoopManager.
        """
        if self._loop is not None:
            return self._loop
        try:
            self._loop = asyncio.get_event_loop()
            return self._loop
        except RuntimeError:
            return None

    def _ensure_async_manager(self) -> AsyncLoopManager:
        """Get or create AsyncLoopManager for async execution."""
        if self._async_manager is None:
            self._async_manager = AsyncLoopManager()
            self._async_manager.start()
            self._owns_async_manager = True
        return self._async_manager

    def _schedule_recording(self, params: ActionParams) -> None:
        """Schedule async recording without blocking UI."""
        try:
            if self._async_manager is not None:
                self._async_manager.run_coroutine(self._record_action(params))
                return

            loop = self._get_event_loop()
            if loop is not None:
                asyncio.ensure_future(self._record_action(params), loop=loop)  # noqa: RUF006
                return

            # No loop in this thread (common in Tkinter callbacks): run in dedicated thread.
            self._ensure_async_manager().run_coroutine(self._record_action(params))
        except Exception as e:
            logger.error(f"Failed to schedule recording: {e}")

    async def _record_action(self, params: ActionParams) -> None:
        """Record action via BotActionInterface."""
        try:
            result = await self._interface.execute(params)
            logger.debug(
                f"Recorded human action: {params.action_type.value} "
                f"success={result.success} latency={result.total_latency_ms}ms"
            )
        except Exception as e:
            logger.error(f"Failed to record action: {e}")

    def __del__(self):
        """Best-effort cleanup for owned AsyncLoopManager instance."""
        try:
            if self._owns_async_manager and self._async_manager:
                self._async_manager.stop(timeout=1.0)
        except Exception:
            pass

    # ========== ButtonEvent Methods ==========

    def _detect_game_phase(self) -> int:
        """
        Detect current game phase from GameState.

        Returns:
            0=COOLDOWN, 1=PRESALE, 2=ACTIVE, 3=RUGGED
        """
        if self._game_state is None:
            return 0  # Default to COOLDOWN

        phase_str = self._game_state.get("current_phase", "UNKNOWN")

        # Map phase string to int
        phase_map = {
            "COOLDOWN": 0,
            "PRESALE": 1,
            "ACTIVE": 2,
            "RUGGED": 3,
            "UNKNOWN": 0,
        }
        return phase_map.get(phase_str, 0)

    def _get_player_balance(self) -> Decimal:
        """Get current player balance (server-authoritative if available)."""
        if self._live_state_provider and self._live_state_provider.is_live:
            return self._live_state_provider.cash
        if self._game_state:
            return self._game_state.get("balance", Decimal("0"))
        return Decimal("0")

    def _get_position_qty(self) -> Decimal:
        """Get current position quantity."""
        if self._live_state_provider and self._live_state_provider.is_live:
            return self._live_state_provider.position_qty
        if self._game_state:
            position = self._game_state.get("position")
            if position and position.get("status") == "active":
                return position.get("amount", Decimal("0"))
        return Decimal("0")

    def _should_start_new_sequence(self, button_category: ButtonCategory) -> bool:
        """
        Determine if we should start a new action sequence.

        New sequence starts when:
        1. Previous action was an ACTION button (BUY/SELL/SIDEBET)
        2. More than 50 ticks since last action (timeout)
        3. Game changed (game_id changed)
        """
        if self._game_state is None:
            return True

        current_tick = self._game_state.get("current_tick", 0)
        ticks_since_last = current_tick - self._last_action_tick

        # Start new sequence if timeout (50 ticks ~5 seconds at 10 ticks/sec)
        if ticks_since_last > 50:
            return True

        return False

    def _emit_button_event(
        self,
        button_text: str,
        bet_amount: Decimal = Decimal("0"),
    ) -> None:
        """
        Create and emit ButtonEvent with full game context.

        Args:
            button_text: Raw button text (e.g., "BUY", "+0.01", "25%")
            bet_amount: Current bet amount from UI
        """
        if self._event_bus is None:
            logger.debug("No EventBus, skipping ButtonEvent emission")
            return

        try:
            # Get button info
            button_id, button_category = get_button_info(button_text)

            # Check if we need a new sequence
            if button_category == ButtonCategory.ACTION or self._should_start_new_sequence(
                button_category
            ):
                self._current_sequence_id = str(uuid.uuid4())
                self._sequence_position = 0
            else:
                self._sequence_position += 1

            # Get game context
            current_tick = 0
            current_price = 1.0
            game_id = "unknown"

            if self._game_state:
                current_tick = self._game_state.get("current_tick", 0)
                current_price = float(self._game_state.get("current_price", Decimal("1.0")))
                game_id = self._game_state.get("game_id") or "unknown"

            # Calculate ticks since last action
            ticks_since_last = current_tick - self._last_action_tick
            self._last_action_tick = current_tick

            # Create ButtonEvent
            event = ButtonEvent(
                ts=datetime.now(timezone.utc),
                server_ts=None,  # Will be filled by confirmation if available
                button_id=button_id,
                button_category=button_category,
                tick=current_tick,
                price=current_price,
                game_phase=self._detect_game_phase(),
                game_id=game_id,
                balance=self._get_player_balance(),
                position_qty=self._get_position_qty(),
                bet_amount=bet_amount,
                ticks_since_last_action=max(0, ticks_since_last),
                sequence_id=self._current_sequence_id,
                sequence_position=self._sequence_position,
            )

            # Emit via EventBus
            self._event_bus.publish(Events.BUTTON_PRESS, event.to_dict())

            logger.debug(
                f"ButtonEvent emitted: {button_id} tick={current_tick} "
                f"seq={self._current_sequence_id[:8]}:{self._sequence_position}"
            )

        except KeyError:
            logger.warning(f"Unknown button text: {button_text}")
        except Exception as e:
            logger.error(f"Failed to emit ButtonEvent: {e}")

    def wrap_buy(
        self,
        original_handler: Callable[[], None],
        get_amount: Callable[[], Decimal],
    ) -> Callable[[], None]:
        """
        Wrap BUY button handler.

        Args:
            original_handler: Original button callback
            get_amount: Function that returns current bet amount

        Returns:
            Wrapped callback that records then executes
        """

        def wrapped():
            # Get amount before executing (UI may change)
            amount = get_amount()

            # Emit ButtonEvent for RL training
            self._emit_button_event("BUY", bet_amount=amount)

            # Record the action
            params = ActionParams(action_type=ActionType.BUY, amount=amount)
            self._schedule_recording(params)

            # Call original handler
            original_handler()

        return wrapped

    def wrap_sell(
        self,
        original_handler: Callable[[], None],
        get_percentage: Callable[[], Decimal],
    ) -> Callable[[], None]:
        """
        Wrap SELL button handler.

        Args:
            original_handler: Original button callback
            get_percentage: Function that returns current sell percentage

        Returns:
            Wrapped callback that records then executes
        """

        def wrapped():
            percentage = get_percentage()

            # Emit ButtonEvent for RL training
            self._emit_button_event("SELL")

            params = ActionParams(action_type=ActionType.SELL, percentage=percentage)
            self._schedule_recording(params)

            original_handler()

        return wrapped

    def wrap_sidebet(
        self,
        original_handler: Callable[[], None],
        get_amount: Callable[[], Decimal],
    ) -> Callable[[], None]:
        """
        Wrap SIDEBET button handler.

        Args:
            original_handler: Original button callback
            get_amount: Function that returns current bet amount

        Returns:
            Wrapped callback that records then executes
        """

        def wrapped():
            amount = get_amount()

            # Emit ButtonEvent for RL training
            self._emit_button_event("SIDEBET", bet_amount=amount)

            params = ActionParams(action_type=ActionType.SIDEBET, amount=amount)
            self._schedule_recording(params)

            original_handler()

        return wrapped

    def wrap_increment(
        self,
        original_handler: Callable[[], None],
        button_text: str,
    ) -> Callable[[], None]:
        """
        Wrap increment button handler (+0.001, +0.01, etc.).

        Args:
            original_handler: Original button callback
            button_text: Button identifier (e.g., "+0.01", "X", "1/2")

        Returns:
            Wrapped callback that records then executes
        """

        def wrapped():
            # Emit ButtonEvent for RL training
            self._emit_button_event(button_text)

            params = ActionParams(
                action_type=ActionType.BET_INCREMENT,
                button=button_text,
            )
            self._schedule_recording(params)

            original_handler()

        return wrapped

    def wrap_percentage(
        self,
        original_handler: Callable[[], None],
        percentage: Decimal,
    ) -> Callable[[], None]:
        """
        Wrap percentage button handler (10%, 25%, 50%, 100%).

        Args:
            original_handler: Original button callback
            percentage: Percentage value (e.g., Decimal("0.25"))

        Returns:
            Wrapped callback that records then executes
        """
        # Convert decimal to button text (e.g., 0.25 -> "25%")
        pct_int = int(percentage * 100)
        button_text = f"{pct_int}%"

        def wrapped():
            # Emit ButtonEvent for RL training
            self._emit_button_event(button_text)

            params = ActionParams(
                action_type=ActionType.BET_PERCENTAGE,
                percentage=percentage,
            )
            self._schedule_recording(params)

            original_handler()

        return wrapped
