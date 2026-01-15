"""
BotExecutionBridge - Executes bot decisions via browser button clicks.

Bridges LiveBacktestService bot decisions to real browser button clicks
using delta-based sequencing and front-running optimization.

Features:
- Delta-based sequencing: calculates current → target, not always from zero
- Front-running: prepares next bet amount immediately after placing current
- Tracks current browser amount to minimize clicks
- Safety gate: explicit enable() required before any execution

Usage:
    bridge = BotExecutionBridge(trading_controller, browser_bridge)
    bridge.enable()  # Must be explicitly enabled

    # Stage next bet for front-running
    bridge.stage_next_amount(Decimal("0.002"))

    # Execute current bet (will also prepare next bet)
    await bridge.execute_sidebet(Decimal("0.004"))
"""

import asyncio
import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from bot.bet_amount_sequencer import calculate_optimal_sequence

if TYPE_CHECKING:
    from browser.bridge import BrowserBridge
    from ui.controllers.trading_controller import TradingController

logger = logging.getLogger(__name__)


class BotExecutionBridge:
    """
    Executes bot decisions via browser button clicks.

    Key Features:
    - Delta-based sequencing: uses current amount, doesn't always clear
    - Front-running: prepares next bet amount immediately after placing current
    - Tracks current browser amount to minimize clicks
    - Explicit enable gate for safety
    """

    # Delay between button clicks (ms) - allows browser to register each click
    INTER_CLICK_DELAY_MS = 100

    def __init__(
        self,
        trading_controller: "TradingController",
        browser_bridge: "BrowserBridge",
    ):
        """
        Initialize the execution bridge.

        Args:
            trading_controller: TradingController for UI button methods
            browser_bridge: BrowserBridge for checking connection status
        """
        self.trading_controller = trading_controller
        self.browser_bridge = browser_bridge

        # Safety gate - must be explicitly enabled
        self._enabled = False

        # Track browser input state for delta-based sequencing
        self._current_amount = Decimal("0")

        # Pre-staged amount for front-running
        self._next_amount: Decimal | None = None

        # Execution lock to prevent concurrent operations
        self._lock = asyncio.Lock()

        logger.info("BotExecutionBridge initialized (disabled)")

    # ========================================================================
    # ENABLE/DISABLE CONTROL
    # ========================================================================

    def enable(self) -> None:
        """
        Enable real execution.

        WARNING: This enables real money trading!
        """
        self._enabled = True
        logger.warning("BotExecutionBridge ENABLED - Real money trading active!")

    def disable(self) -> None:
        """Disable real execution."""
        self._enabled = False
        self._next_amount = None  # Clear any staged amounts
        logger.info("BotExecutionBridge disabled")

    @property
    def is_enabled(self) -> bool:
        """Check if execution is enabled."""
        return self._enabled

    # ========================================================================
    # FRONT-RUNNING SUPPORT
    # ========================================================================

    def stage_next_amount(self, amount: Decimal) -> None:
        """
        Stage the next bet amount for front-running.

        Call this when you know what the next bet will be,
        so we can prepare it immediately after current bet executes.

        This allows preparing the next bet amount during the 40-tick
        resolution window, giving us a speed advantage.

        Args:
            amount: Next bet amount in SOL
        """
        self._next_amount = Decimal(str(amount)).quantize(Decimal("0.001"))
        logger.info(f"Staged next bet amount: {self._next_amount} SOL for front-running")

    def clear_staged_amount(self) -> None:
        """Clear any staged front-running amount."""
        self._next_amount = None

    # ========================================================================
    # EXECUTION
    # ========================================================================

    async def execute_sidebet(self, amount: Decimal) -> bool:
        """
        Execute sidebet with the specified amount.

        Flow:
        1. Calculate delta sequence from current → target amount
        2. Click each button with inter-click delay
        3. Click SIDEBET button
        4. If next amount is staged, immediately prepare it (front-run)

        Args:
            amount: Bet amount in SOL

        Returns:
            True if execution succeeded, False otherwise
        """
        if not self._enabled:
            logger.warning(f"Blocked (not enabled): sidebet {amount} SOL")
            return False

        if not self.browser_bridge.is_connected():
            logger.error("Cannot execute: browser not connected")
            return False

        async with self._lock:
            return await self._execute_sidebet_internal(amount)

    async def _execute_sidebet_internal(self, amount: Decimal) -> bool:
        """Internal execution logic (assumes lock is held)."""
        # Normalize amount
        target = Decimal(str(amount)).quantize(Decimal("0.001"))

        # Calculate delta sequence from current → target
        sequence = calculate_optimal_sequence(self._current_amount, target)

        logger.info(
            f"Executing sidebet {target} SOL: {self._current_amount} → {target} "
            f"via {len(sequence)} clicks: {sequence}"
        )

        # Execute amount adjustment sequence
        for button in sequence:
            success = await self._click_button(button)
            if not success:
                logger.error(f"Failed to click button: {button}")
                return False
            await asyncio.sleep(self.INTER_CLICK_DELAY_MS / 1000)

        # Update tracked amount
        self._current_amount = target

        # Click SIDEBET button
        try:
            self.trading_controller.execute_sidebet()
            logger.info(f"SIDEBET clicked for {target} SOL")
        except Exception as e:
            logger.error(f"Failed to click SIDEBET: {e}")
            return False

        # FRONT-RUN: Immediately prepare next bet if staged
        if self._next_amount is not None:
            await self._prepare_next_bet()

        return True

    async def _prepare_next_bet(self) -> None:
        """
        Front-run: adjust amount for next bet immediately.

        This happens right after placing current bet, during the
        40-tick resolution window. Gives us a speed advantage by
        having the amount already set when the next bet tick arrives.
        """
        if self._next_amount is None:
            return

        next_seq = calculate_optimal_sequence(self._current_amount, self._next_amount)

        if next_seq:
            logger.info(
                f"Front-running: {self._current_amount} → {self._next_amount} "
                f"via {len(next_seq)} clicks: {next_seq}"
            )

            for button in next_seq:
                success = await self._click_button(button)
                if not success:
                    logger.warning(f"Front-run failed at button: {button}")
                    break
                await asyncio.sleep(self.INTER_CLICK_DELAY_MS / 1000)

            # Update tracked amount
            self._current_amount = self._next_amount
        else:
            logger.debug(f"Front-run: no clicks needed, already at {self._next_amount}")

        # Clear staged amount
        self._next_amount = None

    async def _click_button(self, button: str) -> bool:
        """
        Click a single button, updating tracked state only on success.

        Args:
            button: Button identifier (X, +0.001, X2, 1/2, etc.)

        Returns:
            True if click succeeded, False otherwise
        """
        # Calculate what the new amount would be (before attempting click)
        new_amount = self._current_amount
        try:
            if button == "X":
                self.trading_controller.clear_bet_amount()
                new_amount = Decimal("0")
            elif button == "X2":
                self.trading_controller.double_bet_amount()
                new_amount = self._current_amount * 2
            elif button == "1/2":
                self.trading_controller.half_bet_amount()
                new_amount = self._current_amount / 2
            elif button.startswith("+"):
                # Parse increment amount from button text
                inc = Decimal(button)
                self.trading_controller.increment_bet_amount(inc)
                new_amount = self._current_amount + inc
            else:
                logger.warning(f"Unknown button: {button}")
                return False

            # Only update tracked amount after successful click
            self._current_amount = new_amount.quantize(Decimal("0.001"))
            return True

        except Exception as e:
            # Don't update _current_amount on failure - keep previous value
            logger.error(f"Failed to click button {button}: {e}")
            return False

    # ========================================================================
    # STATE MANAGEMENT
    # ========================================================================

    def reset_tracked_amount(self, amount: Decimal = Decimal("0")) -> None:
        """
        Reset the tracked browser amount.

        Call this after browser refresh or if tracking gets out of sync.

        Args:
            amount: Current amount in browser (default 0 for fresh state)
        """
        self._current_amount = Decimal(str(amount)).quantize(Decimal("0.001"))
        logger.info(f"Reset tracked amount to {self._current_amount}")

    def sync_from_ui(self, amount_str: str) -> None:
        """
        Sync tracked amount from UI entry field.

        Call this to ensure tracking matches UI state.

        Args:
            amount_str: Current amount string from bet entry field
        """
        try:
            self._current_amount = Decimal(amount_str).quantize(Decimal("0.001"))
            logger.debug(f"Synced tracked amount from UI: {self._current_amount}")
        except Exception as e:
            logger.warning(f"Failed to sync from UI '{amount_str}': {e}")

    @property
    def current_amount(self) -> Decimal:
        """Get the currently tracked browser amount."""
        return self._current_amount

    @property
    def staged_amount(self) -> Decimal | None:
        """Get the staged front-running amount (if any)."""
        return self._next_amount
