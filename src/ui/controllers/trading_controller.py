"""
TradingController - Manages trade execution and bet amount management.

Handles:
- Trade execution (buy/sell/sidebet)
- Bet amount management (increment, clear, half, double, max)
- Sell percentage management (10%, 25%, 50%, 100%)
"""

import logging
import tkinter as tk
from collections.abc import Callable
from decimal import Decimal, InvalidOperation

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

        logger.info("TradingController initialized")

    # ========================================================================
    # TRADE EXECUTION
    # ========================================================================

    def execute_buy(self):
        """Execute buy action using TradeManager."""
        # Click BUY in browser first - browser is source of truth
        try:
            self.browser_bridge.on_buy_clicked()
        except Exception as e:
            logger.warning(f"Browser bridge unavailable for BUY: {e}")
            # Continue with local trading - browser is optional

        amount = self.get_bet_amount()
        if amount is None:
            return  # Validation failed, but browser click already sent

        result = self.trade_manager.execute_buy(amount)

        if result["success"]:
            self.log(f"BUY executed at {result['price']:.4f}x")
            self.toast.show(f"Bought {amount} SOL at {result['price']:.4f}x", "success")
        else:
            self.log(f"BUY failed: {result['reason']}")
            self.toast.show(f"Buy failed: {result['reason']}", "error")

    def execute_sell(self):
        """Execute sell action using TradeManager (supports partial sells)."""
        # Click SELL in browser if connected
        try:
            self.browser_bridge.on_sell_clicked()
        except Exception as e:
            logger.warning(f"Browser bridge unavailable for SELL: {e}")
            # Continue with local trading - browser is optional

        result = self.trade_manager.execute_sell()

        if result["success"]:
            pnl = result.get("pnl_sol", 0)
            pnl_pct = result.get("pnl_percent", 0)
            msg_type = "success" if pnl >= 0 else "error"

            # Show partial sell information
            if result.get("partial", False):
                percentage = result.get("percentage", 1.0)
                remaining = result.get("remaining_amount", 0)
                self.log(
                    f"PARTIAL SELL ({percentage * 100:.0f}%) - P&L: {pnl:+.4f} SOL, Remaining: {remaining:.4f} SOL"
                )
                self.toast.show(
                    f"Sold {percentage * 100:.0f}%! P&L: {pnl:+.4f} SOL ({pnl_pct:+.1f}%)", msg_type
                )
            else:
                self.log(f"SELL executed - P&L: {pnl:+.4f} SOL")
                self.toast.show(f"Sold! P&L: {pnl:+.4f} SOL ({pnl_pct:+.1f}%)", msg_type)
        else:
            self.log(f"SELL failed: {result['reason']}")
            self.toast.show(f"Sell failed: {result['reason']}", "error")

    def execute_sidebet(self):
        """Execute sidebet using TradeManager (Phase 9.3: syncs to browser)"""
        # Click SIDEBET in browser first - browser is source of truth
        try:
            self.browser_bridge.on_sidebet_clicked()
        except Exception as e:
            logger.warning(f"Browser bridge unavailable for SIDEBET: {e}")
            # Continue with local trading - browser is optional

        amount = self.get_bet_amount()
        if amount is None:
            return  # Validation failed (toast already shown), but browser click already sent

        result = self.trade_manager.execute_sidebet(amount)

        if result["success"]:
            potential_win = result.get("potential_win", 0)
            self.log(f"SIDEBET placed ({amount} SOL)")
            self.toast.show(
                f"Side bet placed! {amount} SOL (potential: {potential_win:.4f} SOL)", "warning"
            )
        else:
            self.log(f"SIDEBET failed: {result['reason']}")
            self.toast.show(f"Side bet failed: {result['reason']}", "error")

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
