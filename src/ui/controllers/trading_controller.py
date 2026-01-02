"""
TradingController - Manages trade execution and bet amount management.

Handles:
- Trade execution (buy/sell/sidebet)
- Bet amount management (increment, clear, half, double, max)
- Sell percentage management (10%, 25%, 50%, 100%)

Phase B: ButtonEvent Logging
Emits ButtonEvents via EventBus for RL training data collection.
"""

import logging
import tkinter as tk
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from models.events.button_event import ButtonCategory, ButtonEvent, get_button_info
from services.event_bus import EventBus, Events

logger = logging.getLogger(__name__)


class TradingController:
    """Manages trade execution and bet amount management."""

    def __init__(
        self,
        parent_window,  # Reference to MainWindow for state access
        trade_manager,
        state,
        config,
        browser_bridge,
        bet_entry: tk.Entry,
        percentage_buttons: dict,
        ui_dispatcher,
        toast,
        log_callback: Callable[[str], None],
        event_bus: EventBus | None = None,
        live_state_provider: Any | None = None,
    ):
        """
        Initialize TradingController with dependencies.

        Args:
            parent_window: MainWindow instance
            trade_manager: TradeManager instance
            state: GameState instance
            config: Config object
            browser_bridge: BrowserBridge instance
            bet_entry: Bet amount entry widget
            percentage_buttons: Dict mapping percentages to button info
            ui_dispatcher: TkDispatcher for thread-safe UI updates
            toast: Toast notification widget
            log_callback: Logging function
            event_bus: EventBus for ButtonEvent emission (Phase B)
            live_state_provider: LiveStateProvider for live game context (Phase B)
        """
        self.parent = parent_window
        self.trade_manager = trade_manager
        self.state = state
        self.config = config
        self.browser_bridge = browser_bridge
        self.bet_entry = bet_entry
        self.percentage_buttons = percentage_buttons
        self.ui_dispatcher = ui_dispatcher
        self.toast = toast
        self.log = log_callback
        self.event_bus = event_bus
        self.live_state_provider = live_state_provider

        # ButtonEvent sequence tracking (Phase B)
        self._current_sequence_id: str = str(uuid.uuid4())
        self._sequence_position: int = 0
        self._last_action_tick: int = 0

        logger.info("TradingController initialized")

    # ========================================================================
    # BUTTONEVENT EMISSION (Phase B)
    # ========================================================================

    def _detect_game_phase(self) -> int:
        """
        Detect current game phase from GameState.

        Returns:
            0=COOLDOWN, 1=PRESALE, 2=ACTIVE, 3=RUGGED
        """
        phase_str = self.state.get("current_phase", "UNKNOWN")
        phase_map = {
            "COOLDOWN": 0,
            "PRESALE": 1,
            "ACTIVE": 2,
            "RUGGED": 3,
            "UNKNOWN": 0,
        }
        return phase_map.get(phase_str, 0)

    def _should_start_new_sequence(self, button_category: ButtonCategory) -> bool:
        """
        Determine if we should start a new action sequence.

        New sequence starts when:
        1. Previous action was an ACTION button (BUY/SELL/SIDEBET)
        2. More than 50 ticks since last action (timeout)
        """
        current_tick = self.state.get("current_tick", 0)
        ticks_since_last = current_tick - self._last_action_tick

        # Start new sequence if timeout (50 ticks ~5 seconds at 10 ticks/sec)
        if ticks_since_last > 50:
            return True

        return False

    def _emit_button_event(self, button_text: str) -> None:
        """
        Create and emit ButtonEvent with full game context.

        Args:
            button_text: Raw button text (e.g., "BUY", "+0.01", "25%")
        """
        if self.event_bus is None:
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

            # Get game context - prefer LiveStateProvider for live WebSocket data
            # Use is_live (source=cdp/public_ws) rather than is_connected (needs player_update)
            if self.live_state_provider and self.live_state_provider.is_live:
                current_tick = self.live_state_provider.current_tick
                current_price = float(self.live_state_provider.current_multiplier)
                game_id = self.live_state_provider.game_id or "unknown"
                balance = self.live_state_provider.cash
                position_qty = self.live_state_provider.position_qty
            else:
                # Fallback to GameState (for replay mode or disconnected state)
                current_tick = self.state.get("current_tick", 0)
                current_price = float(self.state.get("current_price", Decimal("1.0")))
                game_id = self.state.get("game_id") or "unknown"
                balance = self.state.get("balance", Decimal("0"))
                position_qty = self.state.get("position_qty", Decimal("0"))

            # Calculate ticks since last action
            ticks_since_last = current_tick - self._last_action_tick
            self._last_action_tick = current_tick

            # Get bet amount from entry
            try:
                bet_amount = Decimal(self.bet_entry.get())
            except (InvalidOperation, ValueError):
                bet_amount = Decimal("0")

            # Pipeline C: Get time_in_position from LiveStateProvider
            time_in_position = 0
            if self.live_state_provider and self.live_state_provider.is_live:
                time_in_position = self.live_state_provider.time_in_position

            # Pipeline C: Capture client timestamp for latency tracking
            client_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)

            # Create ButtonEvent
            event = ButtonEvent(
                ts=datetime.now(timezone.utc),
                server_ts=None,
                button_id=button_id,
                button_category=button_category,
                tick=current_tick,
                price=current_price,
                game_phase=self._detect_game_phase(),
                game_id=game_id,
                balance=balance,
                position_qty=position_qty,
                bet_amount=bet_amount,
                ticks_since_last_action=max(0, ticks_since_last),
                sequence_id=self._current_sequence_id,
                sequence_position=self._sequence_position,
                # Pipeline C fields
                time_in_position=time_in_position,
                client_timestamp=client_timestamp,
            )

            # Emit via EventBus
            self.event_bus.publish(Events.BUTTON_PRESS, event.to_dict())

            logger.debug(
                f"ButtonEvent emitted: {button_id} tick={current_tick} "
                f"seq={self._current_sequence_id[:8]}:{self._sequence_position}"
            )

        except KeyError:
            logger.warning(f"Unknown button text: {button_text}")
        except Exception as e:
            logger.error(f"Failed to emit ButtonEvent: {e}")

    # ========================================================================
    # TRADE EXECUTION
    # ========================================================================

    def execute_buy(self):
        """
        Execute buy action - SERVER AUTHORITATIVE.

        Flow: Button press → Browser bridge → Server → WebSocket response → UI
        No local validation - server determines success/failure.
        """
        # Emit ButtonEvent for RL training (Phase B)
        self._emit_button_event("BUY")

        # Click BUY in browser - BROWSER/SERVER IS SOURCE OF TRUTH
        try:
            self.browser_bridge.on_buy_clicked()
            self.log("BUY sent to server")
        except Exception as e:
            logger.warning(f"Browser bridge unavailable for BUY: {e}")
            self.log(f"BUY failed: No browser connection")

        # Server response via WebSocket will trigger appropriate UI feedback

    def execute_sell(self):
        """
        Execute sell action - SERVER AUTHORITATIVE.

        Flow: Button press → Browser bridge → Server → WebSocket response → UI
        No local validation - server determines success/failure.
        """
        # Emit ButtonEvent for RL training (Phase B)
        self._emit_button_event("SELL")

        # Click SELL in browser - BROWSER/SERVER IS SOURCE OF TRUTH
        try:
            self.browser_bridge.on_sell_clicked()
            self.log("SELL sent to server")
        except Exception as e:
            logger.warning(f"Browser bridge unavailable for SELL: {e}")
            self.log(f"SELL failed: No browser connection")

        # Server response via WebSocket will trigger appropriate UI feedback

    def execute_sidebet(self):
        """
        Execute sidebet action - SERVER AUTHORITATIVE.

        Flow: Button press → Browser bridge → Server → WebSocket response → UI
        No local validation - server determines success/failure.
        """
        # Emit ButtonEvent for RL training (Phase B)
        self._emit_button_event("SIDEBET")

        # Click SIDEBET in browser - BROWSER/SERVER IS SOURCE OF TRUTH
        try:
            self.browser_bridge.on_sidebet_clicked()
            self.log("SIDEBET sent to server")
        except Exception as e:
            logger.warning(f"Browser bridge unavailable for SIDEBET: {e}")
            self.log(f"SIDEBET failed: No browser connection")

        # Server response via WebSocket will trigger appropriate UI feedback

    # ========================================================================
    # PERCENTAGE SELECTOR (Phase 8.2)
    # ========================================================================

    def set_sell_percentage(self, percentage: float):
        """
        Set the sell percentage (user clicked a percentage button)

        Phase 8.2: Radio-button style selector for partial sells
        Phase 9.3: Syncs to browser

        Args:
            percentage: 0.1 (10%), 0.25 (25%), 0.5 (50%), or 1.0 (100%)
        """
        # Emit ButtonEvent for RL training (Phase B)
        pct_int = int(percentage * 100)
        self._emit_button_event(f"{pct_int}%")

        # Click percentage button in browser if connected
        try:
            self.browser_bridge.on_percentage_clicked(percentage)
        except Exception as e:
            logger.warning(f"Browser bridge unavailable for percentage {percentage}: {e}")

        # Update GameState with new percentage
        success = self.state.set_sell_percentage(Decimal(str(percentage)))

        if success:
            self.parent.current_sell_percentage = percentage
            # Highlight the selected button
            self.ui_dispatcher.submit(lambda: self.highlight_percentage_button(percentage))
            self.log(f"Sell percentage set to {percentage * 100:.0f}%")
        else:
            self.toast.show(f"Invalid percentage: {percentage * 100:.0f}%", "error")

    def highlight_percentage_button(self, selected_percentage: float):
        """
        Highlight the selected percentage button (radio-button style)

        Phase 8.2: Only one button is highlighted at a time

        Args:
            selected_percentage: The percentage value that should be highlighted
        """
        for pct, btn_info in self.percentage_buttons.items():
            button = btn_info["button"]
            if pct == selected_percentage:
                # Highlight selected button
                button.config(bg=btn_info["selected_color"], relief=tk.SUNKEN, bd=3)
            else:
                # Reset unselected buttons
                button.config(bg=btn_info["default_color"], relief=tk.RAISED, bd=2)

    # ========================================================================
    # BET AMOUNT MANAGEMENT
    # ========================================================================

    def set_bet_amount(self, amount: Decimal):
        """Set bet amount from quick buttons or manual input"""
        self.bet_entry.delete(0, tk.END)
        self.bet_entry.insert(0, str(amount))
        logger.debug(f"Bet amount set to {amount}")

    def increment_bet_amount(self, amount: Decimal):
        """Increment bet amount by specified amount (Phase 9.3: syncs to browser)"""
        # Click increment button in browser FIRST
        # Map Decimal amount to button text: 0.001 -> '+0.001', 0.01 -> '+0.01', etc.
        button_text = f"+{amount}"

        # Emit ButtonEvent for RL training (Phase B)
        self._emit_button_event(button_text)

        try:
            self.browser_bridge.on_increment_clicked(button_text)
        except Exception as e:
            logger.warning(f"Browser bridge unavailable for increment {button_text}: {e}")

        # Then update local UI
        try:
            current_amount = Decimal(self.bet_entry.get())
        except (InvalidOperation, ValueError) as e:
            logger.warning(f"Invalid bet amount during increment '{self.bet_entry.get()}': {e}")
            current_amount = Decimal("0")
        except Exception as e:
            logger.error(f"Unexpected error parsing bet amount during increment: {e}")
            current_amount = Decimal("0")

        new_amount = current_amount + amount
        self.bet_entry.delete(0, tk.END)
        self.bet_entry.insert(0, str(new_amount))
        logger.debug(f"Bet amount incremented by {amount} to {new_amount}")

    def clear_bet_amount(self):
        """Clear bet amount to zero (Phase 9.3: syncs to browser)"""
        # Emit ButtonEvent for RL training (Phase B)
        self._emit_button_event("X")

        # Click X (clear) button in browser FIRST
        try:
            self.browser_bridge.on_clear_clicked()
        except Exception as e:
            logger.warning(f"Browser bridge unavailable for clear: {e}")

        # Then update local UI
        self.bet_entry.delete(0, tk.END)
        self.bet_entry.insert(0, "0")
        logger.debug("Bet amount cleared to 0")

    def half_bet_amount(self):
        """Halve bet amount (1/2 button) - Phase 9.3: syncs to browser"""
        # Emit ButtonEvent for RL training (Phase B)
        self._emit_button_event("1/2")

        # Click 1/2 button in browser FIRST
        try:
            self.browser_bridge.on_increment_clicked("1/2")
        except Exception as e:
            logger.warning(f"Browser bridge unavailable for half: {e}")

        # Then update local UI
        try:
            current = Decimal(self.bet_entry.get())
            new_amount = current / 2
            self.bet_entry.delete(0, tk.END)
            self.bet_entry.insert(0, str(new_amount))
            logger.debug(f"Bet amount halved to {new_amount}")
        except (InvalidOperation, ValueError) as e:
            logger.warning(
                f"Invalid bet amount during halve operation '{self.bet_entry.get()}': {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected error during halve operation: {e}")

    def double_bet_amount(self):
        """Double bet amount (X2 button) - Phase 9.3: syncs to browser"""
        # Emit ButtonEvent for RL training (Phase B)
        self._emit_button_event("X2")

        # Click X2 button in browser FIRST
        try:
            self.browser_bridge.on_increment_clicked("X2")
        except Exception as e:
            logger.warning(f"Browser bridge unavailable for double: {e}")

        # Then update local UI
        try:
            current = Decimal(self.bet_entry.get())
            new_amount = current * 2
            self.bet_entry.delete(0, tk.END)
            self.bet_entry.insert(0, str(new_amount))
            logger.debug(f"Bet amount doubled to {new_amount}")
        except (InvalidOperation, ValueError) as e:
            logger.warning(
                f"Invalid bet amount during double operation '{self.bet_entry.get()}': {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected error during double operation: {e}")

    def max_bet_amount(self):
        """Set bet to max (MAX button) - Phase 9.3: syncs to browser"""
        # Emit ButtonEvent for RL training (Phase B)
        self._emit_button_event("MAX")

        # Click MAX button in browser FIRST
        try:
            self.browser_bridge.on_increment_clicked("MAX")
        except Exception as e:
            logger.warning(f"Browser bridge unavailable for MAX: {e}")

        # Then update local UI
        balance = self.state.get("balance")
        if balance:
            self.bet_entry.delete(0, tk.END)
            self.bet_entry.insert(0, str(balance))
            logger.debug(f"Bet amount set to MAX: {balance}")

    def get_bet_amount(self) -> Decimal | None:
        """
        Get and validate bet amount from entry

        Returns:
            Decimal amount if valid, None otherwise
        """
        try:
            bet_amount = Decimal(self.bet_entry.get())

            min_bet = self.config.FINANCIAL["min_bet"]
            max_bet = self.config.FINANCIAL["max_bet"]

            if bet_amount < min_bet:
                self.toast.show(f"Bet must be at least {min_bet} SOL", "error")
                return None

            if bet_amount > max_bet:
                self.toast.show(f"Bet cannot exceed {max_bet} SOL", "error")
                return None

            balance = self.state.get("balance")
            if bet_amount > balance:
                self.toast.show(f"Insufficient balance! Have {balance:.4f} SOL", "error")
                return None

            return bet_amount

        except Exception as e:
            self.toast.show("Invalid bet amount", "error")
            logger.error(f"Invalid bet amount: {e}")
            return None
