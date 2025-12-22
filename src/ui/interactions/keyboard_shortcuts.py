"""
Keyboard shortcuts handler for MainWindow.
"""

import logging
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class KeyboardShortcutsMixin:
    """Mixin providing keyboard shortcut functionality for MainWindow."""

    def _setup_keyboard_shortcuts(self: "MainWindow"):
        """Setup keyboard shortcuts for common actions"""
        self.root.bind(
            "<space>",
            lambda e: self.replay_controller.toggle_playback()
            if hasattr(self, "replay_controller")
            else None,
        )
        self.root.bind(
            "b",
            lambda e: self.trading_controller.execute_buy()
            if self.buy_button["state"] != tk.DISABLED
            else None,
        )
        self.root.bind(
            "B",
            lambda e: self.trading_controller.execute_buy()
            if self.buy_button["state"] != tk.DISABLED
            else None,
        )
        self.root.bind(
            "s",
            lambda e: self.trading_controller.execute_sell()
            if self.sell_button["state"] != tk.DISABLED
            else None,
        )
        self.root.bind(
            "S",
            lambda e: self.trading_controller.execute_sell()
            if self.sell_button["state"] != tk.DISABLED
            else None,
        )
        self.root.bind(
            "d",
            lambda e: self.trading_controller.execute_sidebet()
            if self.sidebet_button["state"] != tk.DISABLED
            else None,
        )
        self.root.bind(
            "D",
            lambda e: self.trading_controller.execute_sidebet()
            if self.sidebet_button["state"] != tk.DISABLED
            else None,
        )
        self.root.bind(
            "r",
            lambda e: self.replay_controller.reset_game()
            if hasattr(self, "replay_controller")
            else None,
        )
        self.root.bind(
            "R",
            lambda e: self.replay_controller.reset_game()
            if hasattr(self, "replay_controller")
            else None,
        )
        self.root.bind(
            "<Left>",
            lambda e: self.replay_controller.step_backward()
            if hasattr(self, "replay_controller")
            else None,
        )
        self.root.bind(
            "<Right>",
            lambda e: self.replay_controller.step_forward()
            if hasattr(self, "replay_controller")
            else None,
        )
        self.root.bind("<h>", lambda e: self.show_help())
        self.root.bind("<H>", lambda e: self.show_help())
        self.root.bind("l", lambda e: self.live_feed_controller.toggle_live_feed())
        self.root.bind("L", lambda e: self.live_feed_controller.toggle_live_feed())

        logger.info("Keyboard shortcuts configured (added 'L' for live feed)")

    def show_help(self: "MainWindow"):
        """Show help dialog with keyboard shortcuts"""
        help_text = """
KEYBOARD SHORTCUTS:

Trading:
  B - Buy (open position)
  S - Sell (close position)
  D - Place side bet

Playback:
  Space - Play/Pause
  R - Reset game
  <- - Step backward
  -> - Step forward

Data Sources:
  L - Toggle live WebSocket feed

Other:
  H - Show this help

GAME RULES:
* Side bets win if rug occurs within 40 ticks
* Side bet pays 5x your wager
* After side bet resolves, 5 tick cooldown before next bet
* All positions are lost when rug occurs
"""
        messagebox.showinfo("Help - Keyboard Shortcuts", help_text)
