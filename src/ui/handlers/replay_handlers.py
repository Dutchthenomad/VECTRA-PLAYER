"""
Replay engine callbacks for MainWindow (tick updates, game end).
"""

import logging
import tkinter as tk
from decimal import Decimal
from typing import TYPE_CHECKING

from models import GameTick

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class ReplayHandlersMixin:
    """Mixin providing replay callback functionality for MainWindow."""

    def _on_tick_update(self: "MainWindow", tick: GameTick, index: int, total: int):
        """Background callback for ReplayEngine tick updates"""
        self.ui_dispatcher.submit(self._process_tick_ui, tick, index, total)

    def _process_tick_ui(self: "MainWindow", tick: GameTick, index: int, total: int):
        """Execute tick updates on the Tk main thread"""
        self.tick_label.config(text=f"TICK: {tick.tick}")
        self.price_label.config(text=f"PRICE: {tick.price:.4f}X")

        display_phase = "RUGGED" if tick.rugged else tick.phase
        self.phase_label.config(text=f"PHASE: {display_phase}")

        self.chart.add_tick(tick.tick, tick.price)

        self.trade_manager.check_and_handle_rug(tick)
        self.trade_manager.check_sidebet_expiry(tick)

        if self.bot_enabled:
            self.bot_executor.queue_execution(tick)

        live_override = self.live_mode or (
            self.browser_bridge and self.browser_bridge.is_connected()
        )

        if not self.bot_enabled and not live_override:
            if tick.is_tradeable():
                self.buy_button.config(state=tk.NORMAL)
                if not self.state.get("sidebet"):
                    self.sidebet_button.config(state=tk.NORMAL)
            else:
                self.buy_button.config(state=tk.DISABLED)
                self.sidebet_button.config(state=tk.DISABLED)

            position = self.state.get("position")
            if position and position.get("status") == "active":
                self.sell_button.config(state=tk.NORMAL)

                entry_price = position["entry_price"]
                amount = position["amount"]
                pnl_pct = ((tick.price / entry_price) - 1) * 100
                pnl_sol = amount * (tick.price - entry_price)

                self.position_label.config(
                    text=f"POS: {pnl_sol:+.4f} SOL ({pnl_pct:+.1f}%)",
                    fg="#00ff88" if pnl_sol > 0 else "#ff3366",
                )
            else:
                self.sell_button.config(state=tk.DISABLED)
                self.position_label.config(text="POSITION: NONE", fg="#666666")
        else:
            position = self.state.get("position")
            if position and position.get("status") == "active":
                entry_price = position["entry_price"]
                amount = position["amount"]
                pnl_pct = ((tick.price / entry_price) - 1) * 100
                pnl_sol = amount * (tick.price - entry_price)

                self.buy_button.config(state=tk.NORMAL)
                self.sidebet_button.config(state=tk.NORMAL)
                self.sell_button.config(state=tk.NORMAL)

                self.position_label.config(
                    text=f"POS: {pnl_sol:+.4f} SOL ({pnl_pct:+.1f}%)",
                    fg="#00ff88" if pnl_sol > 0 else "#ff3366",
                )
            else:
                if live_override:
                    self.buy_button.config(state=tk.NORMAL)
                    self.sidebet_button.config(state=tk.NORMAL)
                    self.sell_button.config(state=tk.NORMAL)
                else:
                    self.sell_button.config(state=tk.DISABLED)
                self.position_label.config(text="POSITION: NONE", fg="#666666")

        sidebet = self.state.get("sidebet")
        if sidebet and sidebet.get("status") == "active":
            placed_tick = sidebet.get("placed_tick", 0)
            resolution_window = self.config.GAME_RULES.get("sidebet_window_ticks", 40)
            ticks_remaining = (placed_tick + resolution_window) - tick.tick

            if ticks_remaining > 0:
                self.sidebet_status_label.config(
                    text=f"SIDEBET: {ticks_remaining} ticks", fg="#ffcc00"
                )
            else:
                self.sidebet_status_label.config(text="SIDEBET: RESOLVING", fg="#ff9900")
        else:
            self.sidebet_status_label.config(text="SIDEBET: NONE", fg="#666666")

    def _on_game_end(self: "MainWindow", metrics: dict):
        """Callback for game end - AUDIT FIX Phase 2.6: Thread-safe UI updates"""
        self.log(f"Game ended. Final balance: {metrics.get('current_balance', 0):.4f} SOL")

        def _update_ui():
            """Execute UI updates on main thread"""
            if self.state.get("balance") < Decimal("0.001"):
                logger.warning("BANKRUPT - Resetting balance to initial")
                self.state.update(balance=self.state.get("initial_balance"))
                self.log("Warning: Balance reset to initial (bankruptcy)")

            if self.multi_game_mode and self.game_queue.has_next():
                next_file = self.game_queue.next_game()
                logger.info(f"Auto-loading next game: {next_file.name}")
                self.log(
                    f"Auto-loading game {self.game_queue.current_index}/{len(self.game_queue)}"
                )
                if hasattr(self, "replay_controller"):
                    self.replay_controller.load_next_game(next_file)
                if not self.user_paused:
                    self.replay_engine.play()
                    self.play_button.config(text="\u23f8\ufe0f Pause")
                else:
                    self.play_button.config(text="\u25b6\ufe0f Play")
            else:
                if self.bot_enabled:
                    self.bot_executor.stop()
                    self.bot_enabled = False
                    self.bot_toggle_button.config(text="\U0001f916 Enable Bot", bg="#666666")
                    self.bot_status_label.config(text="Bot: Disabled", fg="#666666")
                    self.bot_var.set(False)

                self.play_button.config(text="\u25b6\ufe0f Play")

        self.ui_dispatcher.submit(_update_ui)
