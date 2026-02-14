"""
SimpleTradingAdapter - Minimal adapter for BotExecutionBridge.

Provides the same interface as TradingController but without
all the UI dependencies. Just forwards to BrowserBridge.
"""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from browser.bridge import BrowserBridge

logger = logging.getLogger(__name__)


class SimpleTradingAdapter:
    """
    Minimal trading adapter that forwards commands to BrowserBridge.

    Implements the methods needed by BotExecutionBridge:
    - clear_bet_amount()
    - double_bet_amount()
    - half_bet_amount()
    - increment_bet_amount(amount)
    - execute_sidebet()
    """

    def __init__(self, browser_bridge: "BrowserBridge"):
        self.browser_bridge = browser_bridge

    def clear_bet_amount(self):
        """Clear bet amount to zero (X button)."""
        logger.debug("Clicking X (clear)")
        try:
            self.browser_bridge.on_clear_clicked()
        except Exception as e:
            logger.error(f"Failed to click X: {e}")

    def double_bet_amount(self):
        """Double bet amount (X2 button)."""
        logger.debug("Clicking X2")
        try:
            self.browser_bridge.on_increment_clicked("X2")
        except Exception as e:
            logger.error(f"Failed to click X2: {e}")

    def half_bet_amount(self):
        """Halve bet amount (1/2 button)."""
        logger.debug("Clicking 1/2")
        try:
            self.browser_bridge.on_increment_clicked("1/2")
        except Exception as e:
            logger.error(f"Failed to click 1/2: {e}")

    def increment_bet_amount(self, amount: Decimal):
        """Increment bet amount by specified amount."""
        button_text = f"+{amount}"
        logger.debug(f"Clicking {button_text}")
        try:
            self.browser_bridge.on_increment_clicked(button_text)
        except Exception as e:
            logger.error(f"Failed to click {button_text}: {e}")

    def execute_sidebet(self):
        """Click SIDEBET button."""
        logger.info("Clicking SIDEBET")
        try:
            self.browser_bridge.on_sidebet_clicked()
        except Exception as e:
            logger.error(f"Failed to click SIDEBET: {e}")
